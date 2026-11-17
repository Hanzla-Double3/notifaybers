from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from app.db import get_session
from app.deps import get_api_key_user
from app.models import ApiKey, User
from app.push import notify_user
from app.ratelimit import check_webhook_rate_limit

router = APIRouter(prefix="/api")


class WebhookPayload(BaseModel):
    title: str
    body: str | None = None
    url: str | None = None


@router.post("/webhook")
def webhook(
    payload: WebhookPayload,
    session: Session = Depends(get_session),
    user_key: tuple[User, ApiKey] = Depends(get_api_key_user),
):
    user, api_key = user_key

    if not check_webhook_rate_limit(api_key.id):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    api_key.last_used_at = datetime.utcnow()
    session.add(api_key)
    session.commit()

    status = notify_user(
        session, user, title=payload.title, body=payload.body, url=payload.url, source="webhook"
    )
    return {"status": status}
