"""Authentication routes for registration, login, and logout."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.exc import SQLAlchemyError

from backend.auth import ACCESS_TOKEN_COOKIE, create_access_token, get_current_user_optional, hash_password, token_hash, verify_password
from backend.database import create_user, create_user_session, get_user_by_email, get_user_by_username, init_db, revoke_user_session

logger = logging.getLogger(__name__)

router = APIRouter(tags=["auth"])
BASE_DIR = Path(__file__).resolve().parents[2]
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def _auth_redirect(path: str) -> RedirectResponse:
    return RedirectResponse(url=path, status_code=status.HTTP_303_SEE_OTHER)


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    user = get_current_user_optional(request)
    if user:
        return _auth_redirect("/dashboard")
    return templates.TemplateResponse(
        request,
        "auth.html",
        {
            "page_title": "Login",
            "auth_mode": "login",
            "auth_action": "/auth/login",
            "auth_heading": "Welcome back",
            "auth_copy": "Sign in to reach the TrendHunter AI dashboard, analysis tools, and exports.",
            "auth_cta": "Login",
        },
    )


@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    current_user = get_current_user_optional(request)
    if current_user:
        return _auth_redirect("/dashboard")
    return templates.TemplateResponse(
        request,
        "auth.html",
        {
            "page_title": "Register",
            "auth_mode": "register",
            "auth_action": "/auth/register",
            "auth_heading": "Create your account",
            "auth_copy": "Get secure access to the dashboard, creator intelligence, PDF exports, and trend tools.",
            "auth_cta": "Create account",
        },
    )


@router.post("/auth/register")
def register_user(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
):
    init_db()
    username = username.strip()
    email = email.strip().lower()
    password = password.strip()

    if len(username) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters.")
    if "@" not in email:
        raise HTTPException(status_code=400, detail="Enter a valid email address.")
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters.")

    if get_user_by_username(username):
        raise HTTPException(status_code=400, detail="Username is already taken.")
    if get_user_by_email(email):
        raise HTTPException(status_code=400, detail="Email is already registered.")

    try:
        user = create_user(username=username, email=email, password_hash=hash_password(password))
        token, expires_at, jti = create_access_token(user["id"], user["username"], user["email"])
        create_user_session(user_id=user["id"], jti=jti, token_hash=token_hash(token), expires_at=expires_at)
        response = _auth_redirect("/dashboard")
        response.set_cookie(
            key=ACCESS_TOKEN_COOKIE,
            value=token,
            httponly=True,
            secure=request.url.scheme == "https",
            samesite="lax",
            max_age=60 * 60 * 12,
            path="/",
        )
        return response
    except SQLAlchemyError as exc:
        logger.exception("Registration failed")
        raise HTTPException(status_code=500, detail=f"Database error: {exc}") from exc


@router.post("/auth/login")
def login_user(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    init_db()
    username = username.strip()
    password = password.strip()
    user = get_user_by_username(username) or get_user_by_email(username)
    if not user or not verify_password(password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid username/email or password.")

    token, expires_at, jti = create_access_token(user["id"], user["username"], user["email"])
    create_user_session(user_id=user["id"], jti=jti, token_hash=token_hash(token), expires_at=expires_at)
    response = _auth_redirect("/dashboard")
    response.set_cookie(
        key=ACCESS_TOKEN_COOKIE,
        value=token,
        httponly=True,
        secure=request.url.scheme == "https",
        samesite="lax",
        max_age=60 * 60 * 12,
        path="/",
    )
    return response


@router.get("/logout")
def logout_user(request: Request):
    token = request.cookies.get(ACCESS_TOKEN_COOKIE)
    if token:
        from backend.auth import decode_access_token

        try:
            payload = decode_access_token(token)
            jti = str(payload.get("jti") or "")
            if jti:
                revoke_user_session(jti)
        except Exception:
            logger.debug("Skipping logout revocation because the token could not be decoded.")

    response = _auth_redirect("/login")
    response.delete_cookie(key=ACCESS_TOKEN_COOKIE, path="/")
    return response
