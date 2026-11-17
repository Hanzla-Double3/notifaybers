from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlmodel import Session

from app.db import get_session
from app.deps import public_base_url
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
    return templates.TemplateResponse(
        request,
        template,
        {
            "watchdogs_enabled": user.watchdogs_enabled,
            "reminders_enabled": user.reminders_enabled,
            "bills_enabled": user.bills_enabled,
            "bills_language": user.bills_language,
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
