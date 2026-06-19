"""Creator strategy agent for short, actionable content planning."""

from __future__ import annotations

import json
import logging
import os
import re
from collections import Counter
from typing import Any

from backend.config import settings
from backend.services.gemini_service import GeminiService
from backend.services.insight_tools import InsightTools

logger = logging.getLogger(__name__)


class CreatorStrategyService:
    def __init__(self) -> None:
        self.gemini_service = GeminiService()
        self.insight_tools = InsightTools()
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "").strip()
        self._openai_client = self._load_openai_client() if self.openai_api_key else None
        self._gemini_unavailable = False
        self.gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    def generate_strategy(self, payload: dict[str, Any]) -> dict[str, Any]:
        normalized = self._normalize_payload(payload or {})
        analysis = normalized["analysis"]
        competitor = normalized["competitor_analysis"]
        trends = normalized["trends"]
        region = normalized["region"]
        current_request = analysis.get("current_request", {}) if isinstance(analysis, dict) else {}

        logger.info(
            "Strategy request received: has_analysis=%s trends=%s competitor=%s audience=%s platform=%s",
            bool(analysis),
            len(trends),
            bool(competitor),
            normalized["audience"],
            normalized["platform"],
        )

        if self.gemini_service._client is not None and not self._gemini_unavailable:
            try:
                return self._from_ai(
                    provider="gemini",
                    prompt=self._build_prompt(normalized),
                    normalized=normalized,
                )
            except Exception as exc:
                logger.warning("Gemini strategy generation failed: %s", exc)
                self._gemini_unavailable = True

        if self._openai_client is not None:
            try:
                return self._from_openai(normalized)
            except Exception as exc:
                logger.warning("OpenAI strategy generation failed: %s", exc)

        return self._rule_based_strategy(normalized)

    def _normalize_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        analysis = payload.get("analysis_result") or payload.get("latest_analysis_result") or payload.get("analysis") or {}
        if not isinstance(analysis, dict):
            analysis = {}

        current_request = analysis.get("current_request", {}) if isinstance(analysis.get("current_request"), dict) else {}
        competitor = payload.get("competitor_analysis") or analysis.get("competitor_analysis") or {}
        if not isinstance(competitor, dict):
            competitor = {}

        trends_value = payload.get("trends") or analysis.get("similar_trends") or analysis.get("trend_keywords") or []
        trends = trends_value if isinstance(trends_value, list) else []
        region = str(payload.get("trend_region") or payload.get("region") or analysis.get("region") or analysis.get("current_request", {}).get("region") or "Global").strip() or "Global"

        title = str(payload.get("title") or current_request.get("title") or analysis.get("title") or "").strip()
        caption = str(payload.get("caption") or current_request.get("caption") or analysis.get("caption") or "").strip()
        audience = str(payload.get("audience") or current_request.get("audience") or analysis.get("audience") or "").strip()
        platform = str(payload.get("platform") or current_request.get("platform") or analysis.get("platform") or "LinkedIn").strip() or "LinkedIn"
        content_type = str(payload.get("content_type") or current_request.get("content_type") or analysis.get("content_type") or "").strip()
        hashtags = self._normalize_hashtags(
            payload.get("hashtags")
            or current_request.get("hashtags")
            or analysis.get("hashtags")
            or analysis.get("normalized_hashtags")
            or []
        )
        thumbnail = payload.get("thumbnail_result") or payload.get("thumbnail_analysis") or analysis.get("thumbnail_result") or analysis.get("thumbnail_analysis") or {}
        if not isinstance(thumbnail, dict):
            thumbnail = {}

        content_text = " ".join(
            part
            for part in [
                title,
                caption,
                audience,
                content_type,
                " ".join(hashtags),
                competitor.get("competitor", ""),
                competitor.get("topic", ""),
            ]
            if part
        ).strip()
        trend_match = self.insight_tools.compare_keywords(content_text=content_text, trends=trends if trends and isinstance(trends[0], dict) else [])

        return {
            "analysis": analysis,
            "competitor_analysis": competitor,
            "trends": trends,
            "trend_match_score": trend_match.get("trend_match_score", 0.0),
            "matched_keywords": trend_match.get("matched_keywords", []),
            "content_keywords": trend_match.get("content_keywords", []),
            "trend_keywords": trend_match.get("trend_keywords", []),
            "title": title,
            "caption": caption,
            "audience": audience or "General audience",
            "platform": platform,
            "content_type": content_type or "Post",
            "hashtags": hashtags,
            "thumbnail": thumbnail,
            "region": region,
        }

    def _build_prompt(self, normalized: dict[str, Any]) -> str:
        analysis = normalized["analysis"]
        competitor = normalized["competitor_analysis"]
        trend_keywords = normalized["trend_keywords"]
        trend_match_score = normalized["trend_match_score"]
        return (
            "You are a creator strategy AI agent. Return ONLY valid JSON with these keys: summary, what_to_post_next, best_content_category, best_posting_time, best_content_tone, recommended_hashtags, audience_insights, strategy_cards, recommendation_bullets, growth_insights, trend_match_takeaway, competitor_takeaway.\n"
            "Keep every answer short, specific, and actionable for creators.\n"
            f"Title: {normalized['title']}\n"
            f"Caption: {normalized['caption']}\n"
            f"Audience: {normalized['audience']}\n"
            f"Platform: {normalized['platform']}\n"
            f"Region: {normalized['region']}\n"
            f"Content type: {normalized['content_type']}\n"
            f"Virality score: {analysis.get('virality_score', 0)}\n"
            f"Engagement probability: {analysis.get('engagement_probability', 0)}\n"
            f"Trend match score: {trend_match_score}\n"
            f"Competitor analysis: {json.dumps(competitor, ensure_ascii=False)}\n"
            f"Trending keywords: {json.dumps(trend_keywords, ensure_ascii=False)}\n"
            f"Current hashtags: {json.dumps(normalized['hashtags'], ensure_ascii=False)}\n"
            f"Current analysis: {json.dumps(analysis, ensure_ascii=False)}\n"
            "Prioritize creator growth, consistency, and clear next steps."
        )

    def _from_ai(self, provider: str, prompt: str, normalized: dict[str, Any]) -> dict[str, Any]:
        response_text = ""
        if provider == "gemini" and self.gemini_service._client is not None:
            model = self.gemini_service._client.GenerativeModel(self.gemini_model)
            response = model.generate_content(prompt)
            response_text = getattr(response, "text", "") or ""
        elif provider == "openai" and self._openai_client is not None:
            response = self._openai_client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                messages=[
                    {"role": "system", "content": "You are a creator strategy AI agent that returns only valid JSON."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.4,
            )
            response_text = response.choices[0].message.content or ""

        parsed = self._parse_json(response_text)
        if not parsed:
            if provider == "gemini":
                self._gemini_unavailable = True
            raise ValueError("AI strategy response was not valid JSON.")
        return self._normalize_output(parsed, normalized, source=provider)

    def _from_openai(self, normalized: dict[str, Any]) -> dict[str, Any]:
        prompt = self._build_prompt(normalized)
        return self._from_ai("openai", prompt, normalized)

    def _rule_based_strategy(self, normalized: dict[str, Any]) -> dict[str, Any]:
        analysis = normalized["analysis"]
        competitor = normalized["competitor_analysis"]
        trend_keywords = normalized["trend_keywords"]
        audience = normalized["audience"]
        platform = normalized["platform"].lower()
        content_type = normalized["content_type"]
        region = normalized["region"]
        virality = self._safe_number(analysis.get("virality_score"))
        engagement = self._safe_number(analysis.get("engagement_probability"))
        trend_match = self._safe_number(normalized["trend_match_score"])
        audience_fit = self._safe_number(analysis.get("audience_fit"))
        tone = self._best_tone(platform, audience, content_type)
        category = self._best_category(content_type, audience, competitor, normalized["title"])
        post_time = str(analysis.get("best_posting_time") or self._best_posting_time(platform, audience)).strip()
        next_post = self._next_post_idea(normalized["title"], audience, content_type, tone, competitor)
        hashtags = self._build_hashtag_plan(normalized["hashtags"], normalized["title"], trend_keywords, competitor)
        audience_insight = self._audience_insight(audience, virality, engagement, trend_match, region)
        growth_insights = [
            f"Virality score is {virality:.0f}, so the next post should sharpen the first line.",
            f"Trend alignment is {trend_match:.0f}%, which means a current keyword angle can lift reach.",
            f"Audience fit sits at {audience_fit:.0f}%, so keep the tone aligned to {audience or 'your audience'}.",
        ]
        recommendation_bullets = [
            f"Lead with a {tone.lower()} hook and keep the opening under 12 words.",
            f"Package it as a {category.lower()} and post around {post_time}.",
            f"Use {', '.join(hashtags[:3])} and close with one clear CTA.",
        ]

        strategy_cards = [
            {"label": "What to post next", "value": next_post, "detail": "Keep it short and visual."},
            {"label": "Best content category", "value": category, "detail": f"Works well for {audience or 'this audience'}."},
            {"label": "Best posting time", "value": post_time, "detail": "Match the audience's active window."},
            {"label": "Best content tone", "value": tone, "detail": "Stay clear, useful, and specific."},
            {"label": "Recommended hashtags", "value": " ".join(hashtags[:5]), "detail": "Blend broad and niche tags."},
            {"label": "Audience insight", "value": audience_insight, "detail": "Use it as the post's proof point."},
        ]

        return self._finalize_strategy(
            normalized=normalized,
            source="rule-based",
            summary=f"Focus on {category.lower()} content with a {tone.lower()} tone and a stronger first line.",
            what_to_post_next=next_post,
            best_content_category=category,
            best_posting_time=post_time,
            best_content_tone=tone,
            recommended_hashtags=hashtags,
            audience_insights=audience_insight,
            strategy_cards=strategy_cards,
            recommendation_bullets=recommendation_bullets,
            growth_insights=growth_insights,
            trend_match_takeaway=f"Trend match score is {trend_match:.0f}%. Use the trending angle in the hook.",
            competitor_takeaway=self._competitor_takeaway(competitor),
            confidence=self._confidence(virality, engagement, trend_match),
        )

    def _normalize_output(self, data: dict[str, Any], normalized: dict[str, Any], source: str) -> dict[str, Any]:
        strategy_cards = data.get("strategy_cards") or []
        if not isinstance(strategy_cards, list) or not strategy_cards:
            strategy_cards = self._rule_based_strategy(normalized)["strategy_cards"]

        recommendation_bullets = self._coerce_list(data.get("recommendation_bullets"))
        if not recommendation_bullets:
            recommendation_bullets = self._rule_based_strategy(normalized)["recommendation_bullets"]

        growth_insights = self._coerce_list(data.get("growth_insights"))
        if not growth_insights:
            growth_insights = self._rule_based_strategy(normalized)["growth_insights"]

        recommended_hashtags = self._coerce_list(data.get("recommended_hashtags"))
        if not recommended_hashtags:
            recommended_hashtags = self._build_hashtag_plan(
                normalized["hashtags"],
                normalized["title"],
                normalized["trend_keywords"],
                normalized["competitor_analysis"],
            )

        return self._finalize_strategy(
            normalized=normalized,
            source=source,
            summary=str(data.get("summary") or "").strip() or f"Post {normalized['content_type'].lower()} content for {normalized['audience']}.",
            what_to_post_next=str(data.get("what_to_post_next") or "").strip() or self._next_post_idea(
                normalized["title"], normalized["audience"], normalized["content_type"], self._best_tone(normalized["platform"].lower(), normalized["audience"], normalized["content_type"]), normalized["competitor_analysis"]
            ),
            best_content_category=str(data.get("best_content_category") or "").strip() or self._best_category(
                normalized["content_type"], normalized["audience"], normalized["competitor_analysis"], normalized["title"]
            ),
            best_posting_time=str(data.get("best_posting_time") or "").strip() or self._best_posting_time(normalized["platform"].lower(), normalized["audience"]),
            best_content_tone=str(data.get("best_content_tone") or "").strip() or self._best_tone(
                normalized["platform"].lower(), normalized["audience"], normalized["content_type"]
            ),
            recommended_hashtags=recommended_hashtags,
            audience_insights=str(data.get("audience_insights") or "").strip() or self._audience_insight(
                normalized["audience"],
                self._safe_number(normalized["analysis"].get("virality_score")),
                self._safe_number(normalized["analysis"].get("engagement_probability")),
                self._safe_number(normalized["trend_match_score"]),
                normalized["region"],
            ),
            strategy_cards=strategy_cards,
            recommendation_bullets=recommendation_bullets,
            growth_insights=growth_insights,
            trend_match_takeaway=str(data.get("trend_match_takeaway") or "").strip()
            or f"Trend match score is {self._safe_number(normalized['trend_match_score']):.0f}%. Use a current keyword in the hook.",
            competitor_takeaway=str(data.get("competitor_takeaway") or "").strip() or self._competitor_takeaway(normalized["competitor_analysis"]),
            confidence=self._confidence(
                self._safe_number(normalized["analysis"].get("virality_score")),
                self._safe_number(normalized["analysis"].get("engagement_probability")),
                self._safe_number(normalized["trend_match_score"]),
            ),
        )

    def _finalize_strategy(
        self,
        *,
        normalized: dict[str, Any],
        source: str,
        summary: str,
        what_to_post_next: str,
        best_content_category: str,
        best_posting_time: str,
        best_content_tone: str,
        recommended_hashtags: list[str],
        audience_insights: str,
        strategy_cards: list[dict[str, Any]],
        recommendation_bullets: list[str],
        growth_insights: list[str],
        trend_match_takeaway: str,
        competitor_takeaway: str,
        confidence: float,
    ) -> dict[str, Any]:
        return {
            "success": True,
            "source": source,
            "summary": summary,
            "what_to_post_next": what_to_post_next,
            "best_content_category": best_content_category,
            "best_posting_time": best_posting_time,
            "best_content_tone": best_content_tone,
            "recommended_hashtags": recommended_hashtags[:8],
            "audience_insights": audience_insights,
            "strategy_cards": strategy_cards[:6],
            "recommendation_bullets": recommendation_bullets[:5],
            "growth_insights": growth_insights[:4],
            "trend_match_takeaway": trend_match_takeaway,
            "competitor_takeaway": competitor_takeaway,
            "confidence": round(confidence, 1),
            "analysis_snapshot": {
                "title": normalized["title"],
                "caption": normalized["caption"],
                "audience": normalized["audience"],
                "platform": normalized["platform"],
                "content_type": normalized["content_type"],
                "virality_score": normalized["analysis"].get("virality_score"),
                "engagement_probability": normalized["analysis"].get("engagement_probability"),
                "trend_match_score": normalized["trend_match_score"],
            },
        }

    def _best_category(self, content_type: str, audience: str, competitor: dict[str, Any], title: str) -> str:
        competitor_style = str(competitor.get("content_style") or "").lower()
        if "educational" in competitor_style or "tutorial" in competitor_style:
            return "Educational breakdown"
        if "story" in competitor_style or "insight" in competitor_style:
            return "Insight post"
        if "linkedin" in title.lower() or "founder" in audience.lower():
            return "Professional thought post"
        if content_type:
            return f"{content_type} breakdown"
        return "Short practical post"

    def _best_posting_time(self, platform: str, audience: str) -> str:
        platform = platform.lower()
        audience = audience.lower()
        if platform == "linkedin":
            return "Tue-Thu, 8:00 AM - 10:00 AM"
        if platform in {"instagram", "tiktok"}:
            return "6:00 PM - 9:00 PM"
        if platform == "youtube":
            return "12:00 PM - 3:00 PM"
        if "student" in audience:
            return "7:00 PM - 9:00 PM"
        if "founder" in audience or "professional" in audience:
            return "8:00 AM - 11:00 AM"
        return "Late morning or early evening"

    def _best_tone(self, platform: str, audience: str, content_type: str) -> str:
        audience = audience.lower()
        if platform == "linkedin" or "founder" in audience or "professional" in audience:
            return "Professional and practical"
        if "student" in audience:
            return "Clear and encouraging"
        if "creator" in audience:
            return "Conversational and actionable"
        if "tech" in audience or "developer" in audience:
            return "Technical and concise"
        return "Clear and useful"

    def _next_post_idea(self, title: str, audience: str, content_type: str, tone: str, competitor: dict[str, Any]) -> str:
        title_seed = title or "this topic"
        top_theme = str((competitor.get("keyword_themes") or [{}])[0].get("theme") if isinstance(competitor.get("keyword_themes"), list) and competitor.get("keyword_themes") else "").strip()
        theme_line = f"around {top_theme}" if top_theme else "with one strong example"
        return f"Post a {content_type.lower()} on {title_seed} {theme_line} in a {tone.lower()} tone for {audience.lower()}."

    def _build_hashtag_plan(
        self,
        hashtags: list[str],
        title: str,
        trend_keywords: list[dict[str, Any]],
        competitor: dict[str, Any],
    ) -> list[str]:
        candidates = list(hashtags)
        for item in trend_keywords[:4]:
            keyword = str(item.get("keyword") or "").strip()
            if keyword:
                candidates.append(f"#{re.sub(r'[^a-zA-Z0-9]+', '', keyword).lower()}")
        for theme in (competitor.get("keyword_themes") or [])[:2]:
            candidate = str(theme.get("theme") or "").strip()
            if candidate:
                candidates.append(f"#{re.sub(r'[^a-zA-Z0-9]+', '', candidate).lower()}")
        if title:
            candidates.append(f"#{re.sub(r'[^a-zA-Z0-9]+', '', title).lower()[:24]}")
        candidates.extend(["#creatorstrategy", "#ai", "#contentstrategy"])
        cleaned: list[str] = []
        seen: set[str] = set()
        for tag in candidates:
            value = str(tag or "").strip()
            if not value:
                continue
            if not value.startswith("#"):
                value = f"#{value.lstrip('#')}"
            value = value.lower()
            if value not in seen:
                seen.add(value)
                cleaned.append(value)
        return cleaned[:8]

    def _audience_insight(self, audience: str, virality: float, engagement: float, trend_match: float, region: str = "Global") -> str:
        lift = max(8, min(34, round((virality * 0.22) + (engagement * 0.12) + (trend_match * 0.18))))
        return f"AI automation content performs {lift}% better for {audience or 'this audience'} in {region} when it shows one practical example."

    def _competitor_takeaway(self, competitor: dict[str, Any]) -> str:
        competitor_name = str(competitor.get("competitor") or competitor.get("topic") or "the competitor").strip()
        style = str(competitor.get("content_style") or "clear").strip().lower()
        pattern = str(competitor.get("posting_pattern") or "steady cadence").strip().lower()
        return f"{competitor_name} is leaning into {style} posts, so keep your angle sharper and match the {pattern} signal."

    def _confidence(self, virality: float, engagement: float, trend_match: float) -> float:
        return max(52.0, min(97.0, 42.0 + (virality * 0.28) + (engagement * 0.24) + (trend_match * 0.18)))

    def _normalize_hashtags(self, hashtags: Any) -> list[str]:
        if hashtags is None:
            return []
        if isinstance(hashtags, list):
            items = hashtags
        else:
            items = re.split(r"[,\s]+", str(hashtags))
        normalized: list[str] = []
        for item in items:
            token = str(item).strip()
            if not token:
                continue
            token = token.lstrip("#")
            token = re.sub(r"[^a-zA-Z0-9_]+", "", token)
            if len(token) < 2:
                continue
            normalized.append(f"#{token.lower()}")
        deduped: list[str] = []
        seen: set[str] = set()
        for tag in normalized:
            if tag not in seen:
                seen.add(tag)
                deduped.append(tag)
        return deduped[:8]

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

    def _load_openai_client(self):
        try:
            from openai import OpenAI
        except Exception:
            return None

        try:
            return OpenAI(api_key=self.openai_api_key)
        except Exception:
            return None

    def _coerce_list(self, value: Any) -> list[str]:
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str):
            return [item.strip() for item in re.split(r"[\n,•]+", value) if item.strip()]
        return []

    def _safe_number(self, value: Any) -> float:
        try:
            return float(value or 0)
        except Exception:
            return 0.0
