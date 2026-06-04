"""WebSocket routes for TrendHunter AI dashboard updates."""

from __future__ import annotations

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.websocket_manager import websocket_manager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/dashboard")
async def dashboard_websocket(websocket: WebSocket):
    try:
        await websocket_manager.connect(websocket)
        await websocket_manager.handle_client_messages(websocket)
    except WebSocketDisconnect:
        logger.info("Dashboard websocket disconnected by client.")
    except Exception as exc:
        logger.exception("Dashboard websocket failed: %s", exc)
    finally:
        await websocket_manager.disconnect(websocket)
