from fastapi import Depends, HTTPException, Request
from sqlmodel import Session, select

from app.config import settings
from app.db import get_session
from app.models import ApiKey, User
from app.security import hash_api_key


def public_base_url(request: Request) -> str:
    """Configured PUBLIC_BASE_URL, else the origin this request came in on."""
    return (settings.public_base_url.strip() or str(request.base_url)).rstrip("/")


def get_current_user(request: Request, session: Session = Depends(get_session)) -> User | None:
    user_id = request.session.get("user_id")
    if user_id is None:
        return None
    return session.get(User, user_id)


def require_user_api(user: User | None = Depends(get_current_user)) -> User:
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def get_api_key_user(
    request: Request, session: Session = Depends(get_session)
) -> tuple[User, ApiKey]:
    key = request.headers.get("X-API-Key")
    if not key:
        raise HTTPException(status_code=401, detail="Missing X-API-Key header")
    key_hash = hash_api_key(key)
    api_key = session.exec(
        select(ApiKey).where(ApiKey.key_hash == key_hash, ApiKey.revoked_at.is_(None))
    ).first()
    if api_key is None:
        raise HTTPException(status_code=401, detail="Invalid API key")
    user = session.get(User, api_key.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return user, api_key
