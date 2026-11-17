"""Google sign-in: OAuth client setup and mapping a Google identity to a local user."""

import secrets

from authlib.integrations.starlette_client import OAuth
from sqlmodel import Session, select

from app.config import settings
from app.models import User
from app.security import hash_password

oauth = OAuth()

if settings.google_enabled:
    oauth.register(
        name="google",
        client_id=settings.google_client_id.strip(),
        client_secret=settings.google_client_secret.strip(),
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )


class SignInDenied(Exception):
    """The Google account is valid but not allowed into this deployment."""


def resolve_google_user(session: Session, claims: dict) -> User:
    """Return the local user for verified Google claims, linking or creating as policy allows.

    Order: known Google account id -> existing user with the same email (e.g. the
    seeded admin, via ADMIN_EMAIL) -> new account if the email is allowed.
    """
    sub = claims.get("sub")
    email = (claims.get("email") or "").strip().lower()
    if not sub or not email:
        raise SignInDenied("Google did not return an email address.")
    if not claims.get("email_verified"):
        raise SignInDenied("Your Google email address is not verified.")

    # The allowlist is authoritative on every sign-in, so removing an email from
    # ALLOWED_EMAILS locks that account out again.
    if not (settings.open_signup or email in settings.allowed_email_set):
        raise SignInDenied("This Google account is not allowed to sign in.")

    user = session.exec(select(User).where(User.google_sub == sub)).first()
    if user is None:
        user = session.exec(select(User).where(User.email == email)).first()
        if user is None and email == settings.admin_email.strip().lower():
            # Link the seeded admin account so its data carries over.
            user = session.exec(select(User).where(User.username == settings.admin_username)).first()
            if user is not None and user.google_sub:
                user = None  # already linked to a different Google account

    if user is not None:
        if not user.is_active:
            raise SignInDenied("This account is disabled.")
        if user.google_sub and user.google_sub != sub:
            raise SignInDenied("This email is already linked to a different Google account.")
        user.google_sub = sub
        user.email = email
        user.name = claims.get("name") or user.name
        session.add(user)
        session.commit()
        return user

    # Username must be unique and non-null; the email is a natural choice. The
    # password is random and never shown: these accounts sign in with Google only.
    user = User(
        username=email,
        email=email,
        google_sub=sub,
        name=claims.get("name"),
        password_hash=hash_password(secrets.token_urlsafe(32)),
        timezone=settings.default_timezone,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user
