"""WebSocket connection manager for TrendHunter AI dashboard updates."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect

logger = logging.getLogger(__name__)


class WebSocketManager:
    def __init__(self) -> None:
        self.active_connections: set[WebSocket] = set()
        self._lock = asyncio.Lock()
        self._loop: asyncio.AbstractEventLoop | None = None

    def set_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop
        logger.info("WebSocket event loop registered.")

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self.active_connections.add(websocket)
            active_count = len(self.active_connections)
        logger.info("Dashboard websocket connected. active_connections=%s", active_count)
        await websocket.send_json(
            self._build_event(
                "connection_status",
                {
                    "connected": True,
                    "active_connections": active_count,
                    "message": "Connected to TrendHunter AI live dashboard.",
                },
            )
        )
        await self.broadcast_event(
            "activity",
            {
                "message": "A dashboard client connected.",
                "level": "info",
            },
            exclude=websocket,
        )

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
            active_count = len(self.active_connections)
        logger.info("Dashboard websocket disconnected. active_connections=%s", active_count)
        await self.broadcast_event(
            "connection_status",
            {
                "connected": active_count > 0,
                "active_connections": active_count,
                "message": "Dashboard connection updated.",
            },
        )

    async def handle_client_messages(self, websocket: WebSocket) -> None:
        while True:
            try:
                payload = await websocket.receive_text()
            except WebSocketDisconnect:
                raise
            except Exception as exc:
                logger.warning("Websocket receive failed: %s", exc)
                continue

            if not payload:
                logger.warning("Ignored empty websocket payload.")
                continue

            if payload.lower() == "ping":
                await websocket.send_json(self._build_event("pong", {"message": "pong"}))
                continue

            try:
                data = json.loads(payload)
            except Exception:
                logger.warning("Invalid websocket payload received.")
                continue

            if not isinstance(data, dict):
                logger.warning("Ignored non-dict websocket payload.")
                continue

            if data.get("type") == "ping":
                await websocket.send_json(self._build_event("pong", {"message": "pong"}))
            elif data.get("type") == "subscribe":
                await websocket.send_json(
                    self._build_event(
                        "connection_status",
                        {
                            "connected": True,
                            "active_connections": len(self.active_connections),
                            "message": "Subscription confirmed.",
                        },
                    )
                )

    async def broadcast_event(
        self,
        event_type: str,
        payload: dict[str, Any],
        exclude: WebSocket | None = None,
    ) -> None:
        message = self._build_event(event_type, payload)
        await self.broadcast(message, exclude=exclude)

    async def broadcast(self, message: dict[str, Any], exclude: WebSocket | None = None) -> None:
        async with self._lock:
            connections = [ws for ws in self.active_connections if ws is not exclude]

        if not connections:
            return

        stale_connections: list[WebSocket] = []
        await asyncio.gather(
            *[self._safe_send(connection, message, stale_connections) for connection in connections],
            return_exceptions=True,
        )

        if stale_connections:
            async with self._lock:
                for websocket in stale_connections:
                    self.active_connections.discard(websocket)
            logger.info("Cleaned up %s stale websocket connections.", len(stale_connections))

    def broadcast_sync(self, message: dict[str, Any]) -> None:
        try:
            if self._loop and self._loop.is_running():
                asyncio.run_coroutine_threadsafe(self.broadcast(message), self._loop)
                return

            loop = asyncio.get_running_loop()
            loop.create_task(self.broadcast(message))
            return
        except RuntimeError:
            try:
                asyncio.run(self.broadcast(message))
            except RuntimeError:
                logger.warning("Unable to broadcast websocket message because no event loop is available.")

    async def _safe_send(
        self,
        websocket: WebSocket,
        message: dict[str, Any],
        stale_connections: list[WebSocket],
    ) -> None:
        try:
            await websocket.send_json(message)
        except Exception as exc:
            logger.warning("Websocket broadcast failed: %s", exc)
            stale_connections.append(websocket)

    def broadcast_trend_update(self, trend: dict[str, Any], action: str = "updated") -> None:
        trend_snapshot = self._trend_snapshot(trend)
        logger.info(
            "Broadcasting trend update: action=%s platform=%s title=%s",
            action,
            trend_snapshot.get("platform"),
            trend_snapshot.get("title"),
        )
        self.broadcast_sync(
            self._build_event(
                "trend_update",
                {
                    "action": action,
                    "trend": trend_snapshot,
                },
            )
        )

    def broadcast_alert_update(self, alert: dict[str, Any], action: str = "created") -> None:
        logger.info("Broadcasting alert update: action=%s title=%s", action, alert.get("title"))
        self.broadcast_sync(
            self._build_event(
                "alert_update",
                {
                    "action": action,
                    "alert": alert,
                },
            )
        )

    def broadcast_virality_update(self, trend: dict[str, Any], action: str = "analyzed") -> None:
        logger.info("Broadcasting virality update for trend_id=%s", trend.get("id"))
        self.broadcast_sync(
            self._build_event(
                "virality_update",
                {
                    "action": action,
                    "trend": trend,
                },
            )
        )

    def broadcast_rag_update(self, payload: dict[str, Any]) -> None:
        logger.info("Broadcasting RAG update for title=%s", payload.get("current_trend"))
        self.broadcast_sync(
            self._build_event(
                "rag_update",
                payload,
            )
        )

    def broadcast_forecast_update(self, payload: dict[str, Any]) -> None:
        logger.info("Broadcasting forecast update for title=%s", payload.get("trend", {}).get("title"))
        self.broadcast_sync(
            self._build_event(
                "forecast_update",
                payload,
            )
        )

    def broadcast_activity(self, message: str, level: str = "info") -> None:
        self.broadcast_sync(self._build_event("activity", {"message": message, "level": level}))

    def _build_event(self, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "active_connections": len(self.active_connections),
            "payload": payload,
        }

    def _trend_snapshot(self, trend: dict[str, Any]) -> dict[str, Any]:
        """Create a compact JSON-safe trend payload for websocket broadcasts."""

        return {
            "id": self._json_safe(trend.get("id")),
            "title": self._json_safe(trend.get("title") or trend.get("name") or "Untitled trend"),
            "platform": self._json_safe(trend.get("platform") or trend.get("source_type") or "unknown"),
            "source_type": self._json_safe(trend.get("source_type")),
            "source_label": self._json_safe(trend.get("source_label")),
            "subreddit": self._json_safe(trend.get("subreddit")),
            "url": self._json_safe(trend.get("url")),
            "upvotes": self._json_safe(trend.get("upvotes", 0)),
            "comments": self._json_safe(trend.get("comments", 0)),
            "trend_score": self._json_safe(trend.get("trend_score", trend.get("search_interest", 0))),
            "sentiment_label": self._json_safe(trend.get("sentiment_label")),
            "virality_score": self._json_safe(trend.get("virality_score")),
            "virality_probability": self._json_safe(trend.get("virality_probability")),
            "forecast_confidence": self._json_safe(trend.get("forecast_confidence")),
            "prediction_label": self._json_safe(trend.get("prediction_label")),
            "growth_stage": self._json_safe(trend.get("growth_stage")),
            "expected_engagement": self._json_safe(trend.get("expected_engagement")),
            "opportunity_score": self._json_safe(trend.get("opportunity_score")),
            "risk_score": self._json_safe(trend.get("risk_score")),
            "forecast_updated_at": self._json_safe(trend.get("forecast_updated_at")),
            "virality_label": self._json_safe(trend.get("virality_label")),
            "fetched_at": self._json_safe(trend.get("fetched_at")),
            "analyzed_at": self._json_safe(trend.get("analyzed_at")),
            "source_uid": self._json_safe(trend.get("source_uid")),
        }

    def _json_safe(self, value: Any) -> Any:
        if value is None:
            return None
        if hasattr(value, "item"):
            try:
                value = value.item()
            except Exception:
                pass
        if isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, datetime):
            return value.isoformat()
        return str(value)


websocket_manager = WebSocketManager()
