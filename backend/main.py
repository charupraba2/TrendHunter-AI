"""FastAPI application entrypoint for TrendHunter AI."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles

from backend.config import settings
from backend.database import init_db
from backend.routers.api import router as api_router
from backend.routers.web import router as web_router
from backend.routers.ws import router as ws_router
from backend.websocket_manager import websocket_manager

BASE_DIR = Path(__file__).resolve().parent.parent

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.app_name, version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.trusted_hosts,
)

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

app.include_router(web_router)
app.include_router(api_router)
app.include_router(ws_router)


def _validate_environment() -> None:
    missing_keys = []
    if not settings.news_api_key:
        missing_keys.append("NEWS_API_KEY")
    if not settings.youtube_api_key:
        missing_keys.append("YOUTUBE_API_KEY")
    if not settings.gemini_api_key:
        missing_keys.append("GEMINI_API_KEY")

    if missing_keys:
        logger.warning("Optional API keys are missing: %s", ", ".join(missing_keys))
    else:
        logger.info("All optional API keys are configured.")


@app.on_event("startup")
async def on_startup() -> None:
    _validate_environment()
    websocket_manager.set_event_loop(asyncio.get_running_loop())
    init_db()
    logger.info("TrendHunter AI started in %s mode.", settings.app_env)


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "app": settings.app_name,
        "environment": "production-ready",
        "websocket": "enabled",
        "apis": {
            "newsapi": bool(settings.news_api_key),
            "youtube": bool(settings.youtube_api_key),
            "gemini": bool(settings.gemini_api_key),
        },
    }
