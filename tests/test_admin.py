import base64
import json
from datetime import datetime, timedelta

import itsdangerous
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.config import settings
from app.db import engine, init_db, promote_configured_admin
from app.deps import ACTIVE_TOUCH_INTERVAL
from app.main import app
from app.models import User


def login_as(client: TestClient, user_id: int) -> None:
    """Put a signed session cookie on the client, the way SessionMiddleware would."""
    data = base64.b64encode(json.dumps({"user_id": user_id}).encode())
    cookie = itsdangerous.TimestampSigner(settings.secret_key).sign(data).decode()
    client.cookies.clear()
    client.cookies.set("notifaybers_session", cookie)


@pytest.fixture()
def users():
    init_db()
    with Session(engine) as session:
        for u in session.exec(select(User)).all():
            if u.username != settings.admin_username:
                session.delete(u)
        session.commit()
        admin = session.exec(select(User).where(User.username == settings.admin_username)).first()
        admin.timezone = "Asia/Karachi"
        session.add(admin)
        for i in range(25):
            session.add(
                User(
                    username=f"person{i:02d}@example.com",
                    email=f"person{i:02d}@example.com",
                    password_hash="x",
                    created_at=datetime(2026, 11, 1, 12, 0) + timedelta(hours=i),
                    last_active_at=None if i < 3 else datetime(2026, 11, 10, 12, 0) + timedelta(hours=i),
                )
            )
        session.commit()
        session.refresh(admin)
        regular = session.exec(select(User).where(User.username == "person24@example.com")).one()
        return {"admin_id": admin.id, "regular_id": regular.id}


@pytest.fixture()
def client():
    return TestClient(app, follow_redirects=False)


def test_the_configured_account_is_an_admin_and_others_are_not(users):
    with Session(engine) as session:
        admin = session.get(User, users["admin_id"])
        regular = session.get(User, users["regular_id"])
        assert admin.is_admin is True
        assert regular.is_admin is False


def test_promotion_by_admin_email_only_promotes(users, monkeypatch):
    monkeypatch.setattr(settings, "admin_email", "person05@example.com")
    with Session(engine) as session:
        promote_configured_admin(session)
        person = session.exec(select(User).where(User.email == "person05@example.com")).one()
        assert person.is_admin is True
        assert session.get(User, users["admin_id"]).is_admin is True  # nobody is demoted
        other = session.exec(select(User).where(User.email == "person06@example.com")).one()
        assert other.is_admin is False


def test_users_page_needs_login(client, users):
    response = client.get("/admin/users")
    assert response.status_code == 303 and response.headers["location"] == "/login"


def test_users_page_is_closed_to_regular_users(client, users):
    login_as(client, users["regular_id"])
    response = client.get("/admin/users")
    assert response.status_code == 303 and response.headers["location"] == "/settings"


def test_users_page_lists_emails_paginated_with_last_active(client, users):
    login_as(client, users["admin_id"])
    first = client.get("/admin/users")
    assert first.status_code == 200
    assert "26 signed up" in first.text
    assert "Page 1 of 2" in first.text
    # Most recently active first: person24 was last active 10 Nov 12:00 + 24h = 11 Nov 12:00 UTC (17:00 in Karachi).
    assert first.text.index("person24@example.com") < first.text.index("person23@example.com")
    assert "11 Nov 2026, 17:00" in first.text
    assert first.text.count('class="list-item admin-user"') == 20

    second = client.get("/admin/users?page=2")
    assert "Page 2 of 2" in second.text
    assert second.text.count('class="list-item admin-user"') == 6
    # People who never came back are last, shown as "Never".
    assert second.text.index("person00@example.com") > second.text.index("person03@example.com")
    assert "Never" in second.text


def test_page_number_is_clamped(client, users):
    login_as(client, users["admin_id"])
    assert "Page 2 of 2" in client.get("/admin/users?page=99").text
    assert client.get("/admin/users?page=0").status_code == 422


def test_settings_link_only_for_admins(client, users):
    login_as(client, users["regular_id"])
    assert 'href="/admin/users"' not in client.get("/settings").text
    login_as(client, users["admin_id"])
    assert 'href="/admin/users"' in client.get("/settings").text


def test_me_reports_is_admin(client, users):
    login_as(client, users["admin_id"])
    assert client.get("/api/me").json()["is_admin"] is True
    login_as(client, users["regular_id"])
    assert client.get("/api/me").json()["is_admin"] is False


def test_last_active_is_recorded_but_not_on_every_request(client, users):
    login_as(client, users["regular_id"])
    with Session(engine) as session:
        u = session.get(User, users["regular_id"])
        u.last_active_at = None
        session.add(u)
        session.commit()
    client.get("/api/me")
    with Session(engine) as session:
        stamp = session.get(User, users["regular_id"]).last_active_at
    assert stamp is not None and datetime.utcnow() - stamp < timedelta(minutes=1)

    # A request inside the interval leaves it alone...
    client.get("/api/me")
    with Session(engine) as session:
        assert session.get(User, users["regular_id"]).last_active_at == stamp

    # ...and one after the interval moves it on.
    with Session(engine) as session:
        u = session.get(User, users["regular_id"])
        u.last_active_at = datetime.utcnow() - ACTIVE_TOUCH_INTERVAL - timedelta(minutes=1)
        session.add(u)
        session.commit()
    client.get("/api/me")
    with Session(engine) as session:
        assert datetime.utcnow() - session.get(User, users["regular_id"]).last_active_at < timedelta(minutes=1)
