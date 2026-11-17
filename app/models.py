from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    password_hash: str
    email: Optional[str] = Field(default=None, index=True, unique=True)
    google_sub: Optional[str] = Field(default=None, index=True, unique=True)
    name: Optional[str] = None
    timezone: str = Field(default="UTC")
    watchdogs_enabled: bool = Field(default=False)
    reminders_enabled: bool = Field(default=True)
    bills_enabled: bool = Field(default=False)
    bills_language: str = Field(default="ur_roman")  # en | ur_roman | ur: language of bill text and pushes
    openai_api_key: Optional[str] = None
    openai_base_url: Optional[str] = "https://api.openai.com/v1"
    openai_model: Optional[str] = "gpt-4o-mini"
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class LoginAttempt(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True)
    ip: str
    success: bool
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class PushSubscription(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    endpoint: str = Field(unique=True)
    p256dh: str
    auth: str
    user_agent: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_used_at: Optional[datetime] = None


class ApiKey(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    name: str
    key_prefix: str
    key_hash: str = Field(unique=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_used_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None


class Reminder(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    title: str
    body: Optional[str] = None
    url: Optional[str] = None
    category: Optional[str] = None
    schedule_type: str
    schedule_value: str
    enabled: bool = Field(default=True)
    next_run_at: Optional[datetime] = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Watchdog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    name: str
    token: str = Field(unique=True, index=True)
    ping_interval_seconds: int = Field(default=86400)
    grace_period_seconds: int = Field(default=300)
    last_ping_at: Optional[datetime] = None
    status: str = Field(default="pending")  # pending, healthy, down, paused
    alert_sent: bool = Field(default=False)
    enabled: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class NotificationLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    source: str
    title: str
    body: Optional[str] = None
    status: str
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class BillAccount(SQLModel, table=True):
    """One consumer number at one company, e.g. "Home" at GEPCO."""

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    adapter_id: str  # which adapter fetches it, e.g. "gepco"
    consumer_number: str
    nickname: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_checked_at: Optional[datetime] = None  # last attempt, successful or not
    last_success_at: Optional[datetime] = None
    last_error: Optional[str] = None
    failures_in_a_row: int = Field(default=0)
    failure_alerted: bool = Field(default=False)
    captcha_alert_month: Optional[str] = None  # "2026-11": the "needs you" push was sent this month


class BillRecord(SQLModel, table=True):
    """One fetched bill. Re-fetching the same month updates the row."""

    id: Optional[int] = Field(default=None, primary_key=True)
    account_id: int = Field(foreign_key="billaccount.id", index=True)
    bill_month: str = Field(index=True)  # "2026-11"
    due_date: Optional[str] = None  # ISO date
    amount_due: float = 0
    amount_after_due: Optional[float] = None
    units: Optional[float] = None
    paid: Optional[bool] = None
    data: str = "{}"  # the full normalized Bill as JSON
    fetched_at: datetime = Field(default_factory=datetime.utcnow)
    new_alerted: bool = Field(default=False)  # "new bill" push sent
    due_alerted: bool = Field(default=False)  # "due tomorrow" push sent
