import re
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.bills import explain
from app.bills.base import BillError, Challenge
from app.bills.registry import all_adapters, get_adapter
from app.bills.service import (
    account_title,
    begin_fetch,
    challenge_payload,
    fetch_bill,
    finish_challenge,
    latest_record,
    record_bill,
    save_bill,
    take_challenge,
)
from app.db import get_session
from app.deps import require_user_api
from app.models import BillAccount, BillRecord, User

router = APIRouter(prefix="/api")

MIN_SECONDS_BETWEEN_FETCHES = 60  # one account is not asked of the portal more often than this
MAX_ACCOUNTS_PER_USER = 20


# ---------- settings ----------


class BillsSettingsUpdate(BaseModel):
    enabled: Optional[bool] = None
    language: Optional[str] = None


@router.put("/me/bills")
def update_bills_settings(
    body: BillsSettingsUpdate,
    user: User = Depends(require_user_api),
    session: Session = Depends(get_session),
):
    if body.enabled is not None:
        user.bills_enabled = body.enabled
    if body.language is not None:
        if body.language not in explain.LANGS:
            raise HTTPException(status_code=400, detail="Unknown language")
        user.bills_language = body.language
    session.add(user)
    session.commit()
    return {"bills_enabled": user.bills_enabled, "bills_language": user.bills_language}


# ---------- providers ----------


@router.get("/bills/providers")
def list_providers(user: User = Depends(require_user_api)):
    """Every company the app can fetch, with what its "add account" dialog should ask for."""
    return sorted((a.form_spec() for a in all_adapters().values()), key=lambda s: (s["category"], s["name"]))


# ---------- accounts ----------


def _owned(session: Session, user: User, account_id: int) -> BillAccount:
    account = session.get(BillAccount, account_id)
    if account is None or account.user_id != user.id:
        raise HTTPException(status_code=404, detail="Account not found")
    return account


def _summary(record: Optional[BillRecord]) -> Optional[dict]:
    if record is None:
        return None
    return {
        "bill_month": record.bill_month,
        "due_date": record.due_date,
        "amount_due": record.amount_due,
        "amount_after_due": record.amount_after_due,
        "units": record.units,
        "paid": record.paid,
        "fetched_at": record.fetched_at.isoformat() + "Z",
    }


def _account_out(session: Session, account: BillAccount) -> dict:
    adapter_class = get_adapter(account.adapter_id)
    return {
        "id": account.id,
        "adapter_id": account.adapter_id,
        "company": adapter_class.name if adapter_class else account.adapter_id,
        "category": adapter_class.category if adapter_class else "other",
        "title": account_title(account),
        "nickname": account.nickname,
        "consumer_number": account.consumer_number,
        "last_checked_at": account.last_checked_at.isoformat() + "Z" if account.last_checked_at else None,
        "last_error": account.last_error,
        "latest": _summary(latest_record(session, account.id)),
    }


@router.get("/bills/accounts")
def list_accounts(user: User = Depends(require_user_api), session: Session = Depends(get_session)):
    accounts = session.exec(
        select(BillAccount).where(BillAccount.user_id == user.id).order_by(BillAccount.created_at)
    ).all()
    return [_account_out(session, a) for a in accounts]


class AccountIn(BaseModel):
    adapter_id: str
    consumer_number: str
    nickname: str = ""


@router.post("/bills/accounts")
def add_account(
    body: AccountIn,
    user: User = Depends(require_user_api),
    session: Session = Depends(get_session),
):
    adapter_class = get_adapter(body.adapter_id)
    if adapter_class is None:
        raise HTTPException(status_code=400, detail="Unknown company")
    number = body.consumer_number.strip()
    if not adapter_class.valid_number(number):
        raise HTTPException(status_code=400, detail=f"{adapter_class.input_label}: {adapter_class.input_hint}")
    count = len(session.exec(select(BillAccount).where(BillAccount.user_id == user.id)).all())
    if count >= MAX_ACCOUNTS_PER_USER:
        raise HTTPException(status_code=400, detail=f"At most {MAX_ACCOUNTS_PER_USER} accounts")
    normalized = re.sub(r"\s+", "", number)
    duplicate = session.exec(
        select(BillAccount).where(
            BillAccount.user_id == user.id,
            BillAccount.adapter_id == body.adapter_id,
            BillAccount.consumer_number == normalized,
        )
    ).first()
    if duplicate is not None:
        raise HTTPException(status_code=400, detail="You already added this number")

    account = BillAccount(
        user_id=user.id,
        adapter_id=body.adapter_id,
        consumer_number=normalized,
        nickname=body.nickname.strip()[:40],
    )
    session.add(account)
    session.commit()
    session.refresh(account)
    return _run_fetch(session, account, discard_on_error=True)


def _run_fetch(session: Session, account: BillAccount, discard_on_error: bool = False) -> dict:
    """Fetch now. A bill is saved, or the CAPTCHA is returned for the user to answer."""
    try:
        result, token = begin_fetch(session, account)
    except BillError as error:
        if discard_on_error:
            session.delete(account)
            session.commit()
        else:
            account.last_checked_at = datetime.utcnow()
            account.last_error = str(error)
            session.add(account)
            session.commit()
        raise HTTPException(status_code=502, detail=str(error))
    if isinstance(result, Challenge):
        out = challenge_payload(token, result)
        out["account"] = _account_out(session, account)
        return out
    save_bill(session, account, result)
    return {"status": "ok", "account": _account_out(session, account)}


@router.post("/bills/accounts/{account_id}/refresh")
def refresh_account(
    account_id: int,
    user: User = Depends(require_user_api),
    session: Session = Depends(get_session),
):
    account = _owned(session, user, account_id)
    if account.last_checked_at and (datetime.utcnow() - account.last_checked_at).total_seconds() < MIN_SECONDS_BETWEEN_FETCHES:
        raise HTTPException(status_code=429, detail="Checked a moment ago. Try again in a minute.")
    return _run_fetch(session, account)


class ChallengeAnswer(BaseModel):
    token: str
    answer: str


@router.post("/bills/accounts/{account_id}/challenge")
def answer_challenge(
    account_id: int,
    body: ChallengeAnswer,
    user: User = Depends(require_user_api),
    session: Session = Depends(get_session),
):
    account = _owned(session, user, account_id)
    state = take_challenge(body.token, user.id, account.id)
    if state is None:
        raise HTTPException(status_code=410, detail="That code expired. Start again.")
    try:
        result = fetch_bill(account, answer=body.answer, state=state)
    except BillError as error:
        finish_challenge(body.token)
        raise HTTPException(status_code=502, detail=str(error))
    finish_challenge(body.token)
    if isinstance(result, Challenge):
        raise HTTPException(status_code=502, detail="The portal asked again. Try once more.")
    save_bill(session, account, result)
    return {"status": "ok", "account": _account_out(session, account)}


class AccountUpdate(BaseModel):
    nickname: str


@router.put("/bills/accounts/{account_id}")
def update_account(
    account_id: int,
    body: AccountUpdate,
    user: User = Depends(require_user_api),
    session: Session = Depends(get_session),
):
    account = _owned(session, user, account_id)
    account.nickname = body.nickname.strip()[:40]
    session.add(account)
    session.commit()
    return _account_out(session, account)


@router.delete("/bills/accounts/{account_id}")
def delete_account(
    account_id: int,
    user: User = Depends(require_user_api),
    session: Session = Depends(get_session),
):
    account = _owned(session, user, account_id)
    for record in session.exec(select(BillRecord).where(BillRecord.account_id == account.id)).all():
        session.delete(record)
    session.delete(account)
    session.commit()
    return {"status": "deleted", "id": account_id}


@router.get("/bills/accounts/{account_id}")
def account_detail(
    account_id: int,
    user: User = Depends(require_user_api),
    session: Session = Depends(get_session),
):
    account = _owned(session, user, account_id)
    record = latest_record(session, account.id)
    out = _account_out(session, account)
    if record is None:
        return {**out, "bill": None, "explain": {}, "history": []}
    bill = record_bill(record)

    # Chart rows: the portal's own history, plus months we saved ourselves that it does not list.
    rows = {h["month"][:7]: {"month": h["month"][:7], "units": h["units"], "billed": h["billed"], "paid": h["paid"]} for h in bill.get("history", [])}
    for saved in session.exec(select(BillRecord).where(BillRecord.account_id == account.id)).all():
        data = record_bill(saved)
        current = next((c["amount"] for c in data.get("charges", []) if c["key"] == "current_bill"), saved.amount_due)
        rows.setdefault(saved.bill_month, {"month": saved.bill_month, "units": saved.units, "billed": current, "paid": None})
    history = sorted(rows.values(), key=lambda r: r["month"])

    return {
        **out,
        "bill": bill,
        "paid": record.paid,
        "explain": {lang: explain.explain(bill, lang) for lang in explain.LANGS},
        "history": history,
    }
