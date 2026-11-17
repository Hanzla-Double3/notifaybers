"""Glue between adapters and the database: serialize bills, hold CAPTCHA sessions, save results."""

from __future__ import annotations

import base64
import dataclasses
import json
import secrets
import threading
import time
from datetime import date, datetime
from typing import Optional, Union

from sqlmodel import Session, select

from app.bills.base import Bill, BillError, Challenge
from app.bills.http import PolicyClient
from app.bills.registry import get_adapter
from app.models import BillAccount, BillRecord

CHALLENGE_TTL_SECONDS = 600
MAX_CHALLENGES = 50


# ---- serialization ---------------------------------------------------------------------


def _json_default(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    raise TypeError(f"cannot serialize {type(value)}")


def bill_to_dict(bill: Bill) -> dict:
    return json.loads(json.dumps(dataclasses.asdict(bill), default=_json_default))


def record_bill(record: BillRecord) -> dict:
    return json.loads(record.data or "{}")


# ---- CAPTCHA sessions kept in memory (they are short-lived and tied to the portal session) ---

_challenges: dict[str, dict] = {}
_lock = threading.Lock()


def _remember_challenge(user_id: int, account_id: int, challenge: Challenge) -> str:
    now = time.time()
    with _lock:
        for token in [t for t, c in _challenges.items() if now - c["at"] > CHALLENGE_TTL_SECONDS]:
            del _challenges[token]
        while len(_challenges) >= MAX_CHALLENGES:
            del _challenges[min(_challenges, key=lambda t: _challenges[t]["at"])]
        token = secrets.token_urlsafe(24)
        _challenges[token] = {"at": now, "user_id": user_id, "account_id": account_id, "state": challenge.state}
    return token


def take_challenge(token: str, user_id: int, account_id: int) -> Optional[dict]:
    with _lock:
        entry = _challenges.get(token)
        if entry is None or entry["user_id"] != user_id or entry["account_id"] != account_id:
            return None
        if time.time() - entry["at"] > CHALLENGE_TTL_SECONDS:
            del _challenges[token]
            return None
        return entry["state"]


def finish_challenge(token: str) -> None:
    with _lock:
        _challenges.pop(token, None)


def challenge_payload(token: str, challenge: Challenge) -> dict:
    image = base64.b64encode(challenge.image).decode()
    return {
        "status": "challenge",
        "token": token,
        "image": f"data:{challenge.media_type};base64,{image}",
        "prompt": challenge.prompt,
    }


# ---- fetching ---------------------------------------------------------------------------


def fetch_bill(account: BillAccount, answer: str = "", state: Optional[dict] = None) -> Union[Bill, Challenge]:
    """Run the account's adapter. Raises BillError with a message the user can read."""
    adapter_class = get_adapter(account.adapter_id)
    if adapter_class is None:
        raise BillError("This company is no longer supported")
    adapter = adapter_class()
    http = PolicyClient(adapter_class, cookies=(state or {}).get("cookies"))
    try:
        return adapter.fetch(http, account.consumer_number, answer=answer, state=state)
    finally:
        http.close()


def begin_fetch(session: Session, account: BillAccount) -> tuple[Union[Bill, Challenge], Optional[str]]:
    """First call for an account. Returns (bill, None) or (challenge, token)."""
    result = fetch_bill(account)
    if isinstance(result, Challenge):
        return result, _remember_challenge(account.user_id, account.id, result)
    return result, None


# ---- saving -----------------------------------------------------------------------------


def save_bill(session: Session, account: BillAccount, bill: Bill) -> tuple[BillRecord, bool]:
    """Store a fetched bill. Returns (record, is_new): is_new is False when this month was already saved."""
    month = bill.bill_month.strftime("%Y-%m")
    record = session.exec(
        select(BillRecord).where(BillRecord.account_id == account.id, BillRecord.bill_month == month)
    ).first()
    is_new = record is None
    if record is None:
        record = BillRecord(account_id=account.id, bill_month=month)
    record.due_date = bill.due_date.isoformat() if bill.due_date else None
    record.amount_due = bill.amount_due
    record.amount_after_due = bill.amount_after_due
    record.units = bill.units
    record.paid = bill.paid if bill.paid is not None else record.paid
    record.data = json.dumps(bill_to_dict(bill))
    record.fetched_at = datetime.utcnow()
    session.add(record)
    now = datetime.utcnow()
    account.last_checked_at = now
    account.last_success_at = now
    account.last_error = None
    account.failures_in_a_row = 0
    account.failure_alerted = False
    session.add(account)
    session.commit()
    session.refresh(record)
    return record, is_new


def latest_record(session: Session, account_id: int) -> Optional[BillRecord]:
    return session.exec(
        select(BillRecord).where(BillRecord.account_id == account_id).order_by(BillRecord.bill_month.desc())
    ).first()


def account_title(account: BillAccount) -> str:
    adapter_class = get_adapter(account.adapter_id)
    company = adapter_class.name if adapter_class else account.adapter_id
    return f"{account.nickname} · {company}" if account.nickname else company
