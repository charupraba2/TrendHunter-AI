"""AI chat assistant for creator guidance inside the dashboard."""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

from backend.services.creator_strategy_service import CreatorStrategyService
from backend.services.gemini_service import GeminiService
from backend.services.insight_tools import InsightTools

logger = logging.getLogger(__name__)


class AIChatService:
    def __init__(self) -> None:
        self.gemini_service = GeminiService()
        self.strategy_service = CreatorStrategyService()
        self.insight_tools = InsightTools()
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "").strip()
        self._openai_client = self._load_openai_client() if self.openai_api_key else None
        self._gemini_unavailable = False
        self.gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    def chat(self, payload: dict[str, Any]) -> dict[str, Any]:
        normalized = self._normalize_payload(payload or {})
        question = normalized["question"]
        context = normalized["context"]

        logger.info(
            "AI chat request: question=%s has_analysis=%s has_strategy=%s has_competitor=%s trends=%s",
            question,
            bool(context.get("analysis")),
            bool(context.get("strategy")),
            bool(context.get("competitor")),
            len(context.get("trends") or []),
        )

        if self.gemini_service._client is not None and not self._gemini_unavailable:
            try:
                return self._from_ai("gemini", normalized)
            except Exception as exc:
                logger.warning("Gemini assistant response failed: %s", exc)
                self._gemini_unavailable = True

        if self._openai_client is not None:
            try:
                return self._from_ai("openai", normalized)
            except Exception as exc:
                logger.warning("OpenAI assistant response failed: %s", exc)

        return self._rule_based_response(normalized)

    def _normalize_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        question = str(payload.get("message") or payload.get("question") or "").strip()
        analysis = payload.get("latest_analysis_result") or payload.get("analysis_result") or payload.get("analysis") or {}
        strategy = payload.get("strategy_output") or payload.get("latest_strategy") or payload.get("strategy") or {}
        competitor = payload.get("competitor_analysis") or analysis.get("competitor_analysis") or {}
        performance = payload.get("post_performance") or payload.get("performance") or payload.get("latest_performance") or {}
        region = str(payload.get("region") or payload.get("trend_region") or analysis.get("region") or analysis.get("current_request", {}).get("region") or "Global").strip() or "Global"
        trends = payload.get("trend_snapshot") or payload.get("trends") or analysis.get("similar_trends") or []
        current_trends = payload.get("current_trends") or []
        if isinstance(trends, dict):
            trends = trends.get("items") or trends.get("trend_keywords") or []
        if not isinstance(trends, list):
            trends = []
        if not isinstance(current_trends, list):
            current_trends = []
        if not isinstance(analysis, dict):
            analysis = {}
        if not isinstance(strategy, dict):
            strategy = {}
        if not isinstance(competitor, dict):
            competitor = {}
        if not isinstance(performance, dict):
            performance = {}

        current_request = analysis.get("current_request", {}) if isinstance(analysis.get("current_request"), dict) else {}
        title = str(payload.get("title") or current_request.get("title") or analysis.get("title") or "").strip()
        caption = str(payload.get("caption") or current_request.get("caption") or analysis.get("caption") or "").strip()
        audience = str(payload.get("audience") or current_request.get("audience") or analysis.get("audience") or "").strip()
        platform = str(payload.get("platform") or current_request.get("platform") or analysis.get("platform") or "LinkedIn").strip() or "LinkedIn"
        content_type = str(payload.get("content_type") or current_request.get("content_type") or analysis.get("content_type") or "").strip()

        trend_match_score = self._safe_number(
            payload.get("trend_match_score")
            or analysis.get("trend_match_score")
            or analysis.get("analysis", {}).get("trend_match_score")
        )
        virality_score = self._safe_number(analysis.get("virality_score") or analysis.get("analysis", {}).get("virality_score"))
        hook_strength = self._safe_number(analysis.get("hook_strength") or analysis.get("analysis", {}).get("hook_strength"))
        engagement_probability = self._safe_number(analysis.get("engagement_probability") or analysis.get("analysis", {}).get("engagement_probability"))
        best_posting_time = str(strategy.get("best_posting_time") or analysis.get("best_posting_time") or "").strip()
        recommended_hashtags = self._normalize_hashtags(
            strategy.get("recommended_hashtags")
            or analysis.get("optimized_hashtags")
            or analysis.get("normalized_hashtags")
            or payload.get("hashtags")
            or current_request.get("hashtags")
            or []
        )
        trend_keywords = payload.get("trend_keywords") or analysis.get("trend_keywords") or []
        if not isinstance(trend_keywords, list):
            trend_keywords = []

        context = {
            "analysis": analysis,
            "strategy": strategy,
            "competitor": competitor,
            "trends": trends,
            "current_trends": current_trends,
            "title": title,
            "caption": caption,
            "audience": audience or "General audience",
            "platform": platform,
            "content_type": content_type or "Post",
            "region": region,
            "trend_match_score": trend_match_score,
            "virality_score": virality_score,
            "hook_strength": hook_strength,
            "engagement_probability": engagement_probability,
            "best_posting_time": best_posting_time,
            "recommended_hashtags": recommended_hashtags,
            "trend_keywords": trend_keywords,
            "performance": performance,
        }

        return {"question": question, "context": context}

    def _from_ai(self, provider: str, normalized: dict[str, Any]) -> dict[str, Any]:
        prompt = self._build_prompt(normalized)
        response_text = ""
        if provider == "gemini" and self.gemini_service._client is not None:
            model = self.gemini_service._client.GenerativeModel(self.gemini_model)
            response = model.generate_content(prompt)
            response_text = getattr(response, "text", "") or ""
        elif provider == "openai" and self._openai_client is not None:
            response = self._openai_client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                messages=[
                    {"role": "system", "content": "You are a concise creator coach for TrendHunter AI. Return only valid JSON."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.35,
            )
            response_text = response.choices[0].message.content or ""

        parsed = self._parse_json(response_text)
        if not parsed:
            if provider == "gemini":
                self._gemini_unavailable = True
            raise ValueError("Assistant response was not valid JSON.")

        reply = str(parsed.get("reply") or "").strip()
        if not reply:
            reply = self._rule_based_reply(normalized)["reply"]

        quick_replies = self._coerce_list(parsed.get("quick_replies"))
        if not quick_replies:
            quick_replies = self._rule_based_reply(normalized)["quick_replies"]

        return {
            "success": True,
            "source": provider,
            "reply": self._shorten(reply),
            "quick_replies": quick_replies[:4],
        }

    def _build_prompt(self, normalized: dict[str, Any]) -> str:
        context = normalized["context"]
        question = normalized["question"]
        return (
            "You are a short, practical AI chat assistant for a creator dashboard. "
            "Answer in 2-4 concise sentences and return ONLY valid JSON with keys: reply, quick_replies.\n"
            f"User question: {question}\n"
            f"Latest analysis: {json.dumps(context.get('analysis', {}), ensure_ascii=False)}\n"
            f"Strategy output: {json.dumps(context.get('strategy', {}), ensure_ascii=False)}\n"
            f"Competitor analysis: {json.dumps(context.get('competitor', {}), ensure_ascii=False)}\n"
            f"Trend data: {json.dumps(context.get('trends', []), ensure_ascii=False)}\n"
            f"Trend keywords: {json.dumps(context.get('trend_keywords', []), ensure_ascii=False)}\n"
            f"Post performance: {json.dumps(context.get('performance', {}), ensure_ascii=False)}\n"
            f"Current trends: {json.dumps(context.get('current_trends', []), ensure_ascii=False)}\n"
            f"Title: {context.get('title')}\n"
            f"Caption: {context.get('caption')}\n"
            f"Audience: {context.get('audience')}\n"
            f"Platform: {context.get('platform')}\n"
            f"Region: {context.get('region')}\n"
            f"Content type: {context.get('content_type')}\n"
            f"Virality score: {context.get('virality_score')}\n"
            f"Hook strength: {context.get('hook_strength')}\n"
            f"Engagement probability: {context.get('engagement_probability')}\n"
            f"Trend match score: {context.get('trend_match_score')}\n"
            f"Best posting time: {context.get('best_posting_time')}\n"
            f"Recommended hashtags: {json.dumps(context.get('recommended_hashtags', []), ensure_ascii=False)}\n"
            "Keep the answer short, direct, and creator-focused."
        )

    def _rule_based_response(self, normalized: dict[str, Any]) -> dict[str, Any]:
        question = normalized["question"].lower()
        context = normalized["context"]
        reply = self._reply_from_question(question, context)
        return {
            "success": True,
            "source": "rule-based",
            "reply": self._shorten(reply),
            "quick_replies": self._quick_replies(context),
        }

    def _reply_from_question(self, question: str, context: dict[str, Any]) -> str:
        hook_strength = self._safe_number(context.get("hook_strength"))
        virality = self._safe_number(context.get("virality_score"))
        engagement = self._safe_number(context.get("engagement_probability"))
        trend_match = self._safe_number(context.get("trend_match_score"))
        best_posting_time = context.get("best_posting_time") or self.strategy_service._best_posting_time(context.get("platform", ""), context.get("audience", ""))
        hashtags = context.get("recommended_hashtags") or ["#creatorstrategy", "#ai", "#content"]
        audience = context.get("audience") or "your audience"
        region = context.get("region") or "your region"
        competitor = context.get("competitor") or {}
        competitor_name = str(competitor.get("competitor") or competitor.get("topic") or "your competitor").strip()
        competitor_style = str(competitor.get("content_style") or "clear").strip().lower()
        performance = context.get("performance") or {}
        lifecycle = str(performance.get("lifecycle_stage") or performance.get("trend_lifecycle") or "").strip().lower()
        momentum = self._safe_number(performance.get("virality_momentum") or performance.get("momentum"))
        growth_speed = self._safe_number(performance.get("growth_speed"))
        engagement_velocity = self._safe_number(performance.get("engagement_velocity"))
        engagement_decay = self._safe_number(performance.get("engagement_decay"))
        should_repost = bool(performance.get("should_repost"))
        should_follow_up = bool(performance.get("should_follow_up"))
        should_improve_hook = bool(performance.get("should_improve_hook"))
        should_shorten_caption = bool(performance.get("should_shorten_caption"))

        if "hook" in question and ("weak" in question or "improve" in question):
            if hook_strength < 55:
                return "Your hook is weak because it is not promising a fast payoff yet. Lead with one specific outcome, one audience, and one proof point."
            return f"Your hook is decent, but it can still improve by making the payoff clearer in the first line."
        if "repost" in question or "post again" in question:
            if should_repost or lifecycle in {"rising", "peaking"}:
                return "Yes, repost it with a sharper hook and a stronger first line. The current engagement momentum is good enough to justify another push."
            return "I would wait before reposting. Improve the hook or add a follow-up angle first."
        if "die soon" in question or "trend die" in question or "will this trend die" in question:
            if lifecycle in {"declining", "saturated"} or engagement_decay >= 55:
                return "Yes, the current trend signals show it may cool down soon. Publish a follow-up quickly if you want to catch the tail end of the attention."
            return "It does not look like it will die immediately. The engagement curve still has room to hold if you keep the momentum active."
        if "why engagement slowing" in question or "engagement slowing" in question or "why is engagement slowing" in question:
            if lifecycle in {"declining", "saturated"}:
                return "Engagement is slowing because the topic is nearing saturation. Refresh the hook, shorten the caption, and reply to comments faster."
            return "The slowdown is likely from weaker posting velocity rather than a dead topic. Add a follow-up post and keep replying in the comments."
        if "follow-up" in question or "part 2" in question:
            if should_follow_up or lifecycle in {"rising", "peaking", "stable"}:
                return "Yes, create Part 2 within the next 24 hours. The original post has enough signal to support a follow-up."
            return "A follow-up can help, but it should be reframed with a better hook first."
        if "improve caption" in question or "shorten caption" in question:
            if should_shorten_caption or lifecycle in {"saturated", "declining"}:
                return "Shorten the caption and move the key payoff higher. Keep it easier to scan and reduce any extra fluff."
            return "The caption is usable, but you can still trim it slightly to improve readability."
        if "engagement" in question:
            lift = max(5, round((virality * 0.18) + (engagement * 0.22) + (trend_match * 0.15) + (momentum * 0.12) + (growth_speed * 0.08)))
            return f"Engagement should improve if you tighten the hook and lean on current keywords. AI automation content is performing about {lift}% better for {audience} when it gives one practical example."
        if "posting time" in question or "best time" in question:
            return f"Best posting time: {best_posting_time}. That matches the audience pattern and should give the post a cleaner first-hour signal."
        if "hashtag" in question:
            return f"Use a mix of broad and niche tags like {', '.join(hashtags[:4])}. Keep it to 3-5 tags so the post stays focused."
        if "trend score" in question or "why trend score low" in question:
            if trend_match < 35:
                return "Trend score is low because the post is not matching current keywords strongly enough. Add one trending term in the hook and one in the caption."
            return "Trend score is okay, but you can raise it by matching the current trend language more closely."
        if "popular" in question or "trends" in question:
            trend_keywords = context.get("trend_keywords") or []
            top_trends = [item.get("keyword") or item.get("title") or item.get("name") for item in context.get("current_trends") or context.get("trends") or []]
            top_trends = [str(item).strip() for item in top_trends if str(item).strip()]
            if top_trends:
                return f"Popular trends in {region} include {', '.join(top_trends[:4])}. For {audience}, focus on the most practical keyword and keep the hook simple."
            if trend_keywords:
                keywords = [item.get("keyword") for item in trend_keywords if item.get("keyword")]
                return f"Popular trends in {region} lean toward {', '.join(keywords[:4])}. Use one of those keywords in your hook."
        if "competitor" in question:
            return f"{competitor_name} is using a {competitor_style} style, so your edge is to be sharper, more specific, and more practical."
        return (
            f"Focus on a sharper hook, a clearer payoff, and one action step. "
            f"That usually works better for {audience} than adding more text."
        )

    def _quick_replies(self, context: dict[str, Any]) -> list[str]:
        return [
            "Why is my hook weak?",
            "How to improve engagement?",
            f"Best posting time: {context.get('best_posting_time') or 'Use the next active window'}",
            "Why trend score low?",
        ]

    def _shorten(self, text: str, limit: int = 420) -> str:
        value = re.sub(r"\s+", " ", str(text or "")).strip()
        if len(value) <= limit:
            return value
        return value[: limit - 1].rstrip() + "..."

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
        return list(dict.fromkeys(normalized))

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

