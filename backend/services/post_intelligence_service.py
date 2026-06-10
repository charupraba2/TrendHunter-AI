"""Compatibility service for creator/post intelligence analysis."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from backend.services.creator_intelligence_service import CreatorIntelligenceService

logger = logging.getLogger(__name__)


class PostIntelligenceService(CreatorIntelligenceService):
    """Backwards-compatible alias for the creator intelligence workflow."""

    def analyze_post(
        self,
        platform: str,
        title: str,
        caption: str = "",
        hashtags: str | list[str] | None = None,
        content_type: str = "",
        audience: str = "",
        target_audience: str = "",
        region: str = "Global",
        thumbnail_result: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        audience_value = (target_audience or audience or "").strip()
        try:
            return self.analyze_creator_post(
                platform=platform,
                title=title,
                caption=caption,
                hashtags=hashtags,
                content_type=content_type,
                audience=audience_value,
                region=region,
                thumbnail_result=thumbnail_result,
            )
        except ValueError:
            raise
        except Exception:
            logger.exception("Creator analysis failed")
            return self._fallback_response(
                platform=platform,
                title=title,
                caption=caption,
                hashtags=hashtags,
                content_type=content_type,
                audience=audience_value,
                region=region,
                thumbnail_result=thumbnail_result,
            )

    def _fallback_response(
        self,
        platform: str,
        title: str,
        caption: str = "",
        hashtags: str | list[str] | None = None,
        content_type: str = "",
        audience: str = "",
        region: str = "Global",
        thumbnail_result: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        platform_key = (platform or "").strip().lower() or "instagram"
        title = (title or "").strip() or "Untitled post idea"
        caption = (caption or "").strip()
        content_type = (content_type or "").strip() or "Post"
        audience = (audience or "").strip() or "General audience"
        normalized_hashtags = self._normalize_hashtags(hashtags, title)
        warnings = [
            "AI fallback mode was used because the primary creator analysis path was unavailable.",
        ]
        if not caption:
            warnings.append("Caption was empty, so the fallback used the title context.")
        if not normalized_hashtags:
            warnings.append("No valid hashtags were provided, so fallback suggestions were generated.")

        context_description = " ".join(part for part in [caption, content_type, audience] if part).strip()
        base_trend = self._build_trend_context(platform_key, title, caption, normalized_hashtags, content_type, audience)

        try:
            similar_trends = self.rag_service.retrieve_similar_trends(title, context_description or caption or title, limit=5, region=region)
        except Exception:
            similar_trends = []

        try:
            rag_result = self.rag_service.rag_analyze_trend(title=title, description=context_description or caption or title, region=region)
        except Exception:
            rag_result = {
                "current_trend": title,
                "similar_trends": similar_trends,
                "rag_analysis": {
                    "summary": f"{title} appears to be a creator-relevant concept with practical content potential.",
                    "historical_comparison": "No reliable RAG context was available, so the fallback used a conservative historical comparison.",
                    "virality_prediction": "Moderate growth potential with room to improve the hook and packaging.",
                    "content_opportunities": [
                        "Turn the idea into a short-form breakdown.",
                        "Use a clear before-and-after or framework format.",
                        "Test it as a hook-led post and a follow-up explainer.",
                    ],
                    "risk_level": "Medium",
                    "final_recommendation": "Publish a sharper creator-first version and refine based on audience response.",
                },
            }

        try:
            forecast_result = self.forecast_service.forecast_trend_growth(
                title=title,
                description=context_description or caption or title,
                trend=base_trend,
                region=region,
            )
        except Exception:
            forecast_result = {
                "forecast": {
                    "forecast_explanation": f"{title} has enough creator relevance to support a cautious growth forecast.",
                    "why_the_trend_may_grow": "The topic has enough utility and audience curiosity to support early engagement.",
                    "possible_audience_behavior": "Audiences may engage if the idea is packaged into a fast, useful format.",
                    "recommended_creator_actions": [
                        f"Lead with a direct hook around {title}.",
                        "Keep the post concise and action-oriented.",
                        "Use a strong call to action and visual payoff.",
                    ],
                    "business_opportunity_analysis": "This concept can support educational, reaction, and workflow-driven creator content.",
                }
            }

        forecast = forecast_result.get("forecast", {})
        similar_context = self.rag_service.build_rag_context(similar_trends)
        heuristic = self._heuristic_analysis(
            platform_key=platform_key,
            title=title,
            caption=caption,
            hashtags=normalized_hashtags,
            content_type=content_type,
            audience=audience,
            similar_trends=similar_trends,
            forecast=forecast,
        )
        recommendations = self._demo_recommendations(
            platform_key=platform_key,
            title=title,
            caption=caption,
            hashtags=normalized_hashtags,
            content_type=content_type,
            audience=audience,
            forecast=forecast,
            rag_result=rag_result,
            heuristic=heuristic,
        )

        analysis = {
            **heuristic,
            **recommendations,
            "platform": platform_key,
            "platform_label": self.SUPPORTED_PLATFORMS.get(platform_key, platform_key.title()),
            "content_type": content_type,
            "audience": audience,
            "region": region,
            "thumbnail_result": thumbnail_result or {},
            "normalized_hashtags": normalized_hashtags,
            "similar_trends": similar_trends,
            "forecast": forecast,
            "rag_analysis": rag_result.get("rag_analysis", {}),
            "warnings": warnings,
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }

        return {
            "current_request": {
                "platform": platform_key,
                "platform_label": analysis["platform_label"],
                "title": title,
                "caption": caption,
                "hashtags": normalized_hashtags,
                "content_type": content_type,
                "audience": audience,
                "region": region,
            },
            "similar_trends": similar_trends,
            "forecast": forecast,
            "rag_analysis": rag_result.get("rag_analysis", {}),
            "analysis": analysis,
            "recommendations": recommendations,
            "warnings": warnings,
            "fallback_used": True,
            "similar_context": similar_context,
        }


def analyze_creator_post(
    platform: str,
    title: str,
    caption: str,
        hashtags: str | list[str] | None,
        content_type: str,
        target_audience: str = "",
        audience: str = "",
        region: str = "Global",
        thumbnail_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Module-level compatibility helper used by the API route."""

    service = PostIntelligenceService()
    return service.analyze_post(
        platform=platform,
        title=title,
        caption=caption,
        hashtags=hashtags,
        content_type=content_type,
        audience=audience,
        target_audience=target_audience,
        region=region,
        thumbnail_result=thumbnail_result,
    )
