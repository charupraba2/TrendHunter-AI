"""High viral trend alert generation."""

from __future__ import annotations

from typing import Any


class AlertAgent:
    def should_alert(self, trend: dict[str, Any]) -> bool:
        return (
            float(trend.get("virality_score", 0) or 0) >= 75
            and str(trend.get("virality_label", "")).strip() == "High Viral"
        )

    def build_alert_message(self, trend: dict[str, Any]) -> str:
        title = trend.get("title") or trend.get("name") or "Untitled trend"
        score = int(float(trend.get("virality_score", 0) or 0))
        return (
            f"🔥 High viral trend detected: {title} scored {score}/100. "
            "Create content now before the trend peaks."
        )

    def prepare_alert(self, trend: dict[str, Any]) -> dict[str, Any] | None:
        if not self.should_alert(trend):
            return None

        return {
            "trend_id": trend.get("id"),
            "title": trend.get("title") or trend.get("name") or "Untitled trend",
            "platform": trend.get("platform", "reddit"),
            "virality_score": float(trend.get("virality_score", 0) or 0),
            "virality_label": trend.get("virality_label", "High Viral"),
            "message": self.build_alert_message(trend),
        }
