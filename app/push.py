import json
import logging

from pywebpush import WebPushException, webpush
from sqlmodel import Session, select

from app.config import settings
from app.models import NotificationLog, PushSubscription, User

logger = logging.getLogger("notifaybers.push")


def _send_to_subscription(sub: PushSubscription, payload: dict) -> str:
    try:
        webpush(
            subscription_info={
                "endpoint": sub.endpoint,
                "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
            },
            data=json.dumps(payload),
            vapid_private_key=settings.vapid_private_key_path,
            vapid_claims={"sub": settings.vapid_subject},
        )
        return "ok"
    except WebPushException as exc:
        status = exc.response.status_code if exc.response is not None else None
        if status in (404, 410):
            return "gone"
        logger.warning("push failed (status=%s): %s", status, exc)
        return "error"


def notify_user(
    session: Session,
    user: User,
    title: str,
    body: str | None,
    url: str | None,
    source: str,
) -> str:
    subs = session.exec(
        select(PushSubscription).where(PushSubscription.user_id == user.id)
    ).all()

    if not subs:
        status = "no_subscriptions"
    else:
        payload = {"title": title, "body": body or "", "url": url or "/"}
        results = []
        for sub in subs:
            result = _send_to_subscription(sub, payload)
            results.append(result)
            if result == "gone":
                session.delete(sub)
            elif result == "ok":
                from datetime import datetime

                sub.last_used_at = datetime.utcnow()
                session.add(sub)
        session.commit()
        status = "sent" if "ok" in results else "failed"

    session.add(
        NotificationLog(
            user_id=user.id,
            source=source,
            title=title,
            body=body,
            status=status,
        )
    )
    session.commit()
    return status
