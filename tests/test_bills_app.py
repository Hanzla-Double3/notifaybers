import json
from datetime import date, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.bills import checker, explain, service
from app.bills.adapters.gepco import Gepco
from app.bills.adapters.pitc import parse_pitc_bill
from app.bills.base import Bill, BillError, Challenge
from app.db import engine, init_db
from app.deps import require_user_api
from app.main import app
from app.routes import bills as bills_routes
from app.models import BillAccount, BillRecord, User

FIXTURE = (Path(__file__).parent / "fixtures" / "pitc_gepco_bill.html").read_text(encoding="utf-8")
REF = "04123456789012"


@pytest.fixture()
def user():
    init_db()
    with Session(engine) as session:
        for model in (BillRecord, BillAccount):
            for row in session.exec(select(model)).all():
                session.delete(row)
        session.commit()
        u = session.exec(select(User)).first()
        u.bills_enabled, u.timezone, u.bills_language = True, "Asia/Karachi", "ur_roman"
        session.add(u)
        session.commit()
        session.refresh(u)
        return u


@pytest.fixture()
def client(user):
    app.dependency_overrides[require_user_api] = lambda: user
    yield TestClient(app)
    app.dependency_overrides.clear()


def parsed(**changes) -> Bill:
    bill = parse_pitc_bill(FIXTURE, "gepco", REF)
    for key, value in changes.items():
        setattr(bill, key, value)
    return bill


# ---- text ----------------------------------------------------------------------------------


@pytest.mark.parametrize("lang", explain.LANGS)
def test_explanation_mentions_the_key_numbers_in_every_language(lang):
    text = " ".join(explain.explain(service.bill_to_dict(parsed()), lang))
    for needle in ("3,831", "4,096", "80", "677"):
        assert needle in text, (lang, needle)


def test_explanation_compares_with_last_month():
    text = " ".join(explain.explain(service.bill_to_dict(parsed()), "en"))
    assert "61% less than last month (203 units)" in text


def test_notices_exist_in_all_languages():
    bill = service.bill_to_dict(parsed())
    for lang in explain.LANGS:
        for title, body in (explain.notice_new(bill, "Home", lang), explain.notice_due(bill, "Home", False, lang)):
            assert title and body and "3,831" in title


# ---- API ---------------------------------------------------------------------------------------


def test_providers_describe_each_dialog_as_plain_data(client):
    spec = next(p for p in client.get("/api/bills/providers").json() if p["id"] == "gepco")
    assert spec["category"] == "electricity" and spec["label"] == "Reference number"
    assert set(spec) >= {"name", "hint", "example", "pattern", "help"}


def test_add_refresh_detail_delete(client, monkeypatch):
    monkeypatch.setattr(service, "fetch_bill", lambda account, answer="", state=None: parsed())
    res = client.post("/api/bills/accounts", json={"adapter_id": "gepco", "consumer_number": "04 12345 6789012", "nickname": "Home"})
    assert res.status_code == 200, res.text
    account = res.json()["account"]
    assert account["consumer_number"] == REF and account["latest"]["amount_due"] == 3831

    detail = client.get(f"/api/bills/accounts/{account['id']}").json()
    assert detail["bill"]["units"] == 80
    assert len(detail["history"]) == 13 and detail["history"][-1]["month"] == "2026-11"  # 12 from the portal + this bill
    assert set(detail["explain"]) == {"en", "ur_roman", "ur"}

    assert client.post(f"/api/bills/accounts/{account['id']}/refresh").status_code == 429  # just fetched
    assert client.post("/api/bills/accounts", json={"adapter_id": "gepco", "consumer_number": REF}).status_code == 400  # duplicate
    assert client.delete(f"/api/bills/accounts/{account['id']}").status_code == 200
    assert client.get("/api/bills/accounts").json() == []


def test_bad_number_and_unknown_company_are_rejected(client):
    assert client.post("/api/bills/accounts", json={"adapter_id": "gepco", "consumer_number": "123"}).status_code == 400
    assert client.post("/api/bills/accounts", json={"adapter_id": "nope", "consumer_number": REF}).status_code == 400


def test_a_failed_first_fetch_leaves_no_account_behind(client, monkeypatch):
    def boom(account, answer="", state=None):
        raise BillError("Portal is down")

    monkeypatch.setattr(service, "fetch_bill", boom)
    res = client.post("/api/bills/accounts", json={"adapter_id": "gepco", "consumer_number": REF})
    assert res.status_code == 502 and "Portal is down" in res.json()["detail"]
    assert client.get("/api/bills/accounts").json() == []


def test_captcha_flow(client, monkeypatch):
    def fake(account, answer="", state=None):
        if state is None:
            return Challenge(image=b"\x89PNG", media_type="image/png", state={"cookies": {}})
        assert answer == "AB12"
        return parsed()

    monkeypatch.setattr(service, "fetch_bill", fake)
    monkeypatch.setattr(bills_routes, "fetch_bill", fake)
    res = client.post("/api/bills/accounts", json={"adapter_id": "gepco", "consumer_number": REF}).json()
    assert res["status"] == "challenge" and res["image"].startswith("data:image/png;base64,")
    account_id = res["account"]["id"]

    assert client.post(f"/api/bills/accounts/{account_id}/challenge", json={"token": "wrong", "answer": "AB12"}).status_code == 410
    done = client.post(f"/api/bills/accounts/{account_id}/challenge", json={"token": res["token"], "answer": "AB12"})
    assert done.status_code == 200 and done.json()["account"]["latest"]["amount_due"] == 3831


def test_accounts_are_private_to_their_owner(client, monkeypatch):
    monkeypatch.setattr(service, "fetch_bill", lambda account, answer="", state=None: parsed())
    account_id = client.post("/api/bills/accounts", json={"adapter_id": "gepco", "consumer_number": REF}).json()["account"]["id"]
    with Session(engine) as session:
        other = User(username="someone-else", password_hash="x", bills_enabled=True)
        session.add(other)
        session.commit()
        session.refresh(other)
    app.dependency_overrides[require_user_api] = lambda: other
    assert client.get(f"/api/bills/accounts/{account_id}").status_code == 404
    assert client.delete(f"/api/bills/accounts/{account_id}").status_code == 404


# ---- the daily check -----------------------------------------------------------------------


class Pushes(list):
    pass


@pytest.fixture()
def pushes(monkeypatch):
    sent = Pushes()
    monkeypatch.setattr(checker, "notify_user", lambda session, user, title, body, url, source: sent.append((title, body)))
    return sent


def make_account(user_id, **record):
    with Session(engine) as session:
        account = BillAccount(user_id=user_id, adapter_id="gepco", consumer_number=REF, nickname="Home")
        session.add(account)
        session.commit()
        session.refresh(account)
        return account.id


def utc(y, m, d, hour):  # Karachi is UTC+5
    return datetime(y, m, d, hour - 5, 0)


def test_new_bill_sends_one_push_and_then_waits(user, monkeypatch, pushes):
    account_id = make_account(user.id)
    monkeypatch.setattr(service, "fetch_bill", lambda account, answer="", state=None: parsed())
    monkeypatch.setattr(checker, "fetch_bill", service.fetch_bill)

    checker.run_checks(utc(2026, 11, 12, 9))
    assert len(pushes) == 1 and "Naya Home bill aa gaya: Rs 3,831" in pushes[0][0]
    checker.run_checks(utc(2026, 11, 12, 15))  # same day again: nothing
    checker.run_checks(utc(2026, 11, 13, 9))  # next day: the bill is found, so it is not fetched again
    assert len(pushes) == 1


def test_nothing_happens_before_8am_local(user, monkeypatch, pushes):
    make_account(user.id)
    monkeypatch.setattr(checker, "fetch_bill", lambda account, answer="", state=None: parsed())
    checker.run_checks(utc(2026, 11, 12, 7))
    assert pushes == []


def test_due_reminder_goes_out_the_day_before_even_after_a_manual_refresh(user, monkeypatch, pushes):
    account_id = make_account(user.id)
    monkeypatch.setattr(checker, "fetch_bill", lambda account, answer="", state=None: parsed())
    checker.run_checks(utc(2026, 11, 12, 9))
    pushes.clear()
    with Session(engine) as session:  # the person refreshed by hand on the 22nd
        account = session.get(BillAccount, account_id)
        account.last_checked_at = utc(2026, 11, 22, 6)
        session.add(account)
        session.commit()
    checker.run_checks(utc(2026, 11, 22, 9))
    assert len(pushes) == 1 and "kal due hai" in pushes[0][0]
    checker.run_checks(utc(2026, 11, 22, 10))
    assert len(pushes) == 1  # once only


def test_three_failures_alert_once(user, monkeypatch, pushes):
    make_account(user.id)

    def boom(account, answer="", state=None):
        raise BillError("down")

    monkeypatch.setattr(checker, "fetch_bill", boom)
    for day in (12, 13, 14, 15, 16):
        checker.run_checks(utc(2026, 11, day, 9))
    assert len(pushes) == 1 and "check nahi ho raha" in pushes[0][0]


def test_a_captcha_in_the_daily_check_asks_the_person_once_a_month(user, monkeypatch, pushes):
    make_account(user.id)
    monkeypatch.setattr(checker, "fetch_bill", lambda account, answer="", state=None: Challenge(image=b"x", state={}))
    checker.run_checks(utc(2026, 11, 12, 9))
    checker.run_checks(utc(2026, 11, 13, 9))
    assert len(pushes) == 1


def test_schedule_window():
    today = date(2026, 11, 9)
    assert checker.why_check(Gepco, None, today) == "new"
    assert checker.why_check(Gepco, None, date(2026, 11, 8)) is None  # window opens 3 days before the 12th


# ---- feature switches -------------------------------------------------------------------------


def test_reminders_switch_hides_the_tab_and_keeps_the_reminders(client, user):
    assert client.get("/api/me").json()["reminders_enabled"] is True  # on for everyone by default
    assert client.put("/api/me/reminders", json={"enabled": False}).json() == {"reminders_enabled": False}
    assert client.get("/api/me").json()["reminders_enabled"] is False
    assert client.put("/api/me/reminders", json={"enabled": True}).json() == {"reminders_enabled": True}
