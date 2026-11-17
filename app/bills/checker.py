"""The daily bill check.

Runs from the scheduler every hour. For each user with Bills on, once their local clock
passes 8 am it looks at each account at most once that day, and only fetches when the
company's schedule says a bill is due to appear (or the day before a bill is due):

  * "new":  from a few days before the company's usual publish day until a bill newer
            than that window shows up. A new bill sends a push.
  * "due":  the day before the due date, unless the portal already says it is paid. Sends
            a reminder (and, where the portal tells us, whether it is still unpaid).
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from sqlmodel import Session, select

from app.bills import explain
from app.bills.base import Adapter, BillError, Challenge
from app.bills.registry import get_adapter
from app.bills.service import account_title, fetch_bill, latest_record, record_bill, save_bill
from app.models import BillAccount, BillRecord, User
from app.push import notify_user

logger = logging.getLogger("notifaybers.bills")

CHECK_HOUR = 8  # local time
FAILURES_BEFORE_ALERT = 3


def _issued(record: BillRecord) -> date:
    """When the latest bill was issued; falls back to the month it was first seen."""
    issue = record_bill(record).get("issue_date")
    if issue:
        return date.fromisoformat(issue[:10])
    return date.fromisoformat(f"{record.bill_month}-01")


def why_check(adapter: type[Adapter], latest: Optional[BillRecord], today: date) -> Optional[str]:
    """"new", "due" or None: should this account be fetched today?"""
    if latest is not None and latest.due_date and not latest.due_alerted and latest.paid is not True:
        if today == date.fromisoformat(latest.due_date) - timedelta(days=1):
            return "due"

    start_day = max(1, (adapter.publish_day or 1) - adapter.check_days_before) if adapter.publish_day else 1
    window_open = date(today.year, today.month, min(start_day, 28))
    if today >= window_open and (latest is None or _issued(latest) < window_open):
        return "new"
    return None


def _local_now(user: User, now_utc: datetime) -> datetime:
    try:
        tz = ZoneInfo(user.timezone or "UTC")
    except Exception:
        tz = ZoneInfo("UTC")
    return now_utc.replace(tzinfo=ZoneInfo("UTC")).astimezone(tz)


def _checked_today(account: BillAccount, user: User, local_today: date) -> bool:
    if account.last_checked_at is None:
        return False
    return _local_now(user, account.last_checked_at).date() == local_today


def check_account(session: Session, user: User, account: BillAccount, reason: str) -> None:
    adapter_class = get_adapter(account.adapter_id)
    if adapter_class is None:
        return
    lang = user.bills_language
    name = account.nickname or adapter_class.name
    account.last_checked_at = datetime.utcnow()
    try:
        result = fetch_bill(account)
    except BillError as error:
        account.last_error = str(error)
        account.failures_in_a_row += 1
        session.add(account)
        session.commit()
        if account.failures_in_a_row >= FAILURES_BEFORE_ALERT and not account.failure_alerted:
            account.failure_alerted = True
            session.add(account)
            session.commit()
            title, body = explain.notice_failure(name, lang)
            notify_user(session, user, title, body, "/bills", "bills")
        return

    if isinstance(result, Challenge):
        # The portal wants a human. Tell the user once a month instead of every day.
        account.last_error = "The portal asked for a code"
        month = date.today().strftime("%Y-%m")
        send = account.captcha_alert_month != month
        account.captcha_alert_month = month
        session.add(account)
        session.commit()
        if send:
            title, body = explain.notice_captcha(name, lang)
            notify_user(session, user, title, body, "/bills", "bills")
        return

    record, is_new = save_bill(session, account, result)
    bill = record_bill(record)
    if is_new and not record.new_alerted:
        record.new_alerted = True
        session.add(record)
        session.commit()
        title, body = explain.notice_new(bill, name, lang)
        notify_user(session, user, title, body, "/bills", "bills")
    if reason == "due":
        send_due_reminder(session, user, account, record)


def send_due_reminder(session: Session, user: User, account: BillAccount, record: BillRecord) -> None:
    """The "due tomorrow" push. Sent once per bill, and not at all once it is known to be paid."""
    if record.due_alerted:
        return
    record.due_alerted = True
    session.add(record)
    session.commit()
    if record.paid is not True:
        name = account.nickname or (get_adapter(account.adapter_id).name if get_adapter(account.adapter_id) else "")
        title, body = explain.notice_due(record_bill(record), name, record.paid, user.bills_language)
        notify_user(session, user, title, body, "/bills", "bills")


def run_checks(now_utc: Optional[datetime] = None) -> None:
    from app.db import engine

    now_utc = now_utc or datetime.utcnow()
    with Session(engine) as session:
        users = session.exec(select(User).where(User.bills_enabled == True, User.is_active == True)).all()  # noqa: E712
        for user in users:
            local = _local_now(user, now_utc)
            if local.hour < CHECK_HOUR:
                continue
            accounts = session.exec(select(BillAccount).where(BillAccount.user_id == user.id)).all()
            for account in accounts:
                try:
                    adapter_class = get_adapter(account.adapter_id)
                    if adapter_class is None:
                        continue
                    latest = latest_record(session, account.id)
                    reason = why_check(adapter_class, latest, local.date())
                    if reason is None:
                        continue
                    if _checked_today(account, user, local.date()):
                        # Already fetched today (for example by a manual refresh): do not ask the
                        # portal again, but a due reminder must still go out from what we saved.
                        if reason == "due":
                            send_due_reminder(session, user, account, latest)
                        continue
                    check_account(session, user, account, reason)
                except Exception:
                    logger.exception("bill check failed for account %s", account.id)
