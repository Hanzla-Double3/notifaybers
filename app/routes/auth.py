import logging

from authlib.integrations.base_client.errors import OAuthError
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlmodel import Session, select

from app.config import settings
from app.db import get_session
from app.deps import public_base_url
from app.google_auth import SignInDenied, oauth, resolve_google_user
from app.models import User
from app.templating import templates

router = APIRouter()
log = logging.getLogger("notifaybers.auth")

_LOOPBACK = {"127.0.0.1", "::1", "localhost"}


def _dev_login_allowed(request: Request) -> bool:
    """DEV_AUTO_LOGIN only ever applies to a direct loopback connection, so even if it
    were switched on in production the request arrives via the proxy and is ignored."""
    return settings.dev_auto_login and request.client is not None and request.client.host in _LOOPBACK


def _login_page(request: Request, error: str | None = None, status_code: int = 200):
    return templates.TemplateResponse(
        request,
        "login.html",
        {"error": error, "google_enabled": settings.google_enabled},
        status_code=status_code,
    )


@router.get("/login")
def login_page(request: Request, session: Session = Depends(get_session)):
    if request.session.get("user_id"):
        return RedirectResponse("/", status_code=303)
    if _dev_login_allowed(request):
        user = session.exec(select(User).where(User.username == settings.admin_username)).first()
        if user is not None and user.is_active:
            request.session["user_id"] = user.id
            return RedirectResponse("/", status_code=303)
    return _login_page(request)


@router.get("/auth/google")
async def google_login(request: Request):
    if not settings.google_enabled:
        raise HTTPException(status_code=404)
    redirect_uri = public_base_url(request) + "/auth/google/callback"
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/auth/google/callback", name="google_callback")
async def google_callback(request: Request, session: Session = Depends(get_session)):
    if not settings.google_enabled:
        raise HTTPException(status_code=404)
    try:
        token = await oauth.google.authorize_access_token(request)
    except OAuthError as exc:
        log.warning("Google sign-in failed: %s", exc)
        return _login_page(request, "Google sign-in was cancelled or failed. Please try again.", 400)
    claims = token.get("userinfo") or {}
    try:
        user = resolve_google_user(session, dict(claims))
    except SignInDenied as exc:
        log.info("Google sign-in denied for %s: %s", claims.get("email"), exc)
        return _login_page(request, str(exc), 403)
    request.session.clear()  # drop the OAuth state; start a fresh session
    request.session["user_id"] = user.id
    return RedirectResponse("/", status_code=303)


@router.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)
