"""Gemini-powered content idea generation with a demo fallback."""

from __future__ import annotations

import json
import os
from typing import Any

from backend.config import settings


class ContentAgent:
    def __init__(self) -> None:
        self.api_key = os.getenv("GEMINI_API_KEY", settings.gemini_api_key).strip()
        self._client = self._load_client() if self.api_key else None

    def _load_client(self):
        try:
            import google.generativeai as genai
        except Exception:
            return None

        try:
            genai.configure(api_key=self.api_key)
            return genai
        except Exception:
            return None

    def generate_content_idea(self, trend: dict[str, Any]) -> dict[str, Any]:
        """Generate structured content ideas for an analyzed trend."""

        if self._client is None:
            return self._demo_content_idea(trend)

        prompt = self._build_prompt(trend)
        try:
            model = self._client.GenerativeModel("gemini-2.5-flash")
            response = model.generate_content(prompt)
            parsed = self._parse_response_text(getattr(response, "text", ""))
            if parsed:
                return self._normalize_output(parsed, trend)
        except Exception:
            return self._demo_content_idea(trend)

        return self._demo_content_idea(trend)

    def build_content_brief(self, trend: dict) -> dict:
        title = trend.get("name", "Untitled trend")
        category = trend.get("category", "general")
        return {
            "hook": f"Why {title} is gaining momentum right now",
            "angles": [
                f"Explain the opportunity for creators in {category}.",
                "Show a practical workflow people can copy today.",
                "End with a strong call to action and a clear takeaway.",
            ],
            "headline": title,
        }

    def _build_prompt(self, trend: dict[str, Any]) -> str:
        return (
            "You are a creator-strategy assistant. "
            "Return ONLY valid JSON with these keys: hook, reel_idea, youtube_shorts_idea, caption, hashtags, content_angle.\n"
            f"Trend title: {trend.get('title') or trend.get('name') or 'Untitled trend'}\n"
            f"Platform: {trend.get('platform', 'unknown')}\n"
            f"Sentiment label: {trend.get('sentiment_label', 'Neutral')}\n"
            f"Virality score: {trend.get('virality_score', 0)}\n"
            f"Virality label: {trend.get('virality_label', 'Low Viral')}\n"
            "Write concise, high-performing ideas for short-form creators."
        )

    def _parse_response_text(self, text: str) -> dict[str, Any] | None:
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

    def _normalize_output(self, data: dict[str, Any], trend: dict[str, Any]) -> dict[str, Any]:
        hashtags = data.get("hashtags", [])
        if isinstance(hashtags, str):
            hashtags = [tag.strip() for tag in hashtags.split(",") if tag.strip()]
        elif not isinstance(hashtags, list):
            hashtags = []

        return {
            "hook": str(data.get("hook", "")).strip() or self._demo_content_idea(trend)["hook"],
            "reel_idea": str(data.get("reel_idea", "")).strip() or self._demo_content_idea(trend)["reel_idea"],
            "youtube_shorts_idea": str(data.get("youtube_shorts_idea", "")).strip()
            or self._demo_content_idea(trend)["youtube_shorts_idea"],
            "caption": str(data.get("caption", "")).strip() or self._demo_content_idea(trend)["caption"],
            "hashtags": hashtags or self._demo_content_idea(trend)["hashtags"],
            "content_angle": str(data.get("content_angle", "")).strip()
            or self._demo_content_idea(trend)["content_angle"],
        }

    def _demo_content_idea(self, trend: dict[str, Any]) -> dict[str, Any]:
        title = trend.get("title") or trend.get("name") or "the trend"
        platform = trend.get("platform", "social")
        sentiment = trend.get("sentiment_label", "Neutral")
        virality = trend.get("virality_label", "Low Viral")
        hashtag_base = "".join(ch for ch in title.lower() if ch.isalnum() or ch == " ").split()
        hashtags = [f"#{word}" for word in hashtag_base[:4]] or ["#trend", "#creator", "#ai"]
        return {
            "hook": f"Why {title} is worth paying attention to right now",
            "reel_idea": f"Create a fast-paced breakdown showing how {platform} creators can act on {title}.",
            "youtube_shorts_idea": f"Make a 30-second tutorial on how to turn {title} into a repeatable content format.",
            "caption": f"Sentiment: {sentiment}. Virality: {virality}. Here is the next move for creators tracking {title}.",
            "hashtags": hashtags,
            "content_angle": f"A creator-first angle focused on converting {title} into practical content ideas.",
        }
