from datetime import date
from pathlib import Path

import httpx
import pytest

from app.bills.adapters.gepco import Gepco
from app.bills.adapters.pitc import parse_pitc_bill
from app.bills.base import Bill, BillError, Challenge
from app.bills.http import PolicyClient
from app.bills.registry import all_adapters, get_adapter

FIXTURE = (Path(__file__).parent / "fixtures" / "pitc_gepco_bill.html").read_text(encoding="utf-8")
REF = "04123456789012"


def charge(bill: Bill, key: str) -> float:
    return next(c.amount for c in bill.charges if c.key == key)


def test_parses_the_headline_numbers():
    bill = parse_pitc_bill(FIXTURE, "gepco", REF)
    assert bill.bill_month == date(2026, 11, 1)
    assert bill.due_date == date(2026, 11, 23)
    assert bill.issue_date == date(2026, 11, 12)
    assert bill.amount_due == 3831
    assert bill.amount_after_due == 4096
    assert bill.units == 80
    assert (bill.previous_reading, bill.present_reading) == (16735, 16815)
    assert bill.tariff == "A-1A(01)"
    assert bill.extra["late_payment"][0] == {"surcharge": 133.0, "period": "Till 26-NOV-26", "payable": 3964.0}


def test_breakdown_adds_up():
    bill = parse_pitc_bill(FIXTURE, "gepco", REF)
    assert charge(bill, "electricity") - charge(bill, "subsidies") == charge(bill, "net_electricity")
    assert charge(bill, "net_electricity") + charge(bill, "taxes") == charge(bill, "current_bill")
    assert charge(bill, "current_bill") + charge(bill, "fpa") == charge(bill, "grand_total") == bill.amount_due


def test_history_is_oldest_first_and_complete():
    bill = parse_pitc_bill(FIXTURE, "gepco", REF)
    assert len(bill.history) == 12
    assert bill.history[0].month == date(2025, 11, 1)
    assert bill.history[-1].month == date(2026, 10, 1)
    assert (bill.history[-1].units, bill.history[-1].billed, bill.history[-1].paid) == (203, 10061, 10061)


def test_hidden_detail_block_is_read_and_identifiers_stay_text():
    details = parse_pitc_bill(FIXTURE, "gepco", REF).extra["details"]
    assert details["energy details"]["variable chrg"] == 1795.2
    assert details["taxes"]["gst"] == 481
    assert details["fpa details"]["total"] == 677.27
    assert details["consumer details"]["ref no"] == REF  # not turned into a float
    assert details["bill calc"]["lines"] == ["22.4400 X 80", "275 X 2"]


def test_paid_is_unknown_until_history_shows_a_payment_for_this_month():
    assert parse_pitc_bill(FIXTURE, "gepco", REF).paid is None


def test_not_a_bill_page_raises():
    with pytest.raises(BillError):
        parse_pitc_bill("<html><body>Enter the code from the image</body></html>", "gepco", REF)


# ---- fetching -------------------------------------------------------------------------


def _client(handler):
    return PolicyClient(Gepco, transport=httpx.MockTransport(handler))


def test_direct_post_returns_a_bill():
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append((request.method, str(request.url)))
        return httpx.Response(200, text=FIXTURE)

    result = Gepco().fetch(_client(handler), REF)
    assert isinstance(result, Bill) and result.amount_due == 3831
    assert seen == [("POST", f"https://bill.pitc.com.pk/gepcobill/general/{REF}")]


def test_falls_back_to_a_captcha_challenge_when_the_portal_asks_for_one():
    form = (
        '<form id="SubmitForm"><input type="hidden" name="__VIEWSTATE" value="vs"/>'
        '<img id="captchaImage" src="/CaptchaImageHandler.ashx?t=1"/></form>'
    )

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(302, headers={"location": "/gepcobill"})
        if request.url.path == "/gepcobill":
            return httpx.Response(200, text=form)
        return httpx.Response(200, content=b"\x89PNG", headers={"content-type": "image/png"})

    challenge = Gepco().fetch(_client(handler), REF)
    assert isinstance(challenge, Challenge)
    assert challenge.image == b"\x89PNG" and challenge.state["hidden"] == {"__VIEWSTATE": "vs"}


def test_second_call_posts_the_users_answer():
    posted = {}

    def handler(request: httpx.Request) -> httpx.Response:
        posted.update(dict(x.split("=", 1) for x in request.content.decode().split("&")))
        return httpx.Response(200, text=FIXTURE)

    state = {"hidden": {"__VIEWSTATE": "vs"}, "cookies": {}}
    bill = Gepco().fetch(_client(handler), REF, answer="AB12", state=state)
    assert isinstance(bill, Bill)
    assert posted["captchaInput"] == "AB12" and posted["searchTextBox"] == REF


def test_a_wrong_answer_is_reported():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="<html>Invalid captcha</html>")

    with pytest.raises(BillError):
        Gepco().fetch(_client(handler), REF, answer="nope", state={"hidden": {}, "cookies": {}})


# ---- framework --------------------------------------------------------------------------


def test_client_refuses_hosts_the_adapter_did_not_declare():
    client = _client(lambda request: httpx.Response(200))
    with pytest.raises(BillError):
        client.get("https://example.com/")
    with pytest.raises(BillError):
        client.get("http://bill.pitc.com.pk/gepcobill")  # https only


def test_client_checks_every_redirect_hop():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"location": "https://evil.example/steal"})

    with pytest.raises(BillError):
        _client(handler).get("https://bill.pitc.com.pk/gepcobill")


def test_registry_finds_gepco_and_validates_numbers():
    assert "gepco" in all_adapters()
    gepco = get_adapter("gepco")
    assert gepco.valid_number("04123456789012") and gepco.valid_number("04 12345 6789012")
    assert not gepco.valid_number("12345") and not gepco.valid_number("not a number")
