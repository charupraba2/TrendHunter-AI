"""Authentication helpers for JWT cookie sessions."""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException, Request, status
from jose import JWTError, jwt
from passlib.context import CryptContext

from backend.config import settings
from backend.database import get_user_by_id, get_user_session_by_jti

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

ALGORITHM = "HS256"
ACCESS_TOKEN_COOKIE = "trendhunter_access_token"
ACCESS_TOKEN_TTL_HOURS = 12


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_access_token(user_id: int, username: str, email: str, expires_hours: int = ACCESS_TOKEN_TTL_HOURS) -> tuple[str, datetime, str]:
    expires_at = datetime.now(timezone.utc) + timedelta(hours=expires_hours)
    jti = secrets.token_urlsafe(16)
    payload = {
        "sub": str(user_id),
        "username": username,
        "email": email,
        "jti": jti,
        "iat": int(datetime.now(timezone.utc).timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    token = jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)
    return token, expires_at, jti


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        return payload
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session.") from exc


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def get_token_from_request(request: Request) -> str | None:
    authorization = request.headers.get("authorization", "")
    if authorization.lower().startswith("bearer "):
        return authorization.split(" ", 1)[1].strip() or None
    return request.cookies.get(ACCESS_TOKEN_COOKIE)


def get_current_user_optional(request: Request) -> dict | None:
    token = get_token_from_request(request)
    if not token:
        return None
    return get_current_user_from_token(token)


def get_current_user_from_token(token: str) -> dict | None:
    try:
        payload = decode_access_token(token)
        user_id = int(payload.get("sub") or 0)
        jti = str(payload.get("jti") or "").strip()
        if not user_id or not jti:
            return None

        session = get_user_session_by_jti(jti)
        if not session or session.get("revoked_at") is not None:
            return None
        if session.get("token_hash") != token_hash(token):
            return None

        expires_at = session.get("expires_at")
        if expires_at:
            try:
                expires_dt = datetime.fromisoformat(expires_at)
                if expires_dt.tzinfo is None:
                    expires_dt = expires_dt.replace(tzinfo=timezone.utc)
                else:
                    expires_dt = expires_dt.astimezone(timezone.utc)
                if expires_dt < datetime.now(timezone.utc):
                    return None
            except ValueError:
                return None

        user = get_user_by_id(user_id)
        if not user or not user.get("is_active", True):
            return None
        return user
    except Exception:
        return None


def require_current_user(request: Request) -> dict:
    user = get_current_user_optional(request)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")
    return user
