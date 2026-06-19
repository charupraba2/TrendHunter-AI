"""RAG-style historical trend intelligence service."""

from __future__ import annotations

import json
import logging
from difflib import SequenceMatcher
from typing import Any

from backend.database import get_all_trends, get_alerts
from backend.services.gemini_service import GeminiService

logger = logging.getLogger(__name__)


class RAGService:
    def __init__(self) -> None:
        self.gemini_service = GeminiService()

    def retrieve_similar_trends(self, title: str, description: str = "", limit: int = 5, region: str | None = None) -> list[dict[str, Any]]:
        title_norm = self._normalize_text(title)
        description_norm = self._normalize_text(description)
        candidate_trends = get_all_trends(limit=500, region=region)
        alert_trend_ids = {alert["trend_id"] for alert in get_alerts(500)}

        scored: list[dict[str, Any]] = []
        for trend in candidate_trends:
            trend_title = self._normalize_text(trend.get("title") or trend.get("name") or "")
            if not trend_title:
                continue

            if title_norm and trend_title == title_norm and self._normalize_text(trend.get("description") or "") == description_norm:
                continue

            score = self._similarity_score(title_norm, description_norm, trend)
            if score <= 0:
                continue

            enriched = dict(trend)
            enriched["similarity_score"] = round(score, 2)
            enriched["has_alert"] = trend.get("id") in alert_trend_ids
            scored.append(enriched)

        scored.sort(key=lambda item: (item.get("similarity_score", 0), self._safe_number(item.get("virality_score"))), reverse=True)
        return scored[:limit]

    def build_rag_context(self, similar_trends: list[dict[str, Any]]) -> str:
        if not similar_trends:
            return "No strong historical matches were found."

        lines = []
        for index, trend in enumerate(similar_trends, start=1):
            lines.append(
                {
                    "index": index,
                    "title": trend.get("title"),
                    "platform": trend.get("platform"),
                    "source_label": trend.get("source_label"),
                    "category": trend.get("category"),
                    "source_type": trend.get("source_type"),
                    "virality_score": trend.get("virality_score"),
                    "virality_label": trend.get("virality_label"),
                    "has_alert": trend.get("has_alert", False),
                    "summary": trend.get("summary"),
                    "description": trend.get("description"),
                    "similarity_score": trend.get("similarity_score"),
                }
            )
        return json.dumps(lines, ensure_ascii=False, indent=2)

    def rag_analyze_trend(self, title: str, description: str = "", region: str | None = None) -> dict[str, Any]:
        title = (title or "").strip()
        description = (description or "").strip()

        if not title:
            raise ValueError("title is required for RAG analysis")

        similar_trends = self.retrieve_similar_trends(title, description, region=region)
        context = self.build_rag_context(similar_trends)

        gemini_analysis = self._generate_rag_analysis(title, description, similar_trends, context)

        return {
            "current_trend": title,
            "similar_trends": similar_trends,
            "rag_analysis": gemini_analysis,
        }

    def _generate_rag_analysis(
        self,
        title: str,
        description: str,
        similar_trends: list[dict[str, Any]],
        context: str,
    ) -> dict[str, Any]:
        if self.gemini_service._client is None:
            logger.info("Gemini unavailable for RAG analysis. Using fallback analysis for %s", title)
            return self._demo_rag_analysis(title, description, similar_trends)

        prompt = self._build_prompt(title, description, context)
        try:
            model = self.gemini_service._client.GenerativeModel("gemini-2.5-flash")
            response = model.generate_content(prompt)
            raw_text = getattr(response, "text", "")
            parsed = self._parse_json(raw_text)
            if parsed:
                return self._normalize_output(parsed, title, similar_trends)
        except Exception as exc:
            logger.warning("RAG Gemini analysis failed for %s: %s", title, exc)

        return self._demo_rag_analysis(title, description, similar_trends)

    def _build_prompt(self, title: str, description: str, context: str) -> str:
        return (
            "You are a RAG-based trend intelligence assistant for content creators. "
            "Use the provided historical trend context to reason about the current trend. "
            "Return ONLY valid JSON with these keys: summary, historical_comparison, virality_prediction, content_opportunities, risk_level, final_recommendation.\n"
            f"Current trend title: {title}\n"
            f"Current trend description: {description or 'No description provided.'}\n"
            f"Historical context:\n{context}\n"
            "Use the historical examples to explain how this trend compares, why it may grow, and what content opportunities exist."
        )

    def _demo_rag_analysis(
        self,
        title: str,
        description: str,
        similar_trends: list[dict[str, Any]],
    ) -> dict[str, Any]:
        if similar_trends:
            top_sources = ", ".join(
                sorted({str(item.get("platform") or item.get("source_label") or "mixed") for item in similar_trends[:3]})
            )
            top_titles = ", ".join(item.get("title", "") for item in similar_trends[:3])
        else:
            top_sources = "historical trends"
            top_titles = "No close matches were found"

        opportunities = [
            f"Create a short-form explainer connecting {title} to proven creator workflows.",
            f"Show a side-by-side comparison between the current trend and {top_sources}.",
            "Turn the historical pattern into a repeatable hook, demo, or template.",
        ]

        return {
            "summary": f"{title} is similar to past creator and platform trends, especially {top_titles}.",
            "historical_comparison": f"Historical signals suggest this topic behaves like prior {top_sources} trends that rewarded fast, practical content.",
            "virality_prediction": "Moderate to high growth potential if the topic stays useful and visually easy to package.",
            "content_opportunities": opportunities,
            "risk_level": "Medium",
            "final_recommendation": f"Act quickly with creator-friendly content before the trend matures, using the strongest patterns from past winners.",
        }

    def _normalize_output(self, data: dict[str, Any], title: str, similar_trends: list[dict[str, Any]]) -> dict[str, Any]:
        opportunities = data.get("content_opportunities", [])
        if isinstance(opportunities, str):
            opportunities = [item.strip() for item in opportunities.split("\n") if item.strip()]
        elif not isinstance(opportunities, list):
            opportunities = []

        if not opportunities:
            opportunities = self._demo_rag_analysis(title, "", similar_trends)["content_opportunities"]

        return {
            "summary": str(data.get("summary", "")).strip()
            or f"{title} shows recurring signals seen in past successful trends.",
            "historical_comparison": str(data.get("historical_comparison", "")).strip()
            or "The trend aligns with patterns seen in previously high-engagement topics.",
            "virality_prediction": str(data.get("virality_prediction", "")).strip()
            or "Virality looks promising if creators make it practical and easy to share.",
            "content_opportunities": opportunities,
            "risk_level": str(data.get("risk_level", "")).strip() or "Medium",
            "final_recommendation": str(data.get("final_recommendation", "")).strip()
            or "Use the trend quickly while the audience interest is still rising.",
        }

    def _similarity_score(self, title_norm: str, description_norm: str, trend: dict[str, Any]) -> float:
        trend_title = self._normalize_text(trend.get("title") or trend.get("name") or "")
        trend_description = self._normalize_text(trend.get("description") or "")
        trend_source = self._normalize_text(
            " ".join(
                [
                    str(trend.get("platform") or ""),
                    str(trend.get("source_label") or ""),
                    str(trend.get("source_type") or ""),
                    str(trend.get("category") or ""),
                ]
            )
        )

        title_similarity = SequenceMatcher(None, title_norm, trend_title).ratio() if title_norm and trend_title else 0.0
        description_similarity = SequenceMatcher(None, description_norm, trend_description).ratio() if description_norm and trend_description else 0.0

        keyword_overlap = self._keyword_overlap(title_norm, trend_title) * 0.7 + self._keyword_overlap(description_norm, trend_description) * 0.3
        source_relevance = 1.0 if any(token in trend_source for token in self._keywords(title_norm + " " + description_norm)) else 0.0

        input_signal = self._estimate_signal(title_norm, description_norm)
        trend_virality = self._safe_number(trend.get("virality_score"))
        virality_relevance = max(0.0, 1.0 - min(1.0, abs(trend_virality - input_signal) / 100.0))

        score = (
            (title_similarity * 40.0)
            + (description_similarity * 20.0)
            + (keyword_overlap * 20.0)
            + (source_relevance * 10.0)
            + (virality_relevance * 10.0)
        )
        return round(score, 4)

    def _keyword_overlap(self, source_text: str, target_text: str) -> float:
        source_tokens = self._keywords(source_text)
        target_tokens = self._keywords(target_text)
        if not source_tokens or not target_tokens:
            return 0.0
        intersection = len(source_tokens & target_tokens)
        union = len(source_tokens | target_tokens)
        return intersection / union if union else 0.0

    def _estimate_signal(self, title: str, description: str) -> float:
        text = f"{title} {description}".lower()
        signal = 35.0
        boost_terms = {
            "ai",
            "agent",
            "viral",
            "trend",
            "youtube",
            "news",
            "creator",
            "launch",
            "growth",
            "prompt",
            "video",
        }
        signal += sum(5.0 for term in boost_terms if term in text)
        if "breaking" in text or "hot" in text:
            signal += 10.0
        return min(100.0, signal)

    def _keywords(self, text: str) -> set[str]:
        return {
            token.strip(".,!?;:\"'()[]{}").lower()
            for token in text.split()
            if len(token.strip(".,!?;:\"'()[]{}")) > 2
        }

    def _normalize_text(self, text: str) -> str:
        return " ".join(
            token.strip(".,!?;:\"'()[]{}").lower()
            for token in (text or "").split()
            if token.strip(".,!?;:\"'()[]{}")
        )

    def _safe_number(self, value: Any) -> float:
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0

    def _parse_json(self, text: str) -> dict[str, Any] | None:
        if not text:
            return None

        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            cleaned = cleaned.replace("json", "", 1).strip()

        try:
            parsed = json.loads(cleaned)
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            return None
