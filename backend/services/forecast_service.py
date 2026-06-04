"""AI virality forecasting service for TrendHunter AI."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Any

from backend.database import get_all_trends, get_alerts
from backend.services.gemini_service import GeminiService

logger = logging.getLogger(__name__)

try:  # Optional enhancement. The app still works without sklearn runtime support.
    from sklearn.ensemble import RandomForestRegressor
except Exception:  # pragma: no cover - optional dependency guard
    RandomForestRegressor = None


class ForecastService:
    def __init__(self) -> None:
        self.gemini_service = GeminiService()
        self._model = None
        self._model_ready = False

    def retrieve_similar_trends(self, title: str, description: str = "", limit: int = 5) -> list[dict[str, Any]]:
        title_norm = self._normalize_text(title)
        description_norm = self._normalize_text(description)
        historical_trends = get_all_trends(limit=500)
        alert_trend_ids = {alert["trend_id"] for alert in get_alerts(500)}

        scored: list[dict[str, Any]] = []
        for trend in historical_trends:
            trend_title = self._normalize_text(trend.get("title") or trend.get("name") or "")
            if not trend_title:
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

    def build_forecast_context(self, similar_trends: list[dict[str, Any]]) -> str:
        if not similar_trends:
            return "No strong historical matches were found."

        payload = []
        for index, trend in enumerate(similar_trends, start=1):
            payload.append(
                {
                    "index": index,
                    "title": trend.get("title"),
                    "platform": trend.get("platform"),
                    "source_label": trend.get("source_label"),
                    "source_type": trend.get("source_type"),
                    "virality_score": trend.get("virality_score"),
                    "virality_label": trend.get("virality_label"),
                    "prediction_label": trend.get("prediction_label"),
                    "opportunity_score": trend.get("opportunity_score"),
                    "risk_score": trend.get("risk_score"),
                    "has_alert": trend.get("has_alert", False),
                    "summary": trend.get("summary"),
                    "description": trend.get("description"),
                    "similarity_score": trend.get("similarity_score"),
                }
            )
        return json.dumps(payload, ensure_ascii=False, indent=2)

    def forecast_trend_growth(self, title: str, description: str = "", trend: dict[str, Any] | None = None) -> dict[str, Any]:
        title = (title or "").strip()
        description = (description or "").strip()
        if not title:
            raise ValueError("title is required for forecasting")

        self._ensure_model()

        current_trend = dict(trend or self._find_best_trend(title, description) or {})
        similar_trends = self.retrieve_similar_trends(title, description)
        context = self.build_forecast_context(similar_trends)

        heuristic = self._heuristic_forecast(title, description, current_trend, similar_trends)
        ai_forecast = self._generate_ai_forecast(title, description, current_trend, similar_trends, context, heuristic)

        forecast = {
            **heuristic,
            **ai_forecast,
            "forecast_updated_at": datetime.now(timezone.utc).isoformat(),
        }

        return {
            "current_trend": current_trend.get("title") or title,
            "trend_id": current_trend.get("id"),
            "trend": current_trend or None,
            "similar_trends": similar_trends,
            "forecast": forecast,
        }

    def forecast_live_trends(self, trends: list[dict[str, Any]] | None = None, limit: int = 100) -> list[dict[str, Any]]:
        trend_list = trends or get_all_trends(limit=limit)
        self._ensure_model()
        results: list[dict[str, Any]] = []
        for trend in trend_list:
            title = trend.get("title") or trend.get("name") or "Untitled trend"
            description = trend.get("description") or trend.get("summary") or ""
            forecast_result = self.forecast_trend_growth(title=title, description=description, trend=trend)
            forecast = forecast_result["forecast"]
            results.append(
                {
                    **trend,
                    **forecast,
                    "similar_trends": forecast_result.get("similar_trends", []),
                    "current_trend": forecast_result.get("current_trend"),
                }
            )
        return results

    def _generate_ai_forecast(
        self,
        title: str,
        description: str,
        trend: dict[str, Any],
        similar_trends: list[dict[str, Any]],
        context: str,
        heuristic: dict[str, Any],
    ) -> dict[str, Any]:
        if self.gemini_service._client is None:
            logger.info("Gemini unavailable for forecasting. Using demo forecast for %s", title)
            return self._demo_forecast(title, description, similar_trends, heuristic)

        prompt = self._build_prompt(title, description, trend, similar_trends, context, heuristic)
        try:
            model = self.gemini_service._client.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(prompt)
            raw_text = getattr(response, "text", "")
            parsed = self._parse_json(raw_text)
            if parsed:
                return self._normalize_ai_output(parsed, title, similar_trends, heuristic)
        except Exception as exc:
            logger.warning("Forecast Gemini analysis failed for %s: %s", title, exc)

        return self._demo_forecast(title, description, similar_trends, heuristic)

    def _build_prompt(
        self,
        title: str,
        description: str,
        trend: dict[str, Any],
        similar_trends: list[dict[str, Any]],
        context: str,
        heuristic: dict[str, Any],
    ) -> str:
        return (
            "You are a trend forecasting assistant for creators and growth teams. "
            "Use the historical context and heuristic signal to forecast whether the trend will grow, stabilize, or decline over the next 24-48 hours. "
            "Return ONLY valid JSON with these keys: forecast_explanation, why_the_trend_may_grow, possible_audience_behavior, recommended_creator_actions, business_opportunity_analysis.\n"
            f"Current trend title: {title}\n"
            f"Current trend description: {description or 'No description provided.'}\n"
            f"Current trend source: {trend.get('platform') or trend.get('source_type') or 'unknown'}\n"
            f"Heuristic signal: {json.dumps(heuristic, ensure_ascii=False)}\n"
            f"Historical context:\n{context}\n"
            "Keep the output concise, practical, and action-oriented."
        )

    def _normalize_ai_output(self, data: dict[str, Any], title: str, similar_trends: list[dict[str, Any]], heuristic: dict[str, Any]) -> dict[str, Any]:
        actions = data.get("recommended_creator_actions", [])
        if isinstance(actions, str):
            actions = [line.strip("-• ").strip() for line in actions.split("\n") if line.strip("-• ").strip()]
        elif not isinstance(actions, list):
            actions = []

        if not actions:
            actions = self._demo_forecast(title, "", similar_trends, heuristic)["recommended_creator_actions"]

        return {
            "forecast_explanation": str(data.get("forecast_explanation", "")).strip()
            or f"{title} has a measurable signal based on historical engagement and recent trend velocity.",
            "why_the_trend_may_grow": str(data.get("why_the_trend_may_grow", "")).strip()
            or "The topic has repeatable hooks, strong creator relevance, and enough momentum to keep spreading.",
            "possible_audience_behavior": str(data.get("possible_audience_behavior", "")).strip()
            or "Audiences may save, share, and comment more when the trend is packaged into practical examples.",
            "recommended_creator_actions": actions,
            "business_opportunity_analysis": str(data.get("business_opportunity_analysis", "")).strip()
            or "There is a near-term opportunity to create educational, reaction, and workflow content.",
        }

    def _demo_forecast(
        self,
        title: str,
        description: str,
        similar_trends: list[dict[str, Any]],
        heuristic: dict[str, Any],
    ) -> dict[str, Any]:
        similar_count = len(similar_trends)
        stage = heuristic.get("growth_stage", "growing")
        return {
            "forecast_explanation": f"{title} is showing a {stage} pattern backed by {similar_count} similar historical signals.",
            "why_the_trend_may_grow": "The topic has search relevance, audience familiarity, and creator-friendly packaging potential.",
            "possible_audience_behavior": "Viewers are likely to respond with fast engagement if the topic is turned into short, actionable content.",
            "recommended_creator_actions": [
                f"Open with a strong hook around {title}.",
                "Use before/after or comparison-style visuals.",
                "Post quickly while the signal is still fresh.",
            ],
            "business_opportunity_analysis": "This trend may support sponsored explainers, niche tutorials, and short-form educational content.",
        }

    def _heuristic_forecast(
        self,
        title: str,
        description: str,
        trend: dict[str, Any],
        similar_trends: list[dict[str, Any]],
    ) -> dict[str, Any]:
        title_norm = self._normalize_text(title)
        description_norm = self._normalize_text(description)

        upvotes = self._safe_number(trend.get("upvotes"))
        comments = self._safe_number(trend.get("comments"))
        trend_score = self._safe_number(trend.get("trend_score") or trend.get("search_interest"))
        virality_score = self._safe_number(trend.get("virality_score"))
        sentiment_compound = self._safe_number(trend.get("compound_score"))
        source_weight = self._source_weight(trend)
        age_hours = self._age_hours(trend)

        historical_signal = 0.0
        viral_matches = 0
        for item in similar_trends:
            item_virality = self._safe_number(item.get("virality_score"))
            if item_virality >= 75:
                viral_matches += 1
            historical_signal += item_virality * (item.get("similarity_score", 0) / 100.0)

        keyword_pressure = self._keyword_frequency(title_norm, description_norm, similar_trends)
        engagement_signal = (
            min(100.0, upvotes / 250.0)
            + min(100.0, comments / 50.0)
            + min(100.0, trend_score)
            + min(100.0, virality_score)
        ) / 4.0

        historical_average = historical_signal / max(1, len(similar_trends))
        if self._model is not None:
            model_signal = self._predict_with_model(trend, similar_trends)
        else:
            model_signal = historical_average

        virality_probability = self._clamp(
            (
                engagement_signal * 0.38
                + historical_average * 0.22
                + keyword_pressure * 0.16
                + source_weight * 12.0
                + max(0.0, sentiment_compound) * 10.0
                + model_signal * 0.12
                - min(age_hours / 24.0, 4.0) * 4.5
            )
            / 100.0,
            0.05,
            0.98,
        )

        forecast_confidence = self._clamp(
            40.0
            + min(20.0, len(similar_trends) * 3.5)
            + min(15.0, viral_matches * 4.0)
            + min(10.0, max(0.0, source_weight * 4.0))
            + min(15.0, keyword_pressure * 12.0),
            35.0,
            95.0,
        )

        opportunity_score = self._clamp(
            (virality_probability * 100.0) * 0.5
            + engagement_signal * 0.3
            + keyword_pressure * 20.0
            + source_weight * 8.0,
            0.0,
            100.0,
        )

        risk_score = self._clamp(
            (100.0 - opportunity_score) * 0.55
            + min(age_hours / 24.0, 5.0) * 7.0
            + max(0.0, -sentiment_compound) * 12.0,
            0.0,
            100.0,
        )

        expected_engagement = self._clamp(
            engagement_signal * 0.55 + historical_average * 0.2 + opportunity_score * 0.25,
            0.0,
            100.0,
        )

        prediction_label = self._prediction_label(virality_probability, opportunity_score, risk_score)
        growth_stage = self._growth_stage_from_prediction(prediction_label)

        return {
            "virality_probability": round(virality_probability, 4),
            "forecast_confidence": round(forecast_confidence, 2),
            "growth_stage": growth_stage,
            "prediction_label": prediction_label,
            "expected_engagement": round(expected_engagement, 2),
            "opportunity_score": round(opportunity_score, 2),
            "risk_score": round(risk_score, 2),
            "virality_score": round(self._clamp(virality_probability * 100.0 + opportunity_score * 0.18 - risk_score * 0.08, 0.0, 100.0), 2),
        }

    def _prediction_label(self, virality_probability: float, opportunity_score: float, risk_score: float) -> str:
        if virality_probability >= 0.82 and opportunity_score >= 75:
            return "EXPLODING"
        if virality_probability >= 0.68:
            return "GROWING"
        if virality_probability >= 0.46:
            return "STABLE"
        if risk_score >= 65:
            return "DECLINING"
        return "SATURATED"

    def _growth_stage_from_prediction(self, prediction_label: str) -> str:
        mapping = {
            "EXPLODING": "accelerating",
            "GROWING": "growing",
            "STABLE": "stable",
            "DECLINING": "cooling",
            "SATURATED": "saturated",
        }
        return mapping.get(prediction_label, "growing")

    def _build_optional_model(self):
        if RandomForestRegressor is None:
            logger.info("Optional sklearn forecast model unavailable.")
            return None

        trends = [trend for trend in get_all_trends(limit=400) if trend.get("virality_score") is not None]
        if len(trends) < 20:
            return None

        features: list[list[float]] = []
        targets: list[float] = []
        for trend in trends:
            features.append(self._feature_vector(trend))
            targets.append(self._safe_number(trend.get("virality_score")))

        try:
            model = RandomForestRegressor(n_estimators=60, random_state=42)
            model.fit(features, targets)
            logger.info("Forecast model trained on %s historical trends.", len(features))
            return model
        except Exception as exc:
            logger.warning("Forecast model training failed: %s", exc)
            return None

    def _ensure_model(self) -> None:
        if self._model_ready:
            return
        self._model_ready = True
        self._model = self._build_optional_model()

    def _predict_with_model(self, trend: dict[str, Any], similar_trends: list[dict[str, Any]]) -> float:
        if self._model is None:
            return 0.0
        try:
            prediction = float(self._model.predict([self._feature_vector(trend, similar_trends)])[0])
            return self._clamp(prediction, 0.0, 100.0)
        except Exception as exc:
            logger.warning("Forecast model prediction failed: %s", exc)
            return 0.0

    def _feature_vector(self, trend: dict[str, Any], similar_trends: list[dict[str, Any]] | None = None) -> list[float]:
        similar_trends = similar_trends or []
        viral_matches = sum(1 for item in similar_trends if self._safe_number(item.get("virality_score")) >= 75)
        return [
            self._safe_number(trend.get("upvotes")),
            self._safe_number(trend.get("comments")),
            self._safe_number(trend.get("trend_score") or trend.get("search_interest")),
            self._safe_number(trend.get("virality_score")),
            self._safe_number(trend.get("compound_score")),
            self._source_weight(trend) * 100.0,
            self._age_hours(trend),
            len(similar_trends),
            viral_matches,
            self._keyword_frequency(
                self._normalize_text(trend.get("title") or trend.get("name") or ""),
                self._normalize_text(trend.get("description") or ""),
                similar_trends,
            )
            * 100.0,
        ]

    def _find_best_trend(self, title: str, description: str) -> dict[str, Any] | None:
        candidates = self.retrieve_similar_trends(title, description, limit=1)
        if not candidates:
            return None
        best = candidates[0]
        return best if self._safe_number(best.get("similarity_score")) >= 35.0 else None

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
        keyword_overlap = self._keyword_overlap(title_norm, trend_title) * 0.65 + self._keyword_overlap(description_norm, trend_description) * 0.35
        source_relevance = 1.0 if any(token in trend_source for token in self._keywords(f"{title_norm} {description_norm}")) else 0.0

        trend_virality = self._safe_number(trend.get("virality_score"))
        input_signal = self._signal_from_text(title_norm, description_norm)
        virality_relevance = max(0.0, 1.0 - min(1.0, abs(trend_virality - input_signal) / 100.0))

        score = (
            (title_similarity * 40.0)
            + (description_similarity * 20.0)
            + (keyword_overlap * 20.0)
            + (source_relevance * 10.0)
            + (virality_relevance * 10.0)
        )
        return round(score, 4)

    def _signal_from_text(self, title: str, description: str) -> float:
        text = f"{title} {description}".lower()
        signal = 35.0
        boost_terms = {"ai", "agent", "viral", "trend", "youtube", "news", "creator", "launch", "growth", "prompt", "video", "forecast"}
        signal += sum(5.0 for term in boost_terms if term in text)
        if "breaking" in text or "hot" in text:
            signal += 10.0
        return min(100.0, signal)

    def _keyword_frequency(self, title_norm: str, description_norm: str, similar_trends: list[dict[str, Any]]) -> float:
        tokens = self._keywords(f"{title_norm} {description_norm}")
        if not tokens or not similar_trends:
            return 0.0
        count = 0
        total = 0
        for trend in similar_trends:
            trend_tokens = self._keywords(
                " ".join(
                    [
                        str(trend.get("title") or trend.get("name") or ""),
                        str(trend.get("description") or ""),
                        str(trend.get("platform") or ""),
                        str(trend.get("source_label") or ""),
                    ]
                )
            )
            total += len(trend_tokens) or 1
            count += len(tokens & trend_tokens)
        return count / total if total else 0.0

    def _keyword_overlap(self, source_text: str, target_text: str) -> float:
        source_tokens = self._keywords(source_text)
        target_tokens = self._keywords(target_text)
        if not source_tokens or not target_tokens:
            return 0.0
        intersection = len(source_tokens & target_tokens)
        union = len(source_tokens | target_tokens)
        return intersection / union if union else 0.0

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

    def _clamp(self, value: float, minimum: float, maximum: float) -> float:
        return max(minimum, min(maximum, value))

    def _source_weight(self, trend: dict[str, Any]) -> float:
        platform = str(trend.get("platform") or trend.get("source_type") or "").lower()
        weights = {
            "reddit": 1.05,
            "google_trends": 1.00,
            "news": 0.98,
            "newsapi": 0.98,
            "youtube": 1.08,
        }
        return weights.get(platform, 1.0)

    def _age_hours(self, trend: dict[str, Any]) -> float:
        for key in ("forecast_updated_at", "analyzed_at", "fetched_at", "created_utc", "published_at"):
            value = trend.get(key)
            if not value:
                continue
            parsed = self._parse_datetime(value)
            if parsed is not None:
                return max(0.0, (datetime.now(timezone.utc) - parsed).total_seconds() / 3600.0)
        return 0.0

    def _parse_datetime(self, value: Any) -> datetime | None:
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value, tz=timezone.utc)
        if isinstance(value, str):
            try:
                parsed = datetime.fromisoformat(value)
                return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
            except ValueError:
                return None
        return None

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
