import json
import logging
import secrets
from datetime import datetime
from zoneinfo import ZoneInfo, available_timezones

import requests
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlmodel import Session, select

from app.ai import chat_with_llm, execute_tool, get_mcp_manifest
from app.config import settings
from app.db import get_session
from app.deps import public_base_url, require_user_api
from app.models import ApiKey, NotificationLog, PushSubscription, Reminder, User, Watchdog
from app.push import notify_user
from app.reminders import compute_next_run, snooze_target, validate_schedule
from app.security import generate_api_key, hash_api_key

router = APIRouter(prefix="/api")


# ---------- me ----------

@router.get("/me")
def get_me(request: Request, user: User = Depends(require_user_api)):
    return {
        "public_base_url": public_base_url(request),
        "username": user.username,
        "timezone": user.timezone,
        "watchdogs_enabled": user.watchdogs_enabled,
        "watchdog_min_ping_seconds": settings.watchdog_min_ping_seconds,
        "has_openai_key": bool(user.openai_api_key and user.openai_api_key.strip()),
        "openai_base_url": user.openai_base_url or "https://api.openai.com/v1",
        "openai_model": user.openai_model or "gpt-4o-mini",
    }


class TimezoneUpdate(BaseModel):
    timezone: str


@router.put("/me/timezone")
def update_timezone(
    body: TimezoneUpdate,
    user: User = Depends(require_user_api),
    session: Session = Depends(get_session),
):
    if body.timezone not in available_timezones():
        raise HTTPException(status_code=400, detail="Unknown timezone")
    user.timezone = body.timezone
    session.add(user)

    reminders = session.exec(
        select(Reminder).where(Reminder.user_id == user.id, Reminder.enabled == True)  # noqa: E712
    ).all()
    for reminder in reminders:
        value = json.loads(reminder.schedule_value)
        reminder.next_run_at = compute_next_run(reminder.schedule_type, value, user.timezone)
        session.add(reminder)

    session.commit()
    return {"timezone": user.timezone}


@router.get("/timezones")
def list_timezones():
    return sorted(available_timezones())


class AiSettingsUpdate(BaseModel):
    openai_api_key: str | None = None
    openai_base_url: str | None = "https://api.openai.com/v1"
    openai_model: str | None = "gpt-4o-mini"


@router.put("/me/ai")
def update_ai_settings(
    body: AiSettingsUpdate,
    user: User = Depends(require_user_api),
    session: Session = Depends(get_session),
):
    if body.openai_api_key is not None:
        user.openai_api_key = body.openai_api_key.strip()
    if body.openai_base_url:
        user.openai_base_url = body.openai_base_url.strip()
    if body.openai_model:
        user.openai_model = body.openai_model.strip()
    session.add(user)
    session.commit()
    return {
        "status": "saved",
        "has_openai_key": bool(user.openai_api_key and user.openai_api_key.strip()),
        "openai_base_url": user.openai_base_url,
        "openai_model": user.openai_model,
    }


@router.post("/me/ai/test")
def test_ai_settings(
    body: AiSettingsUpdate,
    user: User = Depends(require_user_api),
):
    key = (body.openai_api_key or user.openai_api_key or "").strip()
    if not key:
        raise HTTPException(status_code=400, detail="OpenAI API key cannot be empty")
    base_url = (body.openai_base_url or user.openai_base_url or "https://api.openai.com/v1").rstrip("/")
    model = (body.openai_model or user.openai_model or "gpt-4o-mini").strip()

    try:
        resp = requests.post(
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"model": model, "messages": [{"role": "user", "content": "ping"}], "max_tokens": 5},
            timeout=10,
        )
        resp.raise_for_status()
        return {"status": "ok", "model": model}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Connection failed: {exc}")


class WatchdogFeatureUpdate(BaseModel):
    enabled: bool


@router.put("/me/watchdogs")
def update_watchdog_feature(
    body: WatchdogFeatureUpdate,
    user: User = Depends(require_user_api),
    session: Session = Depends(get_session),
):
    user.watchdogs_enabled = body.enabled
    session.add(user)
    session.commit()
    return {"watchdogs_enabled": user.watchdogs_enabled}


# ---------- push subscriptions ----------

@router.get("/vapid-public-key")
def vapid_public_key():
    return {"publicKey": settings.vapid_public_key}


class SubscriptionIn(BaseModel):
    endpoint: str
    keys: dict
    user_agent: str | None = None


@router.get("/subscriptions")
def list_subscriptions(
    user: User = Depends(require_user_api), session: Session = Depends(get_session)
):
    subs = session.exec(
        select(PushSubscription).where(PushSubscription.user_id == user.id)
    ).all()
    return [
        {
            "id": s.id,
            "user_agent": s.user_agent,
            "created_at": s.created_at,
            "last_used_at": s.last_used_at,
        }
        for s in subs
    ]


@router.post("/subscriptions")
def create_subscription(
    body: SubscriptionIn,
    user: User = Depends(require_user_api),
    session: Session = Depends(get_session),
):
    existing = session.exec(
        select(PushSubscription).where(PushSubscription.endpoint == body.endpoint)
    ).first()
    if existing:
        existing.user_id = user.id
        existing.p256dh = body.keys.get("p256dh", "")
        existing.auth = body.keys.get("auth", "")
        existing.user_agent = body.user_agent
        session.add(existing)
        session.commit()
        return {"status": "updated"}

    sub = PushSubscription(
        user_id=user.id,
        endpoint=body.endpoint,
        p256dh=body.keys.get("p256dh", ""),
        auth=body.keys.get("auth", ""),
        user_agent=body.user_agent,
    )
    session.add(sub)
    session.commit()
    return {"status": "created"}


class SubscriptionDelete(BaseModel):
    endpoint: str


@router.delete("/subscriptions")
def delete_subscription(
    body: SubscriptionDelete,
    user: User = Depends(require_user_api),
    session: Session = Depends(get_session),
):
    sub = session.exec(
        select(PushSubscription).where(
            PushSubscription.endpoint == body.endpoint, PushSubscription.user_id == user.id
        )
    ).first()
    if sub:
        session.delete(sub)
        session.commit()
    return {"status": "deleted"}


@router.post("/test-push")
def test_push(user: User = Depends(require_user_api), session: Session = Depends(get_session)):
    status = notify_user(
        session, user, title="Test notification", body="Notifaybers is working.", url="/", source="test"
    )
    return {"status": status}


# ---------- api keys ----------

@router.get("/api-keys")
def list_api_keys(user: User = Depends(require_user_api), session: Session = Depends(get_session)):
    keys = session.exec(
        select(ApiKey).where(ApiKey.user_id == user.id, ApiKey.revoked_at.is_(None))
    ).all()
    return [
        {
            "id": k.id,
            "name": k.name,
            "key_prefix": k.key_prefix,
            "created_at": k.created_at,
            "last_used_at": k.last_used_at,
        }
        for k in keys
    ]


class ApiKeyCreate(BaseModel):
    name: str


@router.post("/api-keys")
def create_api_key(
    body: ApiKeyCreate,
    user: User = Depends(require_user_api),
    session: Session = Depends(get_session),
):
    raw_key = generate_api_key()
    api_key = ApiKey(
        user_id=user.id,
        name=body.name,
        key_prefix=raw_key[:12],
        key_hash=hash_api_key(raw_key),
    )
    session.add(api_key)
    session.commit()
    session.refresh(api_key)
    return {"id": api_key.id, "name": api_key.name, "key": raw_key}


@router.delete("/api-keys/{key_id}")
def revoke_api_key(
    key_id: int,
    user: User = Depends(require_user_api),
    session: Session = Depends(get_session),
):
    key = session.get(ApiKey, key_id)
    if key is None or key.user_id != user.id:
        raise HTTPException(status_code=404, detail="Not found")
    key.revoked_at = datetime.utcnow()
    session.add(key)
    session.commit()
    return {"status": "revoked"}


# ---------- reminders ----------

class ReminderIn(BaseModel):
    title: str
    body: str | None = None
    url: str | None = None
    category: str | None = None
    schedule_type: str
    schedule_value: dict


def _reminder_out(r: Reminder) -> dict:
    return {
        "id": r.id,
        "title": r.title,
        "body": r.body,
        "url": r.url,
        "category": r.category,
        "schedule_type": r.schedule_type,
        "schedule_value": json.loads(r.schedule_value),
        "enabled": r.enabled,
        "next_run_at": r.next_run_at,
    }


@router.get("/reminders")
def list_reminders(user: User = Depends(require_user_api), session: Session = Depends(get_session)):
    reminders = session.exec(
        select(Reminder).where(Reminder.user_id == user.id).order_by(Reminder.next_run_at)
    ).all()
    return [_reminder_out(r) for r in reminders]


@router.get("/reminders/categories")
def list_reminder_categories(
    user: User = Depends(require_user_api), session: Session = Depends(get_session)
):
    values = session.exec(
        select(Reminder.category).where(Reminder.user_id == user.id, Reminder.category.is_not(None))
    ).all()
    return sorted({v for v in values if v})


@router.post("/reminders")
def create_reminder(
    body: ReminderIn,
    user: User = Depends(require_user_api),
    session: Session = Depends(get_session),
):
    try:
        validate_schedule(body.schedule_type, body.schedule_value)
        next_run = compute_next_run(body.schedule_type, body.schedule_value, user.timezone)
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    reminder = Reminder(
        user_id=user.id,
        title=body.title,
        body=body.body,
        url=body.url,
        category=body.category,
        schedule_type=body.schedule_type,
        schedule_value=json.dumps(body.schedule_value),
        next_run_at=next_run,
        enabled=next_run is not None,
    )
    session.add(reminder)
    session.commit()
    session.refresh(reminder)
    return _reminder_out(reminder)


@router.put("/reminders/{reminder_id}")
def update_reminder(
    reminder_id: int,
    body: ReminderIn,
    user: User = Depends(require_user_api),
    session: Session = Depends(get_session),
):
    reminder = session.get(Reminder, reminder_id)
    if reminder is None or reminder.user_id != user.id:
        raise HTTPException(status_code=404, detail="Not found")

    try:
        validate_schedule(body.schedule_type, body.schedule_value)
        next_run = compute_next_run(body.schedule_type, body.schedule_value, user.timezone)
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    reminder.title = body.title
    reminder.body = body.body
    reminder.url = body.url
    reminder.category = body.category
    reminder.schedule_type = body.schedule_type
    reminder.schedule_value = json.dumps(body.schedule_value)
    reminder.next_run_at = next_run
    reminder.enabled = next_run is not None
    session.add(reminder)
    session.commit()
    session.refresh(reminder)
    return _reminder_out(reminder)


@router.post("/reminders/{reminder_id}/toggle")
def toggle_reminder(
    reminder_id: int,
    user: User = Depends(require_user_api),
    session: Session = Depends(get_session),
):
    reminder = session.get(Reminder, reminder_id)
    if reminder is None or reminder.user_id != user.id:
        raise HTTPException(status_code=404, detail="Not found")

    reminder.enabled = not reminder.enabled
    if reminder.enabled:
        value = json.loads(reminder.schedule_value)
        reminder.next_run_at = compute_next_run(reminder.schedule_type, value, user.timezone)
        reminder.enabled = reminder.next_run_at is not None
    else:
        reminder.next_run_at = None
    session.add(reminder)
    session.commit()
    session.refresh(reminder)
    return _reminder_out(reminder)


class SnoozeIn(BaseModel):
    amount: int
    unit: str  # minutes | hours | days


@router.post("/reminders/{reminder_id}/snooze")
def snooze_reminder(
    reminder_id: int,
    body: SnoozeIn,
    user: User = Depends(require_user_api),
    session: Session = Depends(get_session),
):
    reminder = session.get(Reminder, reminder_id)
    if reminder is None or reminder.user_id != user.id:
        raise HTTPException(status_code=404, detail="Not found")

    try:
        _, next_run = snooze_target(body.amount, body.unit, user.timezone)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # Only the next fire is pushed back -- the underlying recurrence
    # (schedule_type/schedule_value) is untouched, so a daily/weekly/etc
    # reminder resumes its normal pattern after the snoozed fire.
    reminder.next_run_at = next_run
    reminder.enabled = True
    session.add(reminder)
    session.commit()
    session.refresh(reminder)
    return _reminder_out(reminder)


@router.delete("/reminders/{reminder_id}")
def delete_reminder(
    reminder_id: int,
    user: User = Depends(require_user_api),
    session: Session = Depends(get_session),
):
    reminder = session.get(Reminder, reminder_id)
    if reminder is None or reminder.user_id != user.id:
        raise HTTPException(status_code=404, detail="Not found")
    session.delete(reminder)
    session.commit()
    return {"status": "deleted"}


# ---------- notification history ----------

@router.get("/notifications")
def list_notifications(
    limit: int = 50,
    offset: int = 0,
    user: User = Depends(require_user_api),
    session: Session = Depends(get_session),
):
    logs = session.exec(
        select(NotificationLog)
        .where(NotificationLog.user_id == user.id)
        .order_by(NotificationLog.created_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return [
        {
            "id": n.id,
            "source": n.source,
            "title": n.title,
            "body": n.body,
            "status": n.status,
            "created_at": n.created_at,
        }
        for n in logs
    ]


@router.post("/notifications/{notification_id}/snooze")
def snooze_notification(
    notification_id: int,
    body: SnoozeIn,
    user: User = Depends(require_user_api),
    session: Session = Depends(get_session),
):
    log = session.get(NotificationLog, notification_id)
    if log is None or log.user_id != user.id:
        raise HTTPException(status_code=404, detail="Not found")

    try:
        schedule_value, next_run = snooze_target(body.amount, body.unit, user.timezone)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    reminder = Reminder(
        user_id=user.id,
        title=log.title,
        body=log.body,
        schedule_type="once",
        schedule_value=json.dumps(schedule_value),
        next_run_at=next_run,
        enabled=True,
    )
    session.add(reminder)
    session.commit()
    session.refresh(reminder)
    return _reminder_out(reminder)


# ---------- watchdogs ----------

class WatchdogIn(BaseModel):
    name: str
    ping_interval_seconds: int = 86400
    grace_period_seconds: int = 300


class WatchdogUpdate(BaseModel):
    name: str | None = None
    ping_interval_seconds: int | None = None
    grace_period_seconds: int | None = None
    enabled: bool | None = None


def _watchdog_out(wd: Watchdog, request: Request | None = None) -> dict:
    domain = public_base_url(request) if request else ""
    return {
        "id": wd.id,
        "name": wd.name,
        "token": wd.token,
        "ping_url": f"{domain}/api/ping/{wd.token}" if domain else f"/api/ping/{wd.token}",
        "ping_interval_seconds": wd.ping_interval_seconds,
        "grace_period_seconds": wd.grace_period_seconds,
        "last_ping_at": wd.last_ping_at,
        "status": wd.status,
        "alert_sent": wd.alert_sent,
        "enabled": wd.enabled,
        "created_at": wd.created_at,
    }


@router.get("/watchdogs")
def list_watchdogs(
    request: Request,
    user: User = Depends(require_user_api),
    session: Session = Depends(get_session),
):
    wds = session.exec(
        select(Watchdog).where(Watchdog.user_id == user.id).order_by(Watchdog.created_at.desc())
    ).all()
    return [_watchdog_out(w, request) for w in wds]


@router.post("/watchdogs")
def create_watchdog(
    body: WatchdogIn,
    request: Request,
    user: User = Depends(require_user_api),
    session: Session = Depends(get_session),
):
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name cannot be empty")

    min_allowed = settings.watchdog_min_ping_seconds
    if body.ping_interval_seconds < min_allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Ping interval must be at least {min_allowed} seconds",
        )

    wd = Watchdog(
        user_id=user.id,
        name=name,
        token=secrets.token_urlsafe(16),
        ping_interval_seconds=body.ping_interval_seconds,
        grace_period_seconds=max(0, body.grace_period_seconds),
        status="pending",
        enabled=True,
    )
    session.add(wd)
    session.commit()
    session.refresh(wd)
    return _watchdog_out(wd, request)


@router.put("/watchdogs/{watchdog_id}")
def update_watchdog(
    watchdog_id: int,
    body: WatchdogUpdate,
    request: Request,
    user: User = Depends(require_user_api),
    session: Session = Depends(get_session),
):
    wd = session.get(Watchdog, watchdog_id)
    if not wd or wd.user_id != user.id:
        raise HTTPException(status_code=404, detail="Watchdog not found")

    if body.name is not None:
        wd.name = body.name.strip()
    if body.ping_interval_seconds is not None:
        min_allowed = settings.watchdog_min_ping_seconds
        if body.ping_interval_seconds < min_allowed:
            raise HTTPException(
                status_code=400,
                detail=f"Ping interval must be at least {min_allowed} seconds",
            )
        wd.ping_interval_seconds = body.ping_interval_seconds
    if body.grace_period_seconds is not None:
        wd.grace_period_seconds = max(0, body.grace_period_seconds)
    if body.enabled is not None:
        wd.enabled = body.enabled
        if not wd.enabled:
            wd.status = "paused"
        elif wd.status == "paused":
            wd.status = "healthy" if wd.last_ping_at else "pending"

    session.add(wd)
    session.commit()
    session.refresh(wd)
    return _watchdog_out(wd, request)


@router.delete("/watchdogs/{watchdog_id}")
def delete_watchdog(
    watchdog_id: int,
    user: User = Depends(require_user_api),
    session: Session = Depends(get_session),
):
    wd = session.get(Watchdog, watchdog_id)
    if not wd or wd.user_id != user.id:
        raise HTTPException(status_code=404, detail="Watchdog not found")
    session.delete(wd)
    session.commit()
    return {"status": "deleted", "id": watchdog_id}


@router.post("/watchdogs/{watchdog_id}/toggle")
def toggle_watchdog(
    watchdog_id: int,
    request: Request,
    user: User = Depends(require_user_api),
    session: Session = Depends(get_session),
):
    wd = session.get(Watchdog, watchdog_id)
    if not wd or wd.user_id != user.id:
        raise HTTPException(status_code=404, detail="Watchdog not found")
    wd.enabled = not wd.enabled
    if not wd.enabled:
        wd.status = "paused"
    else:
        wd.status = "healthy" if wd.last_ping_at else "pending"
        wd.alert_sent = False
    session.add(wd)
    session.commit()
    session.refresh(wd)
    return _watchdog_out(wd, request)


# ---------- Public Ping Endpoint (No session/login needed) ----------

@router.api_route("/ping/{token}", methods=["GET", "POST", "HEAD"])
def ping_watchdog(
    token: str,
    session: Session = Depends(get_session),
):
    wd = session.exec(select(Watchdog).where(Watchdog.token == token)).first()
    if not wd:
        raise HTTPException(status_code=404, detail="Watchdog not found")

    now = datetime.utcnow()
    was_down = (wd.status == "down")
    wd.last_ping_at = now
    wd.status = "healthy"
    wd.alert_sent = False
    session.add(wd)
    session.commit()

    if was_down and wd.enabled:
        user = session.get(User, wd.user_id)
        if user:
            try:
                notify_user(
                    session,
                    user,
                    title=f"✅ Watchdog Recovered: {wd.name}",
                    body=f"Ping received at {now.strftime('%H:%M:%S UTC')}. Service is healthy again.",
                    url="/watchdogs",
                    source="watchdog",
                )
            except Exception:
                pass

    return {
        "status": "ok",
        "name": wd.name,
        "last_ping_at": wd.last_ping_at.isoformat(),
        "next_expected_before": (
            now.timestamp() + wd.ping_interval_seconds + wd.grace_period_seconds
        ),
    }


# ---------- AI Assistant & MCP ----------

class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]


@router.post("/ai/chat")
def ai_chat(
    body: ChatRequest,
    request: Request,
    user: User = Depends(require_user_api),
    session: Session = Depends(get_session),
):
    domain = public_base_url(request)
    try:
        messages = [{"role": m.role, "content": m.content} for m in body.messages]
        result = chat_with_llm(user, session, messages, domain=domain)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"AI chat error: {exc}")


@router.get("/mcp/tools")
def mcp_tools():
    """Returns the Model Context Protocol tools manifest."""
    return get_mcp_manifest()


class McpCallRequest(BaseModel):
    name: str
    arguments: dict = {}


@router.post("/mcp/call")
def mcp_call(
    body: McpCallRequest,
    request: Request,
    user: User = Depends(require_user_api),
    session: Session = Depends(get_session),
):
    domain = public_base_url(request)
    try:
        result = execute_tool(body.name, body.arguments, user, session, domain=domain)
    except Exception as exc:
        logging.getLogger("notifaybers.mcp").exception("tool call failed: %s", body.name)
        result = {"error": str(exc)}
    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}
