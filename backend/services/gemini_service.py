"""Gemini analysis service for live trends."""

from __future__ import annotations

import json
import logging
from typing import Any

from backend.config import settings

logger = logging.getLogger(__name__)


class GeminiService:
    def __init__(self) -> None:
        self.api_key = settings.gemini_api_key.strip()
        self._client = self._load_client() if self.api_key else None

    def _load_client(self):
        try:
            import google.generativeai as genai
        except Exception:
            logger.warning("google-generativeai is not available.")
            return None

        try:
            genai.configure(api_key=self.api_key)
            return genai
        except Exception as exc:
            logger.warning("Gemini client could not be configured: %s", exc)
            return None

    def analyze_trend(self, title: str, description: str = "") -> dict[str, Any]:
        title = (title or "").strip()
        description = (description or "").strip()

        if not title:
            return self._demo_analysis("Untitled trend", description)

        if self._client is None:
            logger.info("Gemini API key missing or client unavailable. Using demo analysis for %s", title)
            return self._demo_analysis(title, description)

        prompt = self._build_prompt(title, description)
        try:
            model = self._client.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(prompt)
            parsed = self._parse_json(getattr(response, "text", ""))
            if parsed:
                analysis = self._normalize_analysis(parsed, title, description)
                logger.info("Gemini analysis generated successfully for %s", title)
                return analysis
        except Exception as exc:
            logger.warning("Gemini analysis failed for %s: %s", title, exc)

        return self._demo_analysis(title, description)

    def _build_prompt(self, title: str, description: str) -> str:
        return (
            "You are an expert trend analyst for creators and marketers. "
            "Return ONLY valid JSON with these keys: trend_summary, why_it_is_trending, virality_explanation, audience_interest, future_prediction.\n"
            f"Trend title: {title}\n"
            f"Trend description: {description or 'No description provided.'}\n"
            "Keep the analysis concise, practical, and production-ready."
        )

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

    def _normalize_analysis(self, data: dict[str, Any], title: str, description: str) -> dict[str, Any]:
        return {
            "trend_summary": str(data.get("trend_summary", "")).strip()
            or f"{title} is attracting attention across creator and audience communities.",
            "why_it_is_trending": str(data.get("why_it_is_trending", "")).strip()
            or "It combines strong relevance, repeatable discussion points, and clear audience curiosity.",
            "virality_explanation": str(data.get("virality_explanation", "")).strip()
            or "The topic has the right mix of novelty, utility, and shareability to keep spreading.",
            "audience_interest": str(data.get("audience_interest", "")).strip()
            or "Creators, early adopters, and niche communities are likely to engage with this trend.",
            "future_prediction": str(data.get("future_prediction", "")).strip()
            or "Expect this trend to continue growing if creators keep packaging it into short-form content.",
            "title": title,
            "description": description,
        }

    def _demo_analysis(self, title: str, description: str) -> dict[str, Any]:
        return {
            "trend_summary": f"{title} is gaining attention because it connects current audience curiosity with practical creator opportunities.",
            "why_it_is_trending": "The topic has strong momentum, clear utility, and easy-to-share talking points.",
            "virality_explanation": "It is well suited to fast distribution across short-form video, social posts, and creator commentary.",
            "audience_interest": "Creators, marketers, and curious viewers are likely to follow this topic closely.",
            "future_prediction": "If the momentum continues, this trend will likely appear across more creator channels and community posts.",
            "title": title,
            "description": description,
        }
