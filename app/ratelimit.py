import time
from collections import defaultdict, deque
from datetime import datetime, timedelta

from sqlmodel import Session, select

from app.config import settings
from app.models import LoginAttempt


def check_login_allowed(session: Session, username: str) -> tuple[bool, int]:
    window_start = datetime.utcnow() - timedelta(minutes=settings.login_window_minutes)
    attempts = session.exec(
        select(LoginAttempt).where(
            LoginAttempt.username == username,
            LoginAttempt.success == False,  # noqa: E712
            LoginAttempt.created_at >= window_start,
        )
    ).all()
    if len(attempts) < settings.login_max_attempts:
        return True, 0
    oldest = min(a.created_at for a in attempts)
    retry_after = int(
        (oldest + timedelta(minutes=settings.login_window_minutes) - datetime.utcnow()).total_seconds()
    )
    return False, max(retry_after, 1)


def record_login_attempt(session: Session, username: str, ip: str, success: bool) -> None:
    session.add(LoginAttempt(username=username, ip=ip, success=success))
    session.commit()


_webhook_hits: dict[int, deque] = defaultdict(deque)


def check_webhook_rate_limit(api_key_id: int) -> bool:
    now = time.monotonic()
    window = 60.0
    hits = _webhook_hits[api_key_id]
    while hits and now - hits[0] > window:
        hits.popleft()
    if len(hits) >= settings.webhook_rate_limit_per_minute:
        return False
    hits.append(now)
    return True
