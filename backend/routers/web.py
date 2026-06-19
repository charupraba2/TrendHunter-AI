"""Web page routes."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from backend.auth import ACCESS_TOKEN_COOKIE
from backend.database import get_trend_by_id

router = APIRouter()
BASE_DIR = Path(__file__).resolve().parents[2]
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def _require_login(request: Request):
    if getattr(request.state, "current_user", None):
        return None
    if request.cookies.get(ACCESS_TOKEN_COOKIE):
        return RedirectResponse(url="/login", status_code=303)
    return RedirectResponse(url="/login", status_code=303)


@router.get("/", response_class=HTMLResponse)
def landing_page(request: Request):
    return templates.TemplateResponse(
        request,
        "home.html",
        {
            "page_title": "TrendHunter AI",
            "current_user": getattr(request.state, "current_user", None),
        },
    )


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(request: Request):
    redirect = _require_login(request)
    if redirect is not None:
        return redirect
    return templates.TemplateResponse(
        request,
        "trend_workspace.html",
        {
            "page_title": "Trend Intelligence Workspace",
            "workspace": "trend",
            "default_dashboard_tab": "dashboard",
            "current_user": getattr(request.state, "current_user", None),
        },
    )


@router.get("/trend-intelligence", response_class=HTMLResponse)
def trend_intelligence_page(request: Request):
    redirect = _require_login(request)
    if redirect is not None:
        return redirect
    return templates.TemplateResponse(
        request,
        "trend_workspace.html",
        {
            "page_title": "Trend Intelligence Workspace",
            "workspace": "trend",
            "default_dashboard_tab": "dashboard",
            "current_user": getattr(request.state, "current_user", None),
        },
    )


@router.get("/industry-intelligence", response_class=HTMLResponse)
def industry_intelligence_page(request: Request):
    redirect = _require_login(request)
    if redirect is not None:
        return redirect
    return templates.TemplateResponse(
        request,
        "industry_workspace.html",
        {
            "page_title": "Industry Intelligence Workspace",
            "workspace": "industry",
            "default_dashboard_tab": "industry-intelligence",
            "current_user": getattr(request.state, "current_user", None),
        },
    )


@router.get("/trends/{trend_id}", response_class=HTMLResponse)
def trend_detail_page(request: Request, trend_id: int):
    redirect = _require_login(request)
    if redirect is not None:
        return redirect
    trend = get_trend_by_id(trend_id)
    return templates.TemplateResponse(
        request,
        "trend_detail.html",
        {
            "page_title": "Trend Details",
            "trend": trend,
            "current_user": getattr(request.state, "current_user", None),
        },
    )
