"""WebSocket routes for TrendHunter AI dashboard updates."""

from __future__ import annotations

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.auth import ACCESS_TOKEN_COOKIE, get_current_user_from_token
from backend.websocket_manager import websocket_manager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/dashboard")
async def dashboard_websocket(websocket: WebSocket):
    try:
        token = websocket.cookies.get(ACCESS_TOKEN_COOKIE)
        if not token or get_current_user_from_token(token) is None:
            await websocket.close(code=1008)
            return
        await websocket_manager.connect(websocket)
        await websocket_manager.handle_client_messages(websocket)
    except WebSocketDisconnect:
        logger.info("Dashboard websocket disconnected by client.")
    except Exception as exc:
        logger.exception("Dashboard websocket failed: %s", exc)
    finally:
        await websocket_manager.disconnect(websocket)
