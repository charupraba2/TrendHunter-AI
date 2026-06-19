"""Creator intelligence workflow for AI post optimization."""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any

from backend.services.forecast_service import ForecastService
from backend.services.gemini_service import GeminiService
from backend.services.rag_service import RAGService

logger = logging.getLogger(__name__)


class CreatorIntelligenceService:
    """Analyze user-submitted posts like an AI content strategist."""

    SUPPORTED_PLATFORMS = {
        "instagram": "Instagram",
        "youtube": "YouTube",
        "linkedin": "LinkedIn",
        "twitter": "Twitter/X",
        "x": "Twitter/X",
        "reddit": "Reddit",
        "tiktok": "TikTok",
        "facebook": "Facebook",
    }

    def __init__(self) -> None:
        self.gemini_service = GeminiService()
        self.rag_service = RAGService()
        self.forecast_service = ForecastService()

    def analyze_creator_post(
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
        platform_key = self._normalize_platform(platform)
        title = (title or "").strip()
        caption = (caption or "").strip()
        content_type = (content_type or "").strip()
        audience = (audience or "").strip()
        if not title:
            raise ValueError("post title is required")

        normalized_hashtags = self._normalize_hashtags(hashtags, title)
        thumbnail_result = thumbnail_result if isinstance(thumbnail_result, dict) else {}
        warnings = []
        if not caption:
            warnings.append("Caption was empty, so the analysis used the title and content context instead.")
        if not normalized_hashtags:
            warnings.append("No valid hashtags were provided, so optimized suggestions were generated.")

        context_description = " ".join(part for part in [caption, content_type, audience] if part).strip()
        base_trend = self._build_trend_context(platform_key, title, caption, normalized_hashtags, content_type, audience)
        similar_trends = self.rag_service.retrieve_similar_trends(title, context_description or caption or title, limit=5, region=region)
        rag_result = self.rag_service.rag_analyze_trend(title=title, description=context_description or caption or title, region=region)
        forecast_result = self.forecast_service.forecast_trend_growth(
            title=title,
            description=context_description or caption or title,
            trend=base_trend,
            region=region,
        )

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
        platform_intelligence = self._platform_intelligence(
            platform_key=platform_key,
            title=title,
            caption=caption,
            hashtags=normalized_hashtags,
            content_type=content_type,
            audience=audience,
            heuristic=heuristic,
            forecast=forecast,
            thumbnail_result=thumbnail_result,
        )
        ai_recommendations = self._generate_ai_recommendations(
            platform_key=platform_key,
            title=title,
            caption=caption,
            hashtags=normalized_hashtags,
            content_type=content_type,
            audience=audience,
            forecast=forecast,
            rag_result=rag_result,
            similar_context=similar_context,
            heuristic=heuristic,
        )

        analysis = {
            **heuristic,
            **ai_recommendations,
            **platform_intelligence,
            "platform": platform_key,
            "platform_label": self.SUPPORTED_PLATFORMS.get(platform_key, platform_key.title()),
            "content_type": content_type or "Post",
            "audience": audience or "General audience",
            "region": region,
            "thumbnail_result": thumbnail_result,
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
                "content_type": content_type or "Post",
                "audience": audience or "General audience",
                "region": region,
                "thumbnail_result": thumbnail_result,
            },
            "similar_trends": similar_trends,
            "forecast": forecast,
            "rag_analysis": rag_result.get("rag_analysis", {}),
            "analysis": analysis,
            "warnings": warnings,
        }

    def _normalize_platform(self, platform: str) -> str:
        key = (platform or "").strip().lower()
        if key not in self.SUPPORTED_PLATFORMS:
            raise ValueError(
                "Unsupported platform. Choose from Instagram, YouTube, LinkedIn, Twitter/X, Reddit, TikTok, or Facebook."
            )
        return key

    def _normalize_hashtags(self, hashtags: str | list[str] | None, title: str) -> list[str]:
        values: list[str] = []
        if isinstance(hashtags, list):
            raw_items = hashtags
        elif isinstance(hashtags, str):
            raw_items = re.split(r"[,\s]+", hashtags)
        else:
            raw_items = []

        for item in raw_items:
            token = str(item).strip()
            if not token:
                continue
            token = token.lstrip("#")
            token = re.sub(r"[^a-zA-Z0-9_]+", "", token)
            if len(token) < 2:
                continue
            values.append(f"#{token.lower()}")

        if not values:
            base_terms = [term for term in re.findall(r"[A-Za-z0-9]+", title.lower()) if len(term) > 2]
            values = [f"#{term}" for term in base_terms[:4]]

        deduped: list[str] = []
        seen: set[str] = set()
        for tag in values:
            if tag not in seen:
                seen.add(tag)
                deduped.append(tag)
        return deduped[:8]

    def _build_trend_context(
        self,
        platform_key: str,
        title: str,
        caption: str,
        hashtags: list[str],
        content_type: str,
        audience: str,
    ) -> dict[str, Any]:
        title_text = f"{title} {caption} {' '.join(hashtags)} {content_type} {audience}".strip()
        virality_seed = self._score_from_text(title_text, {"viral", "trend", "growth", "hook", "save", "share", "watch", "comment"})
        sentiment_seed = self._score_from_text(title_text, {"love", "win", "easy", "better", "fast", "secret", "wow", "proof", "new", "best"})
        return {
            "title": title,
            "platform": platform_key,
            "source_type": f"creator_{platform_key}",
            "subreddit": "n/a",
            "url": "",
            "description": caption or content_type or audience or title,
            "upvotes": 0,
            "comments": 0,
            "trend_score": self._score_from_text(title_text, {"ai", "creator", "content", "video", "post", "hook", "caption", "growth"}),
            "virality_score": virality_seed,
            "compound_score": (sentiment_seed - 50.0) / 100.0,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }

    def _heuristic_analysis(
        self,
        platform_key: str,
        title: str,
        caption: str,
        hashtags: list[str],
        content_type: str,
        audience: str,
        similar_trends: list[dict[str, Any]],
        forecast: dict[str, Any],
    ) -> dict[str, Any]:
        title_text = f"{title} {caption}".strip()
        text_lower = title_text.lower()
        hook_strength = self._hook_strength(title_text)
        emotional_impact = self._emotion_score(title_text)
        readability = self._readability_score(caption or title)
        audience_fit = self._audience_fit(platform_key, audience, content_type, title_text, similar_trends)
        trend_alignment = self._trend_alignment(similar_trends, forecast)
        content_quality = self._content_quality(caption, hashtags, platform_key, content_type)
        saturation_risk = self._saturation_risk(similar_trends, title_text, forecast)
        cta_words = {"save", "comment", "share", "follow", "reply", "join", "try", "watch", "read", "download", "subscribe"}
        keyword_words = {"ai", "secret", "future", "viral", "mistake", "truth", "shocking"}
        cta_presence = 1.0 if any(term in text_lower for term in cta_words) else 0.0
        keyword_bonus = min(8.0, sum(2.0 for term in keyword_words if term in text_lower))
        caption_words = caption.split()
        if caption_words:
            if 18 <= len(caption_words) <= 80:
                content_quality = self._clamp(content_quality + 6.0, 0.0, 100.0)
            elif len(caption_words) < 8:
                content_quality = self._clamp(content_quality - 6.0, 0.0, 100.0)
        if len(hashtags) == 0:
            content_quality = self._clamp(content_quality - 4.0, 0.0, 100.0)
        elif 3 <= len(hashtags) <= 8:
            content_quality = self._clamp(content_quality + 4.0, 0.0, 100.0)
        elif len(hashtags) > 8:
            content_quality = self._clamp(content_quality - 6.0, 0.0, 100.0)
        if cta_presence:
            content_quality = self._clamp(content_quality + 6.0, 0.0, 100.0)

        engagement_probability = self._clamp(
            (hook_strength * 0.20)
            + (audience_fit * 0.20)
            + (trend_alignment * 0.20)
            + (readability * 0.12)
            + (content_quality * 0.18)
            + (emotional_impact * 0.10)
            + (cta_presence * 8.0),
            0.0,
            100.0,
        )
        weighted_base = (
            (hook_strength * 0.20)
            + (audience_fit * 0.18)
            + (trend_alignment * 0.22)
            + (emotional_impact * 0.15)
            + (engagement_probability * 0.15)
            + (readability * 0.10)
        )
        virality_score = weighted_base + keyword_bonus
        if trend_alignment > 80:
            virality_score += 10.0
        if emotional_impact > 75:
            virality_score += 8.0
        if hook_strength > 85:
            virality_score += 12.0
        if saturation_risk > 70:
            virality_score -= 15.0
        if len(caption_words) >= 15 and len(caption_words) <= 120:
            virality_score += 4.0
        elif caption_words and len(caption_words) < 8:
            virality_score -= 6.0
        if not cta_presence:
            virality_score -= 3.0
        virality_score = self._clamp(virality_score, 0.0, 100.0)
        opportunity_score = self._clamp(
            (trend_alignment * 0.30)
            + (audience_fit * 0.24)
            + (engagement_probability * 0.18)
            + (hook_strength * 0.10)
            + (emotional_impact * 0.08)
            + (content_quality * 0.10),
            0.0,
            100.0,
        )
        growth_potential = self._clamp((virality_score * 0.56) + (trend_alignment * 0.24) + (opportunity_score * 0.20), 0.0, 100.0)
        virality_label = self._virality_label_from_score(virality_score)
        prediction_label = self._prediction_label(virality_score, trend_alignment, saturation_risk)
        growth_stage = self._growth_stage(prediction_label)
        best_posting_time = self._best_posting_time(platform_key, audience)
        risk_or_opportunity_level = self._risk_or_opportunity_level(opportunity_score, saturation_risk)

        return {
            "virality_score": round(virality_score, 2),
            "virality_label": virality_label,
            "hook_strength": round(hook_strength, 2),
            "audience_fit": round(audience_fit, 2),
            "trend_alignment": round(trend_alignment, 2),
            "emotional_impact": round(emotional_impact, 2),
            "readability": round(readability, 2),
            "content_quality": round(content_quality, 2),
            "opportunity_score": round(opportunity_score, 2),
            "saturation_risk": round(saturation_risk, 2),
            "growth_potential": round(growth_potential, 2),
            "engagement_probability": round(engagement_probability, 2),
            "growth_stage": growth_stage,
            "prediction_label": prediction_label,
            "risk_or_opportunity_level": risk_or_opportunity_level,
            "best_posting_time": best_posting_time,
            "will_trend": virality_score >= 65.0,
        }

    def _platform_intelligence(
        self,
        *,
        platform_key: str,
        title: str,
        caption: str,
        hashtags: list[str],
        content_type: str,
        audience: str,
        heuristic: dict[str, Any],
        forecast: dict[str, Any],
        thumbnail_result: dict[str, Any],
    ) -> dict[str, Any]:
        profile = self._platform_profile(platform_key)
        thumbnail_strength = self._thumbnail_strength(title, caption, thumbnail_result)
        hook_strength = self._safe_number(heuristic.get("hook_strength"))
        emotional_impact = self._safe_number(heuristic.get("emotional_impact"))
        readability = self._safe_number(heuristic.get("readability"))
        audience_fit = self._safe_number(heuristic.get("audience_fit"))
        trend_alignment = self._safe_number(heuristic.get("trend_alignment"))
        content_quality = self._safe_number(heuristic.get("content_quality"))
        opportunity_score = self._safe_number(heuristic.get("opportunity_score"))
        engagement_probability = self._safe_number(heuristic.get("engagement_probability"))
        virality_score = self._safe_number(heuristic.get("virality_score"))
        saturation_risk = self._safe_number(heuristic.get("saturation_risk"))
        forecast_confidence = self._safe_number(forecast.get("forecast_confidence"))
        forecast_signal = self._safe_number(forecast.get("virality_score")) or (virality_score * 0.92)

        ctr_potential = self._clamp(
            (hook_strength * profile["weights"].get("hook_strength", 0.0))
            + (thumbnail_strength * profile["weights"].get("thumbnail_strength", 0.0))
            + (trend_alignment * profile["weights"].get("trend_alignment", 0.0))
            + (opportunity_score * profile["weights"].get("opportunity_score", 0.0))
            + (content_quality * 0.08),
            0.0,
            100.0,
        )
        retention_potential = self._clamp(
            (readability * profile["weights"].get("readability", 0.0))
            + (audience_fit * profile["weights"].get("audience_fit", 0.0))
            + (content_quality * 0.18)
            + (forecast_confidence * 0.12)
            + (thumbnail_strength * 0.05),
            0.0,
            100.0,
        )
        shareability = self._clamp(
            (emotional_impact * profile["weights"].get("emotional_impact", 0.0))
            + (trend_alignment * 0.22)
            + (engagement_probability * 0.16)
            + (opportunity_score * 0.18)
            + (virality_score * 0.10),
            0.0,
            100.0,
        )
        save_probability = self._clamp(
            (audience_fit * 0.24)
            + (readability * 0.18)
            + (content_quality * 0.18)
            + (opportunity_score * 0.16)
            + (forecast_signal * 0.14),
            0.0,
            100.0,
        )
        engagement_fit = self._clamp(
            (engagement_probability * profile["weights"].get("engagement_probability", 0.0))
            + (audience_fit * profile["weights"].get("audience_fit", 0.0))
            + (trend_alignment * profile["weights"].get("trend_alignment", 0.0))
            + (content_quality * 0.10),
            0.0,
            100.0,
        )
        algorithm_match_score = self._clamp(
            (ctr_potential * profile["weights"].get("ctr_potential", 0.0))
            + (retention_potential * profile["weights"].get("retention_potential", 0.0))
            + (shareability * profile["weights"].get("shareability", 0.0))
            + (save_probability * profile["weights"].get("save_probability", 0.0))
            + (engagement_fit * profile["weights"].get("engagement_fit", 0.0))
            - (saturation_risk * 0.06),
            0.0,
            100.0,
        )

        recommendations = self._platform_recommendations(
            platform_key=platform_key,
            profile=profile,
            heuristic=heuristic,
            thumbnail_strength=thumbnail_strength,
            title=title,
            caption=caption,
            audience=audience,
            content_type=content_type,
        )
        comparison = self._platform_comparison(heuristic, thumbnail_strength, title, caption, audience, content_type)

        return {
            "ctr_potential": round(ctr_potential, 2),
            "retention_potential": round(retention_potential, 2),
            "shareability": round(shareability, 2),
            "save_probability": round(save_probability, 2),
            "engagement_fit": round(engagement_fit, 2),
            "algorithm_match_score": round(algorithm_match_score, 2),
            "platform_virality_score": round(self._clamp((virality_score * 0.7) + (algorithm_match_score * 0.3), 0.0, 100.0), 2),
            "platform_engagement_probability": round(self._clamp((engagement_probability * 0.68) + (engagement_fit * 0.18) + (algorithm_match_score * 0.14), 0.0, 100.0), 2),
            "platform_intelligence": {
                "platform": platform_key,
                "platform_label": profile["label"],
                "forecast_focus": profile["forecast_focus"],
                "hook_style": profile["hook_style"],
                "caption_style": profile["caption_style"],
                "content_structure": profile["content_structure"],
                "scores": {
                    "ctr_potential": round(ctr_potential, 2),
                    "retention_potential": round(retention_potential, 2),
                    "shareability": round(shareability, 2),
                    "save_probability": round(save_probability, 2),
                    "engagement_fit": round(engagement_fit, 2),
                    "algorithm_match_score": round(algorithm_match_score, 2),
                    "platform_virality_score": round(self._clamp((virality_score * 0.7) + (algorithm_match_score * 0.3), 0.0, 100.0), 2),
                    "platform_engagement_probability": round(self._clamp((engagement_probability * 0.68) + (engagement_fit * 0.18) + (algorithm_match_score * 0.14), 0.0, 100.0), 2),
                },
                "recommendations": recommendations,
                "comparison": comparison,
                "platform_focus": profile["focus"],
                "comparison_summary": self._comparison_summary(platform_key, comparison),
                "platform_virality_score": round(self._clamp((virality_score * 0.7) + (algorithm_match_score * 0.3), 0.0, 100.0), 2),
                "platform_engagement_probability": round(self._clamp((engagement_probability * 0.68) + (engagement_fit * 0.18) + (algorithm_match_score * 0.14), 0.0, 100.0), 2),
            },
            "platform_recommendations": recommendations,
            "platform_comparison": comparison,
            "platform_forecast_focus": profile["forecast_focus"],
        }

    def _generate_ai_recommendations(
        self,
        platform_key: str,
        title: str,
        caption: str,
        hashtags: list[str],
        content_type: str,
        audience: str,
        forecast: dict[str, Any],
        rag_result: dict[str, Any],
        similar_context: str,
        heuristic: dict[str, Any],
    ) -> dict[str, Any]:
        if self.gemini_service._client is None:
            logger.info("Gemini unavailable for creator intelligence. Using demo recommendations for %s", title)
            return self._demo_recommendations(platform_key, title, caption, hashtags, content_type, audience, forecast, rag_result, heuristic)

        prompt = self._build_prompt(
            platform_key=platform_key,
            title=title,
            caption=caption,
            hashtags=hashtags,
            content_type=content_type,
            audience=audience,
            forecast=forecast,
            rag_result=rag_result,
            similar_context=similar_context,
            heuristic=heuristic,
        )

        try:
            model = self.gemini_service._client.GenerativeModel("gemini-2.5-flash")
            response = model.generate_content(prompt)
            parsed = self._parse_json(getattr(response, "text", ""))
            if parsed:
                return self._normalize_ai_output(parsed, platform_key, title, caption, hashtags, content_type, audience, forecast, rag_result, heuristic)
        except Exception as exc:
            logger.warning("Creator intelligence Gemini analysis failed for %s: %s", title, exc)

        return self._demo_recommendations(platform_key, title, caption, hashtags, content_type, audience, forecast, rag_result, heuristic)

    def _build_prompt(
        self,
        platform_key: str,
        title: str,
        caption: str,
        hashtags: list[str],
        content_type: str,
        audience: str,
        forecast: dict[str, Any],
        rag_result: dict[str, Any],
        similar_context: str,
        heuristic: dict[str, Any],
    ) -> str:
        return (
            "You are a senior AI creator strategist. Help the user optimize a social post for reach, virality, and clarity. "
            "Return ONLY valid JSON with these keys: summary, improved_hook, improved_caption, better_cta, optimized_hashtags, thumbnail_text_ideas, posting_strategy, best_posting_time, growth_strategy, platform_optimization_tips, why_it_may_trend, why_it_may_fail, audience_that_may_engage, reach_improvement, audience_persona, competitor_post_comparison, content_calendar_idea.\n"
            f"Platform: {self.SUPPORTED_PLATFORMS.get(platform_key, platform_key)}\n"
            f"Content type: {content_type or 'Post'}\n"
            f"Target audience: {audience or 'General audience'}\n"
            f"Title or post idea: {title}\n"
            f"Caption: {caption or 'No caption provided.'}\n"
            f"Hashtags: {json.dumps(hashtags, ensure_ascii=False)}\n"
            f"Heuristic scores: {json.dumps(heuristic, ensure_ascii=False)}\n"
            f"Forecast context: {json.dumps(forecast, ensure_ascii=False)}\n"
            f"RAG context: {json.dumps(rag_result.get('rag_analysis', {}), ensure_ascii=False)}\n"
            f"Similar trend context:\n{similar_context}\n"
            "Make the answer concise, practical, platform-aware, and suitable for a production dashboard."
        )

    def _normalize_ai_output(
        self,
        data: dict[str, Any],
        platform_key: str,
        title: str,
        caption: str,
        hashtags: list[str],
        content_type: str,
        audience: str,
        forecast: dict[str, Any],
        rag_result: dict[str, Any],
        heuristic: dict[str, Any],
    ) -> dict[str, Any]:
        optimized_hashtags = self._coerce_list(data.get("optimized_hashtags"))
        if not optimized_hashtags:
            optimized_hashtags = self._build_hashtag_suggestions(title, platform_key, hashtags)

        thumbnail_text_ideas = self._coerce_list(data.get("thumbnail_text_ideas"))
        if not thumbnail_text_ideas:
            thumbnail_text_ideas = self._thumbnail_text_ideas(title, platform_key, content_type)

        platform_tips = self._coerce_list(data.get("platform_optimization_tips"))
        if not platform_tips:
            platform_tips = self._platform_tips(platform_key, content_type, audience)

        reach_improvement = self._coerce_list(data.get("reach_improvement"))
        if not reach_improvement:
            reach_improvement = self._reach_improvement(platform_key, title, content_type, audience)

        return {
            "summary": str(data.get("summary", "")).strip()
            or f"{title} can be optimized into a creator-first post with a stronger hook and sharper audience fit.",
            "improved_hook": str(data.get("improved_hook", "")).strip() or self._improved_hook(title, platform_key, audience),
            "improved_caption": str(data.get("improved_caption", "")).strip() or self._improved_caption(title, caption, hashtags, audience, content_type),
            "better_cta": str(data.get("better_cta", "")).strip() or self._better_cta(platform_key, audience),
            "optimized_hashtags": optimized_hashtags,
            "thumbnail_text_ideas": thumbnail_text_ideas,
            "posting_strategy": str(data.get("posting_strategy", "")).strip() or self._posting_strategy(platform_key, content_type, audience),
            "best_posting_time": str(data.get("best_posting_time", "")).strip() or heuristic["best_posting_time"],
            "growth_strategy": str(data.get("growth_strategy", "")).strip()
            or "Lead with a strong hook, keep the content useful, and make the payoff visible in the first few seconds.",
            "platform_optimization_tips": platform_tips,
            "why_it_may_trend": str(data.get("why_it_may_trend", "")).strip() or self._why_it_may_trend(title, forecast, rag_result),
            "why_it_may_fail": str(data.get("why_it_may_fail", "")).strip() or self._why_it_may_fail(title, heuristic),
            "audience_that_may_engage": str(data.get("audience_that_may_engage", "")).strip()
            or audience
            or "Creators, early adopters, and niche audience segments.",
            "reach_improvement": reach_improvement,
            "audience_persona": str(data.get("audience_persona", "")).strip() or self._audience_persona(platform_key, audience, content_type),
            "competitor_post_comparison": str(data.get("competitor_post_comparison", "")).strip()
            or "This concept should outperform generic posts if it leads with a sharper hook, proof, and a clear audience promise.",
            "content_calendar_idea": str(data.get("content_calendar_idea", "")).strip()
            or "Turn this into a 3-part sequence: hook, proof, and implementation follow-up.",
        }

    def _demo_recommendations(
        self,
        platform_key: str,
        title: str,
        caption: str,
        hashtags: list[str],
        content_type: str,
        audience: str,
        forecast: dict[str, Any],
        rag_result: dict[str, Any],
        heuristic: dict[str, Any],
    ) -> dict[str, Any]:
        platform_label = self.SUPPORTED_PLATFORMS.get(platform_key, platform_key.title())
        optimized_hashtags = self._build_hashtag_suggestions(title, platform_key, hashtags)
        return {
            "summary": f"{title} can be turned into a stronger {platform_label} post by sharpening the hook, adding proof, and matching audience intent.",
            "improved_hook": self._improved_hook(title, platform_key, audience),
            "improved_caption": self._improved_caption(title, caption, optimized_hashtags, audience, content_type),
            "better_cta": self._better_cta(platform_key, audience),
            "optimized_hashtags": optimized_hashtags,
            "thumbnail_text_ideas": self._thumbnail_text_ideas(title, platform_key, content_type),
            "posting_strategy": self._posting_strategy(platform_key, content_type, audience),
            "best_posting_time": heuristic["best_posting_time"],
            "growth_strategy": "Pair the post with a clear promise, a fast payoff, and a strong next step for the audience.",
            "platform_optimization_tips": self._platform_tips(platform_key, content_type, audience),
            "why_it_may_trend": self._why_it_may_trend(title, forecast, rag_result),
            "why_it_may_fail": self._why_it_may_fail(title, heuristic),
            "audience_that_may_engage": audience or "Creators, early adopters, and niche audience segments.",
            "reach_improvement": self._reach_improvement(platform_key, title, content_type, audience),
            "audience_persona": self._audience_persona(platform_key, audience, content_type),
            "competitor_post_comparison": "Use a clearer proof point and a more specific audience promise than generic competitor posts.",
            "content_calendar_idea": "Turn the same idea into a hook clip, a deeper breakdown, and a follow-up Q&A post.",
        }

    def _improved_hook(self, title: str, platform_key: str, audience: str) -> str:
        platform_label = self.SUPPORTED_PLATFORMS.get(platform_key, platform_key.title())
        if platform_key == "linkedin":
            return f"How {title} creates a smarter advantage for {audience or 'professionals'}"
        if platform_key == "reddit":
            return f"Why {title} matters right now and what the community is missing"
        if platform_key == "youtube":
            return f"{title}: the real story and the biggest takeaway"
        if platform_key == "twitter":
            return f"The fastest way to turn {title} into content people share"
        return f"Stop scrolling: here is how to turn {title} into a high-performing {platform_label} post"

    def _improved_caption(self, title: str, caption: str, hashtags: list[str], audience: str, content_type: str) -> str:
        caption_core = caption or f"Here is a creator-first breakdown of {title}."
        audience_line = f"Built for {audience}." if audience else "Built for people who want practical content strategy."
        cta = "Save this and use the framework in your next post."
        return " ".join(
            part
            for part in [caption_core.strip(), audience_line, cta, " ".join(hashtags[:5])]
            if part
        )

    def _better_cta(self, platform_key: str, audience: str) -> str:
        if platform_key == "linkedin":
            return f"Comment with your take or share this with a teammate who owns {audience or 'content strategy'}."
        if platform_key == "youtube":
            return "Subscribe for more practical breakdowns and post the next idea in the comments."
        if platform_key == "reddit":
            return "Share your real workflow in the comments and compare notes with the community."
        if platform_key == "twitter":
            return "Reply with your version and bookmark this for later."
        return "Save this, share it, and try the strategy on your next post."

    def _thumbnail_text_ideas(self, title: str, platform_key: str, content_type: str) -> list[str]:
        base = title[:48].strip()
        platform_hint = self.SUPPORTED_PLATFORMS.get(platform_key, platform_key.title())
        return [
            f"{base} in 10 seconds",
            f"Why {base} works",
            f"{platform_hint} growth shortcut",
        ]

    def _posting_strategy(self, platform_key: str, content_type: str, audience: str) -> str:
        platform_label = self.SUPPORTED_PLATFORMS.get(platform_key, platform_key.title())
        return (
            f"Open with a direct promise, deliver one useful insight fast, and close with a clear next step. "
            f"Adapt the pacing for {platform_label} and keep the message aligned to {audience or 'your audience'}."
        )

    def _platform_tips(self, platform_key: str, content_type: str, audience: str) -> list[str]:
        mapping = {
            "instagram": [
                "Lead with a fast hook in the first 2 seconds.",
                "Keep the caption tight and skimmable.",
                "Use 3-5 focused hashtags with strong topic relevance.",
            ],
            "youtube": [
                "Optimize the title for curiosity and clarity.",
                "Use thumbnail text that promises a payoff.",
                "Front-load the value so retention stays high.",
            ],
            "linkedin": [
                "Position the post as practical authority.",
                "Use professional tone with a clear business takeaway.",
                "Break the idea into a clean, readable structure.",
            ],
            "twitter": [
                "Write one concise idea per post or thread entry.",
                "Use a sharp first line that invites a reply.",
                "Keep the structure easy to skim and share.",
            ],
            "reddit": [
                "Sound authentic and avoid marketing-heavy language.",
                "Match the subreddit culture and expectations.",
                "Frame the post as a real discussion or useful breakdown.",
            ],
            "tiktok": [
                "Make the opening visual and immediate.",
                "Keep the pace high and the message simple.",
                "Use a clear payoff in the first half of the video.",
            ],
            "facebook": [
                "Make the idea easy to understand at a glance.",
                "Use a friendly tone with a clear call to action.",
                "Keep the post shareable and discussion-friendly.",
            ],
        }
        return mapping.get(platform_key, [
            f"Keep the post aligned with {audience or 'your audience'}.",
            f"Focus the idea around the content type: {content_type or 'post'}.",
            "Make the hook and payoff visible quickly.",
        ])

    def _reach_improvement(self, platform_key: str, title: str, content_type: str, audience: str) -> list[str]:
        return [
            f"Frame the first line around the promise in {title}.",
            f"Reinforce the value for {audience or 'your audience'} within the first 3 lines or first 3 seconds.",
            f"Turn the same idea into a follow-up {content_type or 'post'} for retention and repostability.",
        ]

    def _audience_persona(self, platform_key: str, audience: str, content_type: str) -> str:
        platform_label = self.SUPPORTED_PLATFORMS.get(platform_key, platform_key.title())
        return (
            f"A {platform_label} audience interested in {audience or 'practical creator growth'}, "
            f"looking for a {content_type or 'post'} that is easy to save, share, and apply."
        )

    def _platform_profile(self, platform_key: str) -> dict[str, Any]:
        profiles = {
            "linkedin": {
                "label": "LinkedIn",
                "focus": ["educational value", "professional tone", "saves/comments", "storytelling", "career relevance"],
                "forecast_focus": "impressions + saves",
                "hook_style": "Lead with a practical lesson or outcome.",
                "caption_style": "Use short paragraphs, proof, and one clear takeaway.",
                "content_structure": "Story -> lesson -> proof -> takeaway",
                "weights": {
                    "hook_strength": 0.18,
                    "thumbnail_strength": 0.04,
                    "trend_alignment": 0.13,
                    "audience_fit": 0.20,
                    "engagement_probability": 0.18,
                    "retention_potential": 0.12,
                    "shareability": 0.10,
                    "save_probability": 0.15,
                    "ctr_potential": 0.06,
                    "emotion": 0.10,
                    "opportunity_score": 0.10,
                    "readability": 0.10,
                },
            },
            "youtube": {
                "label": "YouTube",
                "focus": ["hook strength", "CTR potential", "watch-time potential", "curiosity", "thumbnail strength"],
                "forecast_focus": "views + retention",
                "hook_style": "Promise a clear payoff in the first few seconds.",
                "caption_style": "Use curiosity, clarity, and searchable phrasing.",
                "content_structure": "Hook -> payoff -> walkthrough -> recap",
                "weights": {
                    "hook_strength": 0.28,
                    "thumbnail_strength": 0.18,
                    "trend_alignment": 0.16,
                    "audience_fit": 0.12,
                    "engagement_probability": 0.14,
                    "retention_potential": 0.18,
                    "shareability": 0.06,
                    "save_probability": 0.04,
                    "ctr_potential": 0.24,
                    "opportunity_score": 0.14,
                    "readability": 0.08,
                },
            },
            "instagram": {
                "label": "Instagram",
                "focus": ["emotional impact", "short-form readability", "visual engagement", "shareability", "reel-style structure"],
                "forecast_focus": "shares + reel reach",
                "hook_style": "Lead with a visual or emotional angle.",
                "caption_style": "Keep it tight, scannable, and easy to save/share.",
                "content_structure": "Visual hook -> quick value -> simple CTA",
                "weights": {
                    "hook_strength": 0.16,
                    "thumbnail_strength": 0.14,
                    "trend_alignment": 0.14,
                    "audience_fit": 0.12,
                    "engagement_probability": 0.16,
                    "retention_potential": 0.10,
                    "shareability": 0.24,
                    "save_probability": 0.10,
                    "ctr_potential": 0.08,
                    "emotional_impact": 0.18,
                    "opportunity_score": 0.12,
                    "readability": 0.12,
                },
            },
            "twitter": {
                "label": "Twitter/X",
                "focus": ["short hook", "controversial/opinion style", "fast engagement", "concise writing"],
                "forecast_focus": "replies + repost velocity",
                "hook_style": "Lead with a punchy opinion or short insight.",
                "caption_style": "Keep one sharp idea per post or thread entry.",
                "content_structure": "Hook -> opinion -> proof -> reply bait",
                "weights": {
                    "hook_strength": 0.24,
                    "thumbnail_strength": 0.02,
                    "trend_alignment": 0.14,
                    "audience_fit": 0.14,
                    "engagement_probability": 0.22,
                    "retention_potential": 0.08,
                    "shareability": 0.14,
                    "save_probability": 0.08,
                    "ctr_potential": 0.08,
                    "emotional_impact": 0.16,
                    "opportunity_score": 0.10,
                    "readability": 0.18,
                },
            },
        }
        return profiles.get(platform_key, profiles["linkedin"])

    def _platform_recommendations(
        self,
        *,
        platform_key: str,
        profile: dict[str, Any],
        heuristic: dict[str, Any],
        thumbnail_strength: float,
        title: str,
        caption: str,
        audience: str,
        content_type: str,
    ) -> list[str]:
        recommendations: list[str] = []
        hook_strength = self._safe_number(heuristic.get("hook_strength"))
        emotional_impact = self._safe_number(heuristic.get("emotional_impact"))
        readability = self._safe_number(heuristic.get("readability"))
        shareability = self._safe_number(heuristic.get("shareability", heuristic.get("opportunity_score")))
        save_probability = self._safe_number(heuristic.get("save_probability", heuristic.get("audience_fit")))
        engagement_fit = self._safe_number(heuristic.get("engagement_fit", heuristic.get("engagement_probability")))
        algorithm_match_score = self._safe_number(heuristic.get("algorithm_match_score", 0))
        caption_length = len((caption or "").split())

        if platform_key == "youtube":
            recommendations.append("Strengthen the first 3 seconds to raise CTR and retention.")
            if thumbnail_strength < 65:
                recommendations.append("Improve the thumbnail promise with clearer contrast and a stronger visual hook.")
            if hook_strength < 70:
                recommendations.append("Your hook is weak for YouTube CTR.")
            recommendations.append("Use curiosity in the title and make the payoff obvious early.")
        elif platform_key == "linkedin":
            recommendations.append("Educational storytelling performs better on LinkedIn.")
            if save_probability < 65:
                recommendations.append("Add one practical takeaway people can save for later.")
            if engagement_fit < 65:
                recommendations.append("Add a short business lesson, proof point, or personal insight.")
            recommendations.append("Use a professional tone with a clear career or business relevance.")
        elif platform_key == "instagram":
            if caption_length > 70:
                recommendations.append("Caption length is too long for Instagram engagement.")
            recommendations.append("Keep the post visually strong and easy to share in under 10 seconds.")
            if emotional_impact < 60:
                recommendations.append("Add a more emotional or visually clear opening.")
            recommendations.append("Shorten the caption and use a reel-style structure.")
        elif platform_key == "twitter":
            recommendations.append("Keep it short, opinionated, and easy to reply to.")
            if readability < 65:
                recommendations.append("Make the hook more concise so it lands faster.")
            if shareability < 60:
                recommendations.append("Use a sharper point of view or debate angle.")
            recommendations.append("Write one clear idea per post and invite fast engagement.")
        else:
            recommendations.extend(profile.get("focus", []))

        if algorithm_match_score < 55:
            recommendations.append(f"Your current {self.SUPPORTED_PLATFORMS.get(platform_key, platform_key.title())} match is still early. Tighten the hook and format.")
        if audience:
            recommendations.append(f"Keep the message centered on {audience}.")
        return self._dedupe_strings(recommendations)[:6]

    def _platform_comparison(
        self,
        heuristic: dict[str, Any],
        thumbnail_strength: float,
        title: str,
        caption: str,
        audience: str,
        content_type: str,
    ) -> list[dict[str, Any]]:
        platforms = ["linkedin", "youtube", "instagram", "twitter"]
        comparison: list[dict[str, Any]] = []
        for key in platforms:
            profile = self._platform_profile(key)
            score = self._platform_match_score(
                key,
                heuristic,
                thumbnail_strength=thumbnail_strength,
                title=title,
                caption=caption,
                audience=audience,
                content_type=content_type,
            )
            comparison.append(
                {
                    "platform": key,
                    "platform_label": profile["label"],
                    "score": round(score, 2),
                    "focus": profile["forecast_focus"],
                }
            )
        comparison.sort(key=lambda item: item["score"], reverse=True)
        return comparison

    def _comparison_summary(self, platform_key: str, comparison: list[dict[str, Any]]) -> str:
        if not comparison:
            return "No cross-platform comparison available."
        current = next((item for item in comparison if item.get("platform") == platform_key), comparison[0])
        top = comparison[0]
        if current.get("platform") == top.get("platform"):
            return f"{top['platform_label']} is the strongest fit at {top['score']:.0f}."
        return f"{top['platform_label']} is currently the strongest fit at {top['score']:.0f}, while {self.SUPPORTED_PLATFORMS.get(platform_key, platform_key.title())} scores {current.get('score', 0):.0f}."

    def _platform_match_score(
        self,
        platform_key: str,
        heuristic: dict[str, Any],
        *,
        thumbnail_strength: float,
        title: str,
        caption: str,
        audience: str,
        content_type: str,
    ) -> float:
        profile = self._platform_profile(platform_key)
        hook_strength = self._safe_number(heuristic.get("hook_strength"))
        emotional_impact = self._safe_number(heuristic.get("emotional_impact"))
        readability = self._safe_number(heuristic.get("readability"))
        audience_fit = self._safe_number(heuristic.get("audience_fit"))
        trend_alignment = self._safe_number(heuristic.get("trend_alignment"))
        content_quality = self._safe_number(heuristic.get("content_quality"))
        opportunity_score = self._safe_number(heuristic.get("opportunity_score"))
        engagement_probability = self._safe_number(heuristic.get("engagement_probability"))
        saturation_risk = self._safe_number(heuristic.get("saturation_risk"))

        score = (
            hook_strength * profile["weights"].get("hook_strength", 0.1)
            + thumbnail_strength * profile["weights"].get("thumbnail_strength", 0.0)
            + trend_alignment * profile["weights"].get("trend_alignment", 0.1)
            + audience_fit * profile["weights"].get("audience_fit", 0.1)
            + engagement_probability * profile["weights"].get("engagement_probability", 0.1)
            + content_quality * 0.12
            + opportunity_score * profile["weights"].get("opportunity_score", 0.1)
            + readability * profile["weights"].get("readability", 0.1)
            + emotional_impact * profile["weights"].get("emotional_impact", 0.1)
            - saturation_risk * 0.05
        )
        if platform_key == "youtube":
            score += min(10.0, thumbnail_strength * 0.08)
        if platform_key == "linkedin":
            score += 4.0 if audience and any(term in audience.lower() for term in ["founder", "professional", "student", "creator"]) else 0.0
        if platform_key == "instagram":
            score += 4.0 if len(caption.split()) <= 70 else -4.0
        if platform_key == "twitter":
            score += 4.0 if len(title.split()) <= 14 else -3.0
        return self._clamp(score, 0.0, 100.0)

    def _thumbnail_strength(self, title: str, caption: str, thumbnail_result: dict[str, Any]) -> float:
        if thumbnail_result:
            score = self._safe_number(thumbnail_result.get("thumbnail_score"))
            if score > 0:
                return self._clamp(score, 0.0, 100.0)
        text = f"{title} {caption}".lower()
        score = 45.0
        if any(term in text for term in ["ai", "ml", "python", "fastapi", "project", "tutorial", "how to"]):
            score += 12.0
        if len(text.split()) <= 20:
            score += 8.0
        if "dashboard" in text or "demo" in text:
            score += 6.0
        return self._clamp(score, 0.0, 100.0)

    def _why_it_may_trend(self, title: str, forecast: dict[str, Any], rag_result: dict[str, Any]) -> str:
        forecast_summary = forecast.get("forecast_explanation") or forecast.get("why_the_trend_may_grow") or ""
        rag_summary = rag_result.get("rag_analysis", {}).get("historical_comparison") or rag_result.get("rag_analysis", {}).get("summary") or ""
        if forecast_summary or rag_summary:
            return f"{forecast_summary} {rag_summary}".strip()
        return f"{title} has enough utility and creator relevance to gain traction if packaged clearly."

    def _why_it_may_fail(self, title: str, heuristic: dict[str, Any]) -> str:
        risk = self._safe_number(heuristic.get("saturation_risk"))
        if risk >= 60:
            return f"{title} could underperform if it feels too generic, too long, or too similar to existing content."
        return "It may stall if the hook is vague, the audience promise is unclear, or the post lacks a strong payoff."

    def _virality_label_from_score(self, virality_score: float) -> str:
        if virality_score >= 85:
            return "High Viral"
        if virality_score >= 65:
            return "Trending"
        if virality_score >= 45:
            return "Average"
        return "Low Reach"

    def _hook_strength(self, text: str) -> float:
        score = 30.0
        words = self._keywords(text)
        trigger_terms = {"how", "why", "secret", "mistake", "save", "grow", "fast", "easy", "better", "proof", "viral", "hack", "guide"}
        score += sum(5.0 for term in trigger_terms if term in text.lower())
        if 4 <= len(words) <= 12:
            score += 12.0
        if any(char.isdigit() for char in text):
            score += 4.0
        return self._clamp(score, 0.0, 100.0)

    def _emotion_score(self, text: str) -> float:
        score = 28.0
        emotional_terms = {"wow", "secret", "mistake", "save", "win", "fast", "new", "best", "proof", "breakthrough", "growth", "impact", "change"}
        score += sum(4.5 for term in emotional_terms if term in text.lower())
        return self._clamp(score, 0.0, 100.0)

    def _readability_score(self, text: str) -> float:
        words = [word for word in re.findall(r"[A-Za-z0-9]+", text) if word]
        if not words:
            return 50.0
        avg_length = sum(len(word) for word in words) / len(words)
        score = 100.0 - max(0.0, (len(words) - 20) * 1.2) - max(0.0, avg_length - 6.0) * 8.0
        return self._clamp(score, 0.0, 100.0)

    def _audience_fit(self, platform_key: str, audience: str, content_type: str, text: str, similar_trends: list[dict[str, Any]]) -> float:
        score = 42.0
        text_lower = text.lower()
        audience_lower = audience.lower()
        content_lower = content_type.lower()
        platform_bonus = {
            "instagram": 10.0,
            "youtube": 12.0,
            "linkedin": 11.0,
            "twitter": 9.0,
            "reddit": 10.0,
            "tiktok": 12.0,
            "facebook": 8.0,
        }.get(platform_key, 8.0)
        score += platform_bonus
        if audience_lower:
            score += 8.0 if any(token in text_lower for token in self._keywords(audience_lower)) else 0.0
        if "reel" in content_lower or "short" in content_lower:
            score += 6.0
        if similar_trends:
            score += min(15.0, len(similar_trends) * 2.5)
        return self._clamp(score, 0.0, 100.0)

    def _trend_alignment(self, similar_trends: list[dict[str, Any]], forecast: dict[str, Any]) -> float:
        similarity_average = 0.0
        if similar_trends:
            similarity_average = sum(self._safe_number(item.get("similarity_score")) for item in similar_trends) / len(similar_trends)
        forecast_probability = self._safe_number(forecast.get("virality_probability"))
        if forecast_probability <= 1.0:
            forecast_probability *= 100.0
        score = (similarity_average * 0.35) + (forecast_probability * 0.65)
        return self._clamp(score, 0.0, 100.0)

    def _content_quality(self, caption: str, hashtags: list[str], platform_key: str, content_type: str) -> float:
        score = 35.0
        caption_words = [word for word in re.findall(r"[A-Za-z0-9]+", caption or "") if word]
        caption_length = len(caption_words)
        cta_terms = {"save", "comment", "share", "follow", "reply", "join", "try", "watch", "read", "download", "subscribe"}
        has_cta = any(term in (caption or "").lower() for term in cta_terms)

        if caption:
          score += 8.0
        if 18 <= caption_length <= 80:
            score += 12.0
        elif 8 <= caption_length < 18:
            score += 6.0
        elif caption_length > 120:
            score -= 6.0
        if 3 <= len(hashtags) <= 8:
            score += 12.0
        elif len(hashtags) in {1, 2}:
            score += 4.0
        elif len(hashtags) > 8:
            score -= 8.0
        if has_cta:
            score += 8.0
        if "?" in caption or "!" in caption:
            score += 4.0
        if platform_key == "linkedin" and len(caption.split()) > 40:
            score += 4.0
        if platform_key == "youtube" and len(caption_words) >= 12:
            score += 4.0
        if content_type:
            score += 4.0
        return self._clamp(score, 0.0, 100.0)

    def _saturation_risk(self, similar_trends: list[dict[str, Any]], text: str, forecast: dict[str, Any]) -> float:
        similarity_average = 0.0
        if similar_trends:
            similarity_average = sum(self._safe_number(item.get("similarity_score")) for item in similar_trends) / len(similar_trends)
        forecast_risk = self._safe_number(forecast.get("risk_score"))
        score = (similarity_average * 0.35) + (forecast_risk * 0.65)
        if len(self._keywords(text)) < 4:
            score += 8.0
        return self._clamp(score, 0.0, 100.0)

    def _prediction_label(self, virality_score: float, trend_alignment: float, saturation_risk: float) -> str:
        if virality_score >= 82 and trend_alignment >= 70:
            return "EXPLODING"
        if virality_score >= 66:
            return "GROWING"
        if virality_score >= 45:
            return "STABLE"
        if saturation_risk >= 65:
            return "DECLINING"
        return "SATURATED"

    def _growth_stage(self, prediction_label: str) -> str:
        mapping = {
            "EXPLODING": "accelerating",
            "GROWING": "growing",
            "STABLE": "steady",
            "DECLINING": "cooling",
            "SATURATED": "saturated",
        }
        return mapping.get(prediction_label, "growing")

    def _risk_or_opportunity_level(self, opportunity_score: float, saturation_risk: float) -> str:
        if opportunity_score >= 75 and saturation_risk < 45:
            return "High Opportunity"
        if saturation_risk >= 65:
            return "Caution"
        return "Balanced"

    def _best_posting_time(self, platform_key: str, audience: str) -> str:
        mapping = {
            "instagram": "6:00 PM - 9:00 PM local time",
            "youtube": "12:00 PM - 3:00 PM local time",
            "linkedin": "8:00 AM - 11:00 AM local time",
            "twitter": "9:00 AM - 11:00 AM local time or during live events",
            "reddit": "6:00 PM - 9:00 PM local time for active subreddit discussion",
            "tiktok": "7:00 PM - 10:00 PM local time",
            "facebook": "1:00 PM - 3:00 PM local time",
        }
        return mapping.get(platform_key, "Late afternoon or early evening local time")

    def _build_hashtag_suggestions(self, title: str, platform_key: str, hashtags: list[str]) -> list[str]:
        base_terms = self._keywords(title)
        tags = list(hashtags)
        for term in list(base_terms)[:4]:
            candidate = f"#{term}"
            if candidate not in tags:
                tags.append(candidate)
        platform_tag = {
            "instagram": "#instagramreels",
            "youtube": "#youtubeshorts",
            "linkedin": "#linkedin",
            "twitter": "#twitterx",
            "reddit": "#reddit",
            "tiktok": "#tiktok",
            "facebook": "#facebook",
        }.get(platform_key)
        if platform_tag and platform_tag not in tags:
            tags.append(platform_tag)
        if "#creator" not in tags:
            tags.append("#creator")
        return tags[:8]

    def _coerce_list(self, value: Any) -> list[str]:
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str):
            items = [item.strip() for item in re.split(r"[\n,]+", value) if item.strip()]
            return items
        return []

    def _dedupe_strings(self, values: list[str]) -> list[str]:
        deduped: list[str] = []
        seen: set[str] = set()
        for value in values:
            text = str(value).strip()
            if not text or text.lower() in seen:
                continue
            seen.add(text.lower())
            deduped.append(text)
        return deduped

    def _score_from_text(self, text: str, keywords: set[str]) -> float:
        lowered = text.lower()
        score = 35.0
        score += sum(4.0 for keyword in keywords if keyword in lowered)
        return self._clamp(score, 0.0, 100.0)

    def _safe_number(self, value: Any) -> float:
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0

    def _clamp(self, value: float, minimum: float, maximum: float) -> float:
        return max(minimum, min(maximum, value))

    def _keywords(self, text: str) -> set[str]:
        return {
            token.strip(".,!?;:\"'()[]{}").lower()
            for token in text.split()
            if len(token.strip(".,!?;:\"'()[]{}")) > 2
        }

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
