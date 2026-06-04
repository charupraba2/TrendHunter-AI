"""Rule-based virality scoring helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ViralityResult:
    virality_score: float
    virality_label: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "virality_score": self.virality_score,
            "virality_label": self.virality_label,
        }


class ViralityAgent:
    def analyze_trend(self, trend_payload: dict[str, Any]) -> dict[str, Any]:
        upvotes = self._safe_float(trend_payload.get("upvotes", 0))
        comments = self._safe_float(trend_payload.get("comments", 0))
        trend_score = self._safe_float(
            trend_payload.get("trend_score", trend_payload.get("search_interest", 0))
        )
        compound = self._safe_float(trend_payload.get("compound_score", 0))
        platform = str(trend_payload.get("platform", "reddit")).lower()

        upvote_component = min(45.0, upvotes / 400.0)
        comment_component = min(25.0, comments / 25.0)
        trend_component = max(0.0, min(20.0, trend_score * 0.2 if trend_score > 1 else trend_score * 20.0))
        sentiment_component = self._sentiment_bonus(compound)
        platform_weight = self._platform_weight(platform)

        virality_score = round(
            max(
                0.0,
                min(
                    100.0,
                    upvote_component
                    + comment_component
                    + trend_component
                    + sentiment_component
                    + platform_weight,
                ),
            ),
            2,
        )

        return ViralityResult(
            virality_score=virality_score,
            virality_label=self._label_from_score(virality_score),
        ).to_dict()

    def score_trend(self, trend_payload: dict[str, Any]) -> float:
        """Backward-compatible helper returning only the score."""

        return float(self.analyze_trend(trend_payload)["virality_score"])

    def _platform_weight(self, platform: str) -> float:
        weights = {
            "reddit": 10.0,
            "google_trends": 8.0,
        }
        return weights.get(platform, 7.0)

    def _sentiment_bonus(self, compound: float) -> float:
        if compound >= 0.35:
            return 8.0
        if compound >= 0.05:
            return 5.0
        if compound <= -0.35:
            return -6.0
        if compound <= -0.05:
            return -3.0
        return 0.0

    def _label_from_score(self, score: float) -> str:
        if score >= 75:
            return "High Viral"
        if score >= 45:
            return "Medium Viral"
        return "Low Viral"

    def _safe_float(self, value: Any) -> float:
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0
