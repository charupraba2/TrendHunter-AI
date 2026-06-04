"""Web page routes."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from backend.database import get_trend_by_id

router = APIRouter()
BASE_DIR = Path(__file__).resolve().parents[2]
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@router.get("/", response_class=HTMLResponse)
def landing_page(request: Request):
    return templates.TemplateResponse(
        request,
        "landing.html",
        {"page_title": "TrendHunter AI"},
    )


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(request: Request):
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "page_title": "Dashboard",
        },
    )


@router.get("/trends/{trend_id}", response_class=HTMLResponse)
def trend_detail_page(request: Request, trend_id: int):
    trend = get_trend_by_id(trend_id)
    return templates.TemplateResponse(
        request,
        "trend_detail.html",
        {
            "page_title": "Trend Details",
            "trend": trend,
        },
    )
