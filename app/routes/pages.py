from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import case, func
from sqlmodel import Session, select

from app.db import get_session
from app.deps import public_base_url, touch_last_active
from app.models import User
from app.templating import templates
from app.version import app_version

router = APIRouter()


def _render(request: Request, template: str, session: Session):
    user_id = request.session.get("user_id")
    user = session.get(User, user_id) if user_id else None
    if user is None or not user.is_active:
        request.session.clear()
        return RedirectResponse("/login", status_code=303)
    touch_last_active(session, user)
    return templates.TemplateResponse(
        request,
        template,
        {
            "watchdogs_enabled": user.watchdogs_enabled,
            "reminders_enabled": user.reminders_enabled,
            "bills_enabled": user.bills_enabled,
            "bills_language": user.bills_language,
            "is_admin": user.is_admin,
            "base_url": public_base_url(request),
            "version": app_version(),
        },
    )


@router.get("/")
def dashboard(request: Request, session: Session = Depends(get_session)):
    return _render(request, "dashboard.html", session)


@router.get("/reminders")
def reminders_page(request: Request, session: Session = Depends(get_session)):
    user_id = request.session.get("user_id")
    user = session.get(User, user_id) if user_id else None
    if user is not None and user.is_active and not user.reminders_enabled:
        return RedirectResponse("/settings", status_code=303)
    return _render(request, "reminders.html", session)


@router.get("/settings")
def settings_page(request: Request, session: Session = Depends(get_session)):
    return _render(request, "settings.html", session)


@router.get("/watchdogs")
def watchdogs_page(request: Request, session: Session = Depends(get_session)):
    user_id = request.session.get("user_id")
    user = session.get(User, user_id) if user_id else None
    if user is not None and user.is_active and not user.watchdogs_enabled:
        return RedirectResponse("/settings", status_code=303)
    return _render(request, "watchdogs.html", session)


@router.get("/bills")
def bills_page(request: Request, session: Session = Depends(get_session)):
    user_id = request.session.get("user_id")
    user = session.get(User, user_id) if user_id else None
    if user is not None and user.is_active and not user.bills_enabled:
        return RedirectResponse("/settings", status_code=303)
    return _render(request, "bills.html", session)


USERS_PER_PAGE = 20


def _local(dt: datetime | None, tz: ZoneInfo) -> str:
    if dt is None:
        return ""
    return dt.replace(tzinfo=timezone.utc).astimezone(tz).strftime("%d %b %Y, %H:%M")


@router.get("/admin/users")
def admin_users_page(
    request: Request,
    page: int = Query(1, ge=1),
    session: Session = Depends(get_session),
):
    user_id = request.session.get("user_id")
    admin = session.get(User, user_id) if user_id else None
    if admin is None or not admin.is_active:
        request.session.clear()
        return RedirectResponse("/login", status_code=303)
    if not admin.is_admin:
        return RedirectResponse("/settings", status_code=303)
    touch_last_active(session, admin)

    total = session.exec(select(func.count()).select_from(User)).one()
    pages = max(1, -(-total // USERS_PER_PAGE))
    page = min(page, pages)
    # Most recently active first; people who never came back after signing up go last.
    rows = session.exec(
        select(User)
        .order_by(
            case((User.last_active_at.is_(None), 1), else_=0),
            User.last_active_at.desc(),
            User.created_at.desc(),
        )
        .offset((page - 1) * USERS_PER_PAGE)
        .limit(USERS_PER_PAGE)
    ).all()
    try:
        tz = ZoneInfo(admin.timezone)
    except Exception:
        tz = ZoneInfo("UTC")
    users = [
        {
            "email": u.email or u.username,
            "name": u.name or "",
            "is_admin": u.is_admin,
            "is_active": u.is_active,
            "signed_up": _local(u.created_at, tz),
            "last_active": _local(u.last_active_at, tz),
        }
        for u in rows
    ]
    return templates.TemplateResponse(
        request,
        "admin_users.html",
        {"users": users, "page": page, "pages": pages, "total": total, "timezone": admin.timezone},
    )
