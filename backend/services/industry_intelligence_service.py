"""Live industry intelligence collection for Giggso and enterprise AI signals."""

from __future__ import annotations

import json
from html import unescape
import logging
import os
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from statistics import pstdev
from threading import Lock
from typing import Any
from urllib.parse import quote_plus
from xml.etree import ElementTree as ET

import requests
from bs4 import BeautifulSoup

from backend.database import (
    IndustryCompany,
    IndustryCompetitorActivity,
    IndustryCompetitor,
    IndustryInsight,
    IndustryKeyword,
    IndustryLiveTrend,
    IndustryOpportunity,
    IndustryRAGDocument,
    IndustryRecommendation,
    IndustryReport,
    IndustryTrend,
    LinkedInPostRecord,
    get_industry_company,
    get_industry_competitor_activity,
    get_industry_insights,
    get_industry_keywords,
    get_industry_live_trends,
    get_industry_opportunities,
    get_industry_recommendations,
    get_industry_report,
    get_db_session,
    get_trend_history as db_get_trend_history,
    get_trend_history_leaderboard as db_get_trend_history_leaderboard,
    save_trend_history,
)
from backend.services.gemini_service import GeminiService
from backend.services.industry_analytics_scoring import industry_analytics_scoring_engine
from backend.services.product_impact_ml import product_impact_ml_engine

logger = logging.getLogger(__name__)

_NOW = lambda: datetime.now(timezone.utc)

COMPANY_NAME = "Giggso"
COMPANY_WEBSITE = "https://www.giggso.com/"
COMPANY_LINKEDIN = os.getenv("LINKEDIN_COMPANY_URL", "https://www.linkedin.com/company/gogiggso/posts/?feedView=all").strip()

GIGGSO_PAGES = [
    COMPANY_WEBSITE,
    "https://giggso.com/about",
    "https://giggso.com/solutions/ai-governance",
    "https://giggso.com/services/execution",
    "https://giggso.com/services/airtaas",
    "https://giggso.com/products/prism7-aisecops",
    "https://giggso.com/products/log-analyzer",
    "https://giggso.com/services/greaas",
    "https://giggso.com/services/strategy",
    "https://giggso.com/solutions/technology",
    "https://giggso.com/solutions/financial-services",
    "https://giggso.com/solutions/government",
    "https://www.giggso.com/contact?interest=general-consultation",
]

AI_GOVERNANCE_TOPICS = [
    "AI Governance",
    "Agentic AI",
    "LLM Security",
    "Model Monitoring",
    "AI Compliance",
    "AI Risk",
    "RAG",
    "Enterprise AI",
    "Trustworthy AI",
    "Shadow AI",
]

COMPETITOR_CONFIG = [
    {
        "name": "OpenAI",
        "focus_area": "Foundation models and enterprise AI infrastructure",
        "positioning": "Platform leader expanding from model capability into enterprise deployment and security.",
        "domain": "openai.com",
        "search_query": "OpenAI enterprise security agentic AI",
    },
    {
        "name": "Anthropic",
        "focus_area": "Safe enterprise LLMs and controlled reasoning",
        "positioning": "Safety-first LLM vendor competing on trust, reliability, and governance alignment.",
        "domain": "anthropic.com",
        "search_query": "Anthropic enterprise safety AI governance",
    },
    {
        "name": "Microsoft AI",
        "focus_area": "Enterprise copilots, agents, and cloud AI operations",
        "positioning": "Ecosystem platform bundling agents, productivity, and governance controls.",
        "domain": "microsoft.com",
        "search_query": "Microsoft AI agent governance enterprise",
    },
    {
        "name": "Google DeepMind",
        "focus_area": "Frontier research and multimodal model innovation",
        "positioning": "Research-led AI platform shaping expectations for model quality and capability.",
        "domain": "deepmind.google",
        "search_query": "Google DeepMind enterprise AI governance",
    },
    {
        "name": "Perplexity",
        "focus_area": "AI search and enterprise research workflows",
        "positioning": "Fast-moving AI discovery layer competing on answer quality and knowledge access.",
        "domain": "perplexity.ai",
        "search_query": "Perplexity enterprise AI search governance",
    },
    {
        "name": "Cohere",
        "focus_area": "Enterprise LLMs, secure deployments, and private model operations",
        "positioning": "Enterprise-focused vendor emphasizing secure AI, private deployment, and customization.",
        "domain": "cohere.com",
        "search_query": "Cohere enterprise AI security governance",
    },
]

NEWS_QUERIES = [
    "AI Governance",
    "Agentic AI",
    "AI Security",
    "LLM Security",
    "Enterprise AI",
    "Trustworthy AI",
    "AI Risk",
    "Compliance",
]

LINKEDIN_MAX_POSTS = int(os.getenv("LINKEDIN_MAX_POSTS", "10") or 10)


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = re.sub(r"\s+", " ", str(value)).strip()
    return text


def _safe_number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc) if value.tzinfo else value.replace(tzinfo=timezone.utc)
    text = str(value).strip()
    for candidate in (
        text,
        text.replace("Z", "+00:00"),
    ):
        try:
            parsed = datetime.fromisoformat(candidate)
            return parsed.astimezone(timezone.utc) if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


class IndustryIntelligenceService:
    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "TrendHunterAI/1.0 (+https://trendhunter.local)",
                "Accept": "text/html,application/xml,application/rss+xml,text/xml,*/*;q=0.8",
            }
        )
        self.gemini_service = GeminiService()
        self._cache_lock = Lock()
        self._last_refresh_at: datetime | None = None
        self._cached_snapshot: dict[str, Any] | None = None

    def _clamp(self, value: float, minimum: float, maximum: float) -> float:
        return max(minimum, min(maximum, value))

    def _trend_direction(self, delta: float) -> tuple[str, str]:
        if delta >= 5:
            return "rising", "Rising strongly" if delta >= 10 else "Rising"
        if delta <= -5:
            return "falling", "Falling strongly" if delta <= -10 else "Falling"
        return "stable", "Stable"

    def refresh(self, force: bool = False) -> dict[str, Any]:
        with self._cache_lock:
            now = _NOW()
            if not force:
                persisted_snapshot = self._load_persisted_snapshot()
                if persisted_snapshot:
                    self._cached_snapshot = persisted_snapshot
                    self._last_refresh_at = now
                    return dict(persisted_snapshot)
            if not force and self._cached_snapshot and self._last_refresh_at and (now - self._last_refresh_at) < timedelta(minutes=10):
                return dict(self._cached_snapshot)

            try:
                snapshot = self._build_snapshot(now)
                self._persist_snapshot(snapshot)
            except Exception as exc:
                logger.exception("Industry refresh failed; using cached industry snapshot instead")
                snapshot = self._load_persisted_snapshot()
                if snapshot is None:
                    from backend.database import _build_live_industry_snapshot

                    fallback = _build_live_industry_snapshot(now)
                    snapshot = {
                        "company": fallback.get("company") or {},
                        "company_signals": {
                            "company_name": (fallback.get("company") or {}).get("company_name") or COMPANY_NAME,
                            "website": (fallback.get("company") or {}).get("website") or COMPANY_WEBSITE,
                            "linkedin_url": (fallback.get("company") or {}).get("linkedin_url") or COMPANY_LINKEDIN,
                            "positioning": (fallback.get("company") or {}).get("market_positioning") or (fallback.get("company") or {}).get("industry_positioning") or "",
                            "core_services": (fallback.get("company") or {}).get("core_focus_areas") or [],
                            "strategic_themes": (fallback.get("company") or {}).get("strategic_themes") or [],
                            "focus_keywords": (fallback.get("company") or {}).get("focus_keywords") or [],
                            "product_messaging": (fallback.get("company") or {}).get("content_themes") or [],
                            "source_notes": (fallback.get("company") or {}).get("source_notes") or [],
                            "last_updated": (fallback.get("company") or {}).get("last_updated"),
                        },
                        "linkedin": {},
                        "linkedin_posts": [],
                        "linkedin_themes": {},
                        "news": [],
                        "competitor_signals": fallback.get("competitors") or [],
                        "live_trends": fallback.get("trends") or [],
                        "keywords": fallback.get("keywords") or [],
                        "recommendations": fallback.get("recommendations") or [],
                        "competitor_cards": fallback.get("competitors") or [],
                        "insights": [],
                        "opportunities": [],
                        "report": fallback.get("report") or {},
                        "documents": [],
                    }
            self._cached_snapshot = snapshot
            self._last_refresh_at = now
            return snapshot

    def _load_persisted_snapshot(self) -> dict[str, Any] | None:
        company = get_industry_company() or {}
        live_trends = get_industry_live_trends()
        keywords = get_industry_keywords()
        recommendations = get_industry_recommendations()
        competitor_cards = get_industry_competitor_activity()
        insights = get_industry_insights()
        opportunities = get_industry_opportunities()
        report = get_industry_report() or {}
        has_data = any([company, live_trends, keywords, recommendations, competitor_cards, insights, opportunities, report])
        if not has_data:
            return None

        linkedin_posts = self._get_cached_linkedin_posts(limit=LINKEDIN_MAX_POSTS)
        linkedin_themes = self._derive_linkedin_themes(linkedin_posts, [item.get("content", "") for item in linkedin_posts]) if linkedin_posts else {
            "top_theme": "AI Governance",
            "emerging_theme": "Enterprise AI",
            "keyword_ranking": [],
            "trend_frequency": {},
            "strategic_narrative": "Recent LinkedIn signals emphasize AI governance and enterprise readiness.",
        }
        source_label = linkedin_posts[0].get("source") if linkedin_posts else "Stored LinkedIn cache"
        linkedin = {
            **linkedin_themes,
            "source_status": "cache" if linkedin_posts else "fallback",
            "source_label": source_label,
            "source_coverage": [source_label] if source_label else [],
            "source_notes": [],
            "posts": linkedin_posts,
            "themes": linkedin_themes,
            "last_updated": linkedin_posts[0].get("published_date") if linkedin_posts else None,
        }
        company_signals = {
            "company_name": company.get("company_name") or COMPANY_NAME,
            "website": company.get("website") or COMPANY_WEBSITE,
            "linkedin_url": company.get("linkedin_url") or COMPANY_LINKEDIN,
            "positioning": company.get("market_positioning") or company.get("industry_positioning") or "",
            "core_services": company.get("core_focus_areas") or [],
            "strategic_themes": company.get("strategic_themes") or [],
            "focus_keywords": company.get("focus_keywords") or [],
            "product_messaging": company.get("content_themes") or [],
            "source_notes": company.get("source_notes") or [],
            "last_updated": company.get("last_updated"),
        }
        return {
            "company": company,
            "company_signals": company_signals,
            "linkedin": linkedin,
            "linkedin_posts": linkedin_posts,
            "linkedin_themes": linkedin_themes,
            "news": [],
            "competitor_signals": competitor_cards,
            "live_trends": live_trends,
            "keywords": keywords,
            "recommendations": recommendations,
            "competitor_cards": competitor_cards,
            "insights": insights,
            "opportunities": opportunities,
            "report": report,
            "documents": [],
        }

    def get_company_signals(self) -> dict[str, Any]:
        snapshot = self.refresh()
        return {
            "success": True,
            "item": snapshot["company"],
            "signals": snapshot["company_signals"],
        }

    def get_linkedin_intelligence(self) -> dict[str, Any]:
        snapshot = self.refresh()
        return {
            "success": True,
            "item": snapshot["linkedin"],
        }

    def get_linkedin_posts(self) -> dict[str, Any]:
        snapshot = self.refresh()
        return {
            "success": True,
            "items": snapshot["linkedin_posts"],
            "count": len(snapshot["linkedin_posts"]),
        }

    def get_linkedin_themes(self) -> dict[str, Any]:
        snapshot = self.refresh()
        return {
            "success": True,
            "item": snapshot["linkedin_themes"],
        }

    def get_news_intelligence(self) -> dict[str, Any]:
        snapshot = self.refresh()
        return {
            "success": True,
            "items": snapshot["news"],
            "count": len(snapshot["news"]),
        }

    def get_competitor_signals(self) -> dict[str, Any]:
        snapshot = self.refresh()
        return {
            "success": True,
            "items": snapshot["competitor_signals"],
            "count": len(snapshot["competitor_signals"]),
        }

    def get_executive_insights(self) -> dict[str, Any]:
        snapshot = self.refresh()
        return {
            "success": True,
            "items": snapshot["insights"],
            "count": len(snapshot["insights"]),
        }

    def get_rag_analysis(self, topic: str | None = None) -> dict[str, Any]:
        snapshot = self.refresh()
        query = _clean_text(topic) or "Giggso industry intelligence"
        documents = self._retrieve_rag_documents(query, limit=6)
        analysis = self._build_rag_analysis(query, documents, snapshot)
        return {
            "success": True,
            "item": analysis,
        }

    def get_trend_history(self, keyword: str, range_label: str = "7d") -> dict[str, Any]:
        history = db_get_trend_history(keyword, range_label=range_label)
        if not history:
            return {
                "success": False,
                "keyword": _clean_text(keyword),
                "current_score": 0,
                "previous_score": 0,
                "delta": 0,
                "direction": "stable",
                "movement_label": "Stable",
                "history": [],
                "range": str(range_label or "7d").lower(),
            }
        return {"success": True, **history}

    def get_trend_history_leaderboard(self, range_label: str = "7d") -> dict[str, Any]:
        return {"success": True, **db_get_trend_history_leaderboard(range_label=range_label)}

    def get_board_report(self) -> dict[str, Any]:
        snapshot = self.refresh()
        return {
            "success": True,
            "item": snapshot["report"],
        }

    def build_industry_board_report_payload(self) -> dict[str, Any]:
        snapshot = self.refresh(force=False)
        company = snapshot.get("company") or {}
        live_trends = snapshot.get("live_trends") or []
        competitors = snapshot.get("competitor_cards") or snapshot.get("competitor_signals") or []
        recommendations = snapshot.get("recommendations") or []
        opportunities = snapshot.get("opportunities") or []
        linkedin = snapshot.get("linkedin") or {}
        report = snapshot.get("report") or {}
        searches = []
        for query in ["ChatGPT", "Claude", "Gemini", "Agentic AI", "RAG", "MCP"]:
            search_item = self._build_search_intelligence(query, snapshot, persist_history=False)
            search_item["trend_history"] = db_get_trend_history(query)
            searches.append(search_item)
        top_trend = live_trends[0] if live_trends else {}
        top_opportunity = opportunities[0] if opportunities else {}
        top_risk = (report.get("strategic_risks") or [])
        top_risk_item = top_risk[0] if top_risk else {}
        top_recommendation = recommendations[0] if recommendations else {}
        source_coverage = {
            "company": "Giggso Website" if company else "Unavailable",
            "linkedin": linkedin.get("source_label") or "Unavailable",
            "news": "Google News RSS" if snapshot.get("news") else "Unavailable",
            "competitors": "Competitor Web/Search Signals" if competitors else "Unavailable",
            "insights": "Gemini / Fallback" if recommendations else "Fallback",
            "last_refreshed": report.get("generated_at").isoformat() if isinstance(report.get("generated_at"), datetime) else report.get("generated_at") or _NOW().isoformat(),
        }
        return {
            "generated_at": source_coverage["last_refreshed"],
            "company": company,
            "top_trends": live_trends,
            "search_highlights": searches,
            "competitors": competitors,
            "opportunities": opportunities,
            "recommendations": recommendations,
            "source_coverage": source_coverage,
            "executive_summary": {
                "top_signal": top_trend.get("trend_name") or "No live trend signal available",
                "main_opportunity": top_opportunity.get("opportunity_name") or "No live opportunity available",
                "main_risk": top_risk_item.get("risk") or top_risk_item.get("strategy_risk") or top_risk_item.get("summary") or "No live risk available",
                "recommended_action": top_recommendation.get("recommended_action") or top_recommendation.get("reason") or "Continue leading with governance-first enterprise AI positioning.",
            },
        }

    def get_live_trends(self) -> dict[str, Any]:
        snapshot = self.refresh()
        return {
            "success": True,
            "items": snapshot["live_trends"],
            "count": len(snapshot["live_trends"]),
        }

    def get_keywords(self) -> dict[str, Any]:
        snapshot = self.refresh()
        return {
            "success": True,
            "items": snapshot["keywords"],
            "count": len(snapshot["keywords"]),
            "groups": self._group_keywords(snapshot["keywords"]),
        }

    def get_recommendations(self) -> dict[str, Any]:
        snapshot = self.refresh()
        return {
            "success": True,
            "items": snapshot["recommendations"],
            "count": len(snapshot["recommendations"]),
        }

    def get_company(self) -> dict[str, Any] | None:
        snapshot = self.refresh()
        return snapshot["company"]

    def get_trends(self) -> list[dict[str, Any]]:
        snapshot = self.refresh()
        return snapshot["live_trends"]

    def get_competitors(self) -> list[dict[str, Any]]:
        snapshot = self.refresh()
        return snapshot["competitor_cards"]

    def get_insights(self) -> list[dict[str, Any]]:
        snapshot = self.refresh()
        return snapshot["insights"]

    def get_opportunities(self) -> list[dict[str, Any]]:
        snapshot = self.refresh()
        return snapshot["opportunities"]

    def get_validation_report(self) -> dict[str, Any]:
        snapshot = self.refresh()
        queries = [
            "Claude",
            "ChatGPT",
            "Gemini",
            "OpenAI",
            "Anthropic",
            "RAG",
            "MCP",
            "Agentic AI",
            "Autonomous Systems",
        ]
        cases = [self._validate_search_case(query, snapshot) for query in queries]
        comparison_cases = [
            self._validate_comparison_case("OpenAI", "Anthropic", snapshot),
            self._validate_comparison_case("Claude", "ChatGPT", snapshot),
            self._validate_comparison_case("Giggso", "OpenAI", snapshot),
            self._validate_comparison_case("Giggso", "Cohere", snapshot),
        ]

        passed_checks: list[str] = []
        failed_checks: list[str] = []
        for case in cases + comparison_cases:
            passed_checks.extend(case.get("passed_checks", []))
            failed_checks.extend(case.get("failed_checks", []))

        overall_score = self._average(
            [case.get("overall_accuracy_score", 0.0) for case in cases + comparison_cases]
        )
        recommended_fixes = self._unique_ordered(
            [fix for case in cases + comparison_cases for fix in case.get("recommended_fixes", [])],
            limit=10,
        )
        return {
            "success": True,
            "report_title": "Industry Intelligence Validation Report",
            "overall_system_accuracy_score": round(overall_score, 1),
            "passed_checks": self._unique_ordered(passed_checks, limit=20),
            "failed_checks": self._unique_ordered(failed_checks, limit=20),
            "recommended_fixes": recommended_fixes,
            "cases": cases,
            "comparison_cases": comparison_cases,
            "generated_at": _NOW().isoformat(),
        }

    def search_intelligence(self, query: str) -> dict[str, Any]:
        query_text = _clean_text(query)
        if not query_text:
            return {
                "success": False,
                "query": "",
                "trend_score": 0,
                "momentum": "Low",
                "growth_score": 0,
                "related_keywords": [],
                "recent_news": [],
                "competitor_mentions": [],
                "executive_summary": "Enter an AI company, model, technology, framework, or keyword to search the industry intelligence layer.",
                "recommendation": "Use a specific query such as Claude, ChatGPT, Gemini, MCP, RAG, or AI Governance.",
                "confidence_score": 0,
                "source_coverage": [],
            }

        snapshot = self.refresh()
        result = self._build_search_intelligence(query_text, snapshot)
        history = db_get_trend_history(query_text)
        return {
            "success": True,
            **result,
            "trend_history": history,
        }

    def compare_intelligence(self, query1: str, query2: str) -> dict[str, Any]:
        left_query = _clean_text(query1)
        right_query = _clean_text(query2)
        if not left_query or not right_query:
            return {
                "success": False,
                "error": "Both q1 and q2 are required.",
                "q1": left_query,
                "q2": right_query,
                "trend_score": 0,
                "momentum": "Low",
                "growth_score": 0,
                "keyword_overlap": [],
                "recent_news": [],
                "strengths": [],
                "weaknesses": [],
                "executive_summary": "Provide two signals to compare.",
            }

        snapshot = self.refresh()
        left = self._build_search_intelligence(left_query, snapshot, persist_history=False)
        right = self._build_search_intelligence(right_query, snapshot, persist_history=False)
        left_type = left.get("query_type") or self.detect_query_type(left_query)
        right_type = right.get("query_type") or self.detect_query_type(right_query)
        left_article_count = _safe_int(left.get("article_count") or left.get("news_count") or len(left.get("recent_news") or []))
        right_article_count = _safe_int(right.get("article_count") or right.get("news_count") or len(right.get("recent_news") or []))
        left_mention_count = _safe_int(left.get("mention_count") or left.get("competitor_mention_count") or len(left.get("competitor_mentions") or []))
        right_mention_count = _safe_int(right.get("mention_count") or right.get("competitor_mention_count") or len(right.get("competitor_mentions") or []))
        left_sources = self._evidence_source_names(
            left.get("source_names") or [],
            left.get("source_coverage") or [],
            [item.get("source", "") for item in left.get("recent_news") or []],
            [item.get("name", "") for item in left.get("competitor_mentions") or []],
        )
        right_sources = self._evidence_source_names(
            right.get("source_names") or [],
            right.get("source_coverage") or [],
            [item.get("source", "") for item in right.get("recent_news") or []],
            [item.get("name", "") for item in right.get("competitor_mentions") or []],
        )
        combined_source_names = self._unique_ordered([*left_sources, *right_sources], limit=12)
        combined_source_timestamps = self._unique_ordered(
            [
                *[item.get("published_date") or item.get("published_at") or item.get("date") for item in left.get("recent_news") or []],
                *[item.get("published_date") or item.get("published_at") or item.get("date") for item in right.get("recent_news") or []],
                *[item.get("last_updated") for item in left.get("competitor_mentions") or []],
                *[item.get("last_updated") for item in right.get("competitor_mentions") or []],
            ],
            limit=12,
        )
        combined_evidence_count = (
            left_article_count
            + right_article_count
            + left_mention_count
            + right_mention_count
            + _safe_int(left.get("rag_match_count") or 0)
            + _safe_int(right.get("rag_match_count") or 0)
        )
        combined_source_count = len(combined_source_names)
        if combined_evidence_count < 3 or combined_source_count < 2:
            return {
                "success": True,
                "q1": left_query,
                "q2": right_query,
                "q1_type": left_type,
                "q2_type": right_type,
                "trend_score": 0,
                "momentum": "Low",
                "growth_score": 0,
                "keyword_overlap": [],
                "recent_news": [],
                "strengths": [],
                "weaknesses": [],
                "competitive_gap_analysis": [],
                "strategic_recommendations": [],
                "executive_action_plan": [],
                "roadmap_30_60_90": {},
                "business_impact_forecast": {},
                "executive_readiness_score": {},
                "board_recommendations": [],
                "recommendations": [],
                "executive_summary": "Insufficient evidence available.",
                "source_count": combined_source_count,
                "evidence_count": combined_evidence_count,
                "article_count": left_article_count + right_article_count,
                "mention_count": left_mention_count + right_mention_count,
                "source_names": combined_source_names,
                "source_timestamps": combined_source_timestamps,
                "confidence_reason": "Insufficient evidence available.",
                "last_updated": _NOW().isoformat(),
                "timestamp": _NOW().isoformat(),
            }
        left_keywords = [self._normalize_overlap_keyword(item) for item in left.get("related_keywords") or []]
        right_keywords = [self._normalize_overlap_keyword(item) for item in right.get("related_keywords") or []]
        left_keywords = [item for item in left_keywords if item]
        right_keywords = [item for item in right_keywords if item]
        overlap = self._comparison_theme_overlap(left_query, right_query, set(left_keywords), set(right_keywords))
        if not overlap:
            fallback_overlap = self._extract_keywords(f"{left_query} {right_query}", minimum=2)
            overlap = self._unique_ordered([self._display_search_keyword(item) for item in fallback_overlap], limit=8)

        trend_score = int(round((_safe_number(left.get("trend_score")) + _safe_number(right.get("trend_score"))) / 2.0))
        growth_score = int(round((_safe_number(left.get("growth_score")) + _safe_number(right.get("growth_score"))) / 2.0))
        momentum = self._trend_momentum_label(trend_score)

        combined_news = self._dedupe_search_items(
            [*left.get("recent_news", []), *right.get("recent_news", [])],
            key_fields=("headline", "source"),
            limit=6,
        )
        strengths = self._comparison_strengths(left_query, right_query, left, right, left_type, right_type)
        weaknesses = self._comparison_weaknesses(left_query, right_query, left, right, left_type, right_type)
        competitive_gap_analysis = self._comparison_gap_analysis(
            left_query=left_query,
            right_query=right_query,
            left=left,
            right=right,
            left_type=left_type,
            right_type=right_type,
            strengths=strengths,
            weaknesses=weaknesses,
        )
        strategic_recommendations = self._comparison_strategic_recommendations(
            left_query=left_query,
            right_query=right_query,
            left=left,
            right=right,
            left_type=left_type,
            right_type=right_type,
            overlap=overlap,
            gap_analysis=competitive_gap_analysis,
        )
        executive_action_plan = self._comparison_action_plan(
            left_query=left_query,
            right_query=right_query,
            gap_analysis=competitive_gap_analysis,
            strategic_recommendations=strategic_recommendations,
        )
        roadmap_30_60_90 = self._comparison_roadmap(
            left_query=left_query,
            right_query=right_query,
            strategic_recommendations=strategic_recommendations,
            action_plan=executive_action_plan,
        )
        business_impact_forecast = self._comparison_business_impact_forecast(
            left=left,
            right=right,
            left_type=left_type,
            right_type=right_type,
            overlap=overlap,
            competitive_gap_analysis=competitive_gap_analysis,
        )
        executive_readiness_score = self._comparison_executive_readiness_score(
            left=left,
            right=right,
            left_type=left_type,
            right_type=right_type,
            overlap=overlap,
            gap_analysis=competitive_gap_analysis,
        )
        board_recommendations = self._comparison_board_recommendations(
            left_query=left_query,
            right_query=right_query,
            gap_analysis=competitive_gap_analysis,
            business_impact_forecast=business_impact_forecast,
            executive_readiness_score=executive_readiness_score,
        )
        executive_summary = self._generate_compare_executive_summary(
            left_query=left_query,
            right_query=right_query,
            left=left,
            right=right,
            overlap=overlap,
            strengths=strengths,
            weaknesses=weaknesses,
        )
        evidence_meta = self._evidence_metadata(
            article_count=left_article_count + right_article_count,
            mention_count=left_mention_count + right_mention_count,
            source_notes=combined_source_names,
            source_timestamps=combined_source_timestamps,
            source_count=combined_source_count,
            recency_score=max(_safe_number(left.get("trend_score"), 0.0), _safe_number(right.get("trend_score"), 0.0)),
            last_updated=_NOW().isoformat(),
        )

        return {
            "success": True,
            "q1": left_query,
            "q2": right_query,
            "q1_type": left_type,
            "q2_type": right_type,
            "trend_score": trend_score,
            "momentum": momentum,
            "growth_score": growth_score,
            "keyword_overlap": overlap,
            "recent_news": combined_news,
            "strengths": strengths,
            "weaknesses": weaknesses,
            "competitive_gap_analysis": competitive_gap_analysis,
            "strategic_recommendations": strategic_recommendations,
            "executive_action_plan": executive_action_plan,
            "roadmap_30_60_90": roadmap_30_60_90,
            "business_impact_forecast": business_impact_forecast,
            "executive_readiness_score": executive_readiness_score,
            "board_recommendations": board_recommendations,
            "recommendations": [
                f"{item['priority']}: {item['initiative']} - {item['business_impact']}"
                for item in strategic_recommendations
                if isinstance(item, dict)
            ],
            "executive_summary": executive_summary,
            "source_count": evidence_meta["source_count"],
            "evidence_count": evidence_meta["evidence_count"],
            "article_count": evidence_meta["article_count"],
            "mention_count": evidence_meta["mention_count"],
            "source_names": evidence_meta["source_names"],
            "evidence_sources": evidence_meta["evidence_sources"],
            "source_timestamps": evidence_meta["source_timestamps"],
            "last_updated": evidence_meta["last_updated"],
            "timestamp": evidence_meta["timestamp"],
            "confidence_reason": evidence_meta["confidence_reason"],
        }

    def analyze_product_impact(self, feature_name: str, feature_description: str) -> dict[str, Any]:
        name = _clean_text(feature_name)
        description = _clean_text(feature_description)
        if not name and not description:
            return {
                "success": False,
                "error": "feature_name and feature_description are required.",
                "feature_name": "",
                "feature_description": "",
                "market_demand_score": 0,
                "enterprise_interest_score": 0,
                "competitive_advantage_score": 0,
                "expected_reach_score": 0,
                "adoption_probability_score": 0,
                "revenue_opportunity_score": 0,
                "strategic_fit_score": 0,
                "risk_score": 0,
                "recommended_launch_priority": "Validate further",
                "launch_priority_level": "Low",
                "rollout_plan": {"30_days": [], "60_days": [], "90_days": []},
            }

        feature_name_text = name or (description[:72] if description else "New feature")
        snapshot = self.refresh()
        now = _NOW()
        result = self._build_product_impact_analysis(feature_name_text, description, snapshot, now)
        return {"success": True, **result}

    def _build_product_impact_analysis(
        self,
        feature_name: str,
        feature_description: str,
        snapshot: dict[str, Any],
        now: datetime,
    ) -> dict[str, Any]:
        feature_blob = " ".join(part for part in [feature_name, feature_description] if part).strip()
        feature_lower = feature_blob.lower()
        feature_keywords = self._unique_ordered(
            [self._display_search_keyword(item) for item in self._extract_keywords(feature_blob, minimum=3)],
            limit=12,
        )

        company = snapshot.get("company") or {}
        trends = snapshot.get("live_trends") or []
        competitors = snapshot.get("competitor_cards") or []
        opportunities = snapshot.get("opportunities") or []
        keywords = snapshot.get("keywords") or []
        insights = snapshot.get("insights") or []
        news = snapshot.get("news") or []

        def score_overlap(text: str, bonus_terms: tuple[str, ...] = ()) -> float:
            haystack = _clean_text(text).lower()
            if not haystack:
                return 0.0
            hits = sum(1 for term in feature_keywords if term.lower() in haystack)
            score = (hits / max(1, len(feature_keywords))) * 100.0 if feature_keywords else 0.0
            if any(term in haystack for term in bonus_terms):
                score += 10.0
            if any(term in haystack for term in ("enterprise", "governance", "security", "compliance", "monitoring", "risk", "agent")):
                score += 8.0
            return max(0.0, min(100.0, score))

        trend_matches: list[dict[str, Any]] = []
        for trend in trends:
            if not isinstance(trend, dict):
                continue
            haystack = " ".join(
                [
                    str(trend.get("trend_name") or ""),
                    str(trend.get("category") or ""),
                    str(trend.get("executive_summary") or ""),
                    " ".join(trend.get("source_notes") or []),
                ]
            )
            match_score = score_overlap(haystack, ("enterprise ai", "governance", "security", "compliance"))
            if match_score <= 0:
                continue
            trend_matches.append(
                {
                    "title": trend.get("trend_name") or "Trend",
                    "summary": trend.get("executive_summary") or trend.get("summary") or "",
                    "detail": f"{_safe_number(trend.get('momentum_score')):.0f} momentum • {_safe_number(trend.get('growth_score')):.0f} growth • {_safe_number(trend.get('source_count')):.0f} sources",
                    "score": round(min(100.0, match_score + _safe_number(trend.get("momentum_score")) * 0.35 + _safe_number(trend.get("growth_score")) * 0.25), 1),
                }
            )
        trend_matches.sort(key=lambda item: item["score"], reverse=True)

        competitor_matches: list[dict[str, Any]] = []
        for competitor in competitors:
            if not isinstance(competitor, dict):
                continue
            haystack = " ".join(
                [
                    str(competitor.get("name") or ""),
                    str(competitor.get("focus_area") or ""),
                    str(competitor.get("activity_summary") or ""),
                    str(competitor.get("strategic_position") or ""),
                    " ".join(competitor.get("source_notes") or []),
                ]
            )
            match_score = score_overlap(haystack, ("enterprise", "governance", "security", "ai", "agent"))
            if match_score <= 0:
                continue
            competitor_matches.append(
                {
                    "title": competitor.get("name") or "Competitor",
                    "summary": competitor.get("activity_summary") or competitor.get("strategic_position") or "",
                    "detail": competitor.get("focus_area") or "",
                    "score": round(min(100.0, match_score + _safe_number(competitor.get("momentum_score")) * 0.4), 1),
                }
            )
        competitor_matches.sort(key=lambda item: item["score"], reverse=True)

        opportunity_matches: list[dict[str, Any]] = []
        for opportunity in opportunities:
            if not isinstance(opportunity, dict):
                continue
            haystack = " ".join(
                [
                    str(opportunity.get("opportunity_name") or ""),
                    str(opportunity.get("trend_name") or ""),
                    str(opportunity.get("summary") or ""),
                    str(opportunity.get("business_value") or ""),
                ]
            )
            match_score = score_overlap(haystack, ("launch", "enterprise", "governance", "security", "compliance"))
            if match_score <= 0:
                continue
            opportunity_matches.append(
                {
                    "title": opportunity.get("opportunity_name") or "Opportunity",
                    "summary": opportunity.get("summary") or "",
                    "detail": opportunity.get("business_value") or "",
                    "score": round(min(100.0, match_score + _safe_number(opportunity.get("opportunity_score")) * 0.3), 1),
                }
            )
        opportunity_matches.sort(key=lambda item: item["score"], reverse=True)

        keyword_blob = " ".join(item.get("keyword", "") for item in keywords if isinstance(item, dict))
        keyword_match_score = score_overlap(keyword_blob, ("governance", "security", "enterprise", "ai", "compliance", "monitoring"))
        company_blob = " ".join(
            [
                str(company.get("market_narrative") or ""),
                str(company.get("strategic_direction") or ""),
                str(company.get("company_summary") or company.get("overview") or ""),
                " ".join(company.get("focus_keywords") or []),
                " ".join(company.get("strategic_themes") or []),
            ]
        )
        company_fit_score = score_overlap(company_blob, ("governance", "security", "enterprise", "compliance", "monitoring"))
        insight_blob = " ".join(
            [
                " ".join(str(item.get("insight_title") or "") for item in insights if isinstance(item, dict)),
                " ".join(str(item.get("recommended_action") or "") for item in insights if isinstance(item, dict)),
            ]
        )
        insight_alignment = score_overlap(insight_blob, ("enterprise", "governance", "security", "compliance"))
        news_alignment = score_overlap(
            " ".join(f"{item.get('headline', '')} {item.get('summary', '')}" for item in news[:8] if isinstance(item, dict)),
            ("enterprise", "governance", "security", "llm", "agent", "rag", "compliance"),
        )

        matched_trend_scores = [item["score"] for item in trend_matches[:5]]
        matched_opportunity_scores = [item["score"] for item in opportunity_matches[:4]]
        matched_competitor_scores = [item["score"] for item in competitor_matches[:4]]
        avg_trend_score = self._average(matched_trend_scores) if matched_trend_scores else 35.0
        avg_opportunity_score = self._average(matched_opportunity_scores) if matched_opportunity_scores else 30.0
        avg_competitor_score = self._average(matched_competitor_scores) if matched_competitor_scores else 30.0

        market_demand_score = round(
            max(
                0.0,
                min(
                    100.0,
                    18.0
                    + (avg_trend_score * 0.42)
                    + (news_alignment * 0.16)
                    + (keyword_match_score * 0.2)
                    + (avg_opportunity_score * 0.12),
                ),
            ),
            1,
        )
        enterprise_interest_score = round(
            max(
                0.0,
                min(
                    100.0,
                    20.0 + (company_fit_score * 0.45) + (insight_alignment * 0.25) + (keyword_match_score * 0.18),
                ),
            ),
            1,
        )
        strategic_fit_score = round(
            max(
                0.0,
                min(
                    100.0,
                    18.0 + (company_fit_score * 0.4) + (avg_opportunity_score * 0.2) + (keyword_match_score * 0.2),
                ),
            ),
            1,
        )
        competitive_advantage_score = round(
            max(
                0.0,
                min(
                    100.0,
                    18.0 + (strategic_fit_score * 0.35) + (avg_trend_score * 0.2) + max(0.0, 70.0 - avg_competitor_score) * 0.2,
                ),
            ),
            1,
        )
        expected_reach_score = round(
            max(
                0.0,
                min(
                    100.0,
                    15.0 + (avg_trend_score * 0.28) + (news_alignment * 0.18) + min(15.0, len(feature_keywords) * 2.0) + min(8.0, len(trend_matches) * 1.2),
                ),
            ),
            1,
        )
        adoption_probability_score = round(
            max(
                0.0,
                min(
                    100.0,
                    10.0 + (enterprise_interest_score * 0.38) + (strategic_fit_score * 0.28) + (competitive_advantage_score * 0.18) + (expected_reach_score * 0.12),
                ),
            ),
            1,
        )
        revenue_opportunity_score = round(
            max(
                0.0,
                min(
                    100.0,
                    12.0 + (market_demand_score * 0.32) + (enterprise_interest_score * 0.24) + (adoption_probability_score * 0.24) + (strategic_fit_score * 0.14),
                ),
            ),
            1,
        )
        risk_anchor = self._average([strategic_fit_score, enterprise_interest_score, market_demand_score, competitive_advantage_score, expected_reach_score]) or 0.0
        competitor_anchor = self._average([avg_competitor_score, market_demand_score, strategic_fit_score]) or 0.0
        risk_components = [
            max(0.0, risk_anchor - strategic_fit_score),
            max(0.0, risk_anchor - enterprise_interest_score),
            max(0.0, avg_competitor_score - competitor_anchor),
            max(0.0, risk_anchor - market_demand_score),
        ]
        risk_score = round(max(0.0, min(100.0, self._average(risk_components) + (15.0 if "launch" in feature_lower and "beta" not in feature_lower else 0.0))), 1)
        launch_readiness_score = round(
            max(
                0.0,
                min(
                    100.0,
                    (market_demand_score * 0.22)
                    + (enterprise_interest_score * 0.2)
                    + (competitive_advantage_score * 0.18)
                    + (expected_reach_score * 0.12)
                    + (adoption_probability_score * 0.2)
                    + (revenue_opportunity_score * 0.1)
                    + (strategic_fit_score * 0.18)
                    - (risk_score * 0.32),
                ),
            ),
            1,
        )

        if launch_readiness_score >= 75 and risk_score < 45:
            recommended_launch_priority = "Launch now"
            launch_priority_level = "High"
        elif launch_readiness_score >= 55:
            recommended_launch_priority = "Pilot first"
            launch_priority_level = "Medium"
        else:
            recommended_launch_priority = "Validate further"
            launch_priority_level = "Low"

        top_trend = trend_matches[0]["title"] if trend_matches else "Enterprise AI"
        top_competitor = competitor_matches[0]["title"] if competitor_matches else "OpenAI"
        top_opportunity = opportunity_matches[0]["title"] if opportunity_matches else "Governed AI Command Center"

        executive_launch_readiness_report = (
            f"{feature_name} maps most strongly to {top_trend}, which suggests market interest is real but should be paired with an enterprise story. "
            f"The clearest competitive context comes from {top_competitor}, so the launch should differentiate on governance, security, and deployment proof. "
            f"If Giggso packages {top_opportunity} into the rollout, the feature can move from concept to a credible enterprise buying motion."
        )
        if launch_priority_level == "High":
            executive_launch_readiness_report += " This feature is ready for a near-term launch with a focused pilot and board-level positioning."
        elif launch_priority_level == "Medium":
            executive_launch_readiness_report += " The feature should launch through a controlled pilot before a broader release."
        else:
            executive_launch_readiness_report += " The feature needs more validation before a full launch."

        executive_verdict = self._build_product_impact_executive_verdict(
            launch_readiness_score=launch_readiness_score,
            risk_score=risk_score,
            market_demand_score=market_demand_score,
            enterprise_fit_score=strategic_fit_score,
            revenue_opportunity_score=revenue_opportunity_score,
            competitive_advantage_score=competitive_advantage_score,
        )
        top_opportunities = self._build_product_impact_opportunities(
            opportunity_matches,
            feature_name=feature_name,
            market_demand_score=market_demand_score,
            revenue_opportunity_score=revenue_opportunity_score,
            enterprise_fit_score=strategic_fit_score,
        )
        top_risks = self._build_product_impact_risks(
            risk_score=risk_score,
            market_demand_score=market_demand_score,
            enterprise_fit_score=strategic_fit_score,
            competitive_advantage_score=competitive_advantage_score,
            launch_readiness_score=launch_readiness_score,
        )
        recommended_next_actions = self._build_product_impact_next_actions(
            verdict=executive_verdict["verdict"],
            feature_name=feature_name,
            market_demand_score=market_demand_score,
            enterprise_fit_score=strategic_fit_score,
            risk_score=risk_score,
            opportunity=top_opportunities[0]["opportunity"] if top_opportunities else top_opportunity,
        )
        final_recommendation = self._build_product_impact_final_recommendation(
            verdict=executive_verdict["verdict"],
            feature_name=feature_name,
            top_opportunity=top_opportunities[0]["opportunity"] if top_opportunities else top_opportunity,
            top_risk=top_risks[0]["risk"] if top_risks else "material execution risk",
        )
        confidence_score = self._build_product_impact_confidence(
            launch_readiness_score=launch_readiness_score,
            risk_score=risk_score,
            market_demand_score=market_demand_score,
            enterprise_fit_score=strategic_fit_score,
            opportunity_count=len(top_opportunities),
            trend_count=len(trend_matches),
            competitor_count=len(competitor_matches),
        )
        executive_verdict["confidence_score"] = confidence_score
        key_scores = {
            "market_demand": market_demand_score,
            "enterprise_fit": strategic_fit_score,
            "revenue_opportunity": revenue_opportunity_score,
            "competitive_advantage": competitive_advantage_score,
            "risk": risk_score,
            "launch_readiness": launch_readiness_score,
        }
        executive_launch_readiness_report = executive_verdict["explanation"]
        launch_priority_reason = (
            f"{executive_verdict['verdict']} because demand is {self._score_label(market_demand_score)}, "
            f"enterprise fit is {self._score_label(strategic_fit_score)}, and risk is {self._risk_label(risk_score)}."
        )

        ml_inputs = self._build_product_impact_ml_inputs(
            market_demand_score=market_demand_score,
            enterprise_fit_score=strategic_fit_score,
            revenue_opportunity_score=revenue_opportunity_score,
            competitive_advantage_score=competitive_advantage_score,
            risk_score=risk_score,
            trend_strength=avg_trend_score,
            competitor_density=avg_competitor_score,
            opportunity_count=len(opportunity_matches),
            market_interest=enterprise_interest_score,
            adoption_probability_score=adoption_probability_score,
            feature_keywords=feature_keywords,
            competitor_matches=competitor_matches,
            trend_matches=trend_matches,
            feature_name=feature_name,
            feature_description=feature_description,
        )
        ml_predictions = product_impact_ml_engine.predict(ml_inputs)
        launch_ml = ml_predictions.get("launch_readiness") or {}
        risk_ml = ml_predictions.get("risk_classification") or {}
        revenue_ml = ml_predictions.get("revenue_opportunity") or {}

        predicted_launch_readiness_score = _safe_number(launch_ml.get("predicted_score"), launch_readiness_score)
        predicted_revenue_opportunity_score = _safe_number(revenue_ml.get("predicted_score"), revenue_opportunity_score)
        risk_probability_score = _safe_number(risk_ml.get("risk_probability"), risk_score / 100.0)
        predicted_risk_score = round(risk_probability_score * 100.0, 1)
        hybrid_launch_readiness_score = round(
            predicted_launch_readiness_score * 0.7 + launch_readiness_score * 0.3,
            1,
        ) if launch_ml else launch_readiness_score
        hybrid_revenue_opportunity_score = round(
            predicted_revenue_opportunity_score * 0.7 + revenue_opportunity_score * 0.3,
            1,
        ) if revenue_ml else revenue_opportunity_score
        hybrid_risk_score = round(
            predicted_risk_score * 0.7 + risk_score * 0.3,
            1,
        ) if risk_ml else risk_score
        prediction_confidence = round(
            self._average(
                [
                    _safe_number(launch_ml.get("confidence_score"), 0.0),
                    _safe_number(risk_ml.get("confidence_score"), 0.0),
                    _safe_number(revenue_ml.get("confidence_score"), 0.0),
                ]
            )
            if ml_predictions.get("available")
            else confidence_score,
            1,
        )
        launch_factor_summary = self._summarize_contributing_factors(launch_ml.get("top_factors") or [])
        risk_factor_summary = self._summarize_contributing_factors(risk_ml.get("top_factors") or [])
        revenue_factor_summary = self._summarize_contributing_factors(revenue_ml.get("top_factors") or [])
        ml_prediction_summary = {
            "launch_readiness": launch_ml,
            "risk_classification": risk_ml,
            "revenue_opportunity": revenue_ml,
        }

        key_scores = {
            "market_demand": market_demand_score,
            "enterprise_fit": strategic_fit_score,
            "revenue_opportunity": hybrid_revenue_opportunity_score,
            "competitive_advantage": competitive_advantage_score,
            "risk": hybrid_risk_score,
            "launch_readiness": hybrid_launch_readiness_score,
        }
        if ml_predictions.get("available"):
            launch_priority_reason = (
                f"{ml_prediction_summary['launch_readiness'].get('predicted_score', launch_readiness_score):.0f}/100 predicted launch readiness, "
                f"{ml_prediction_summary['risk_classification'].get('predicted_label', 'Medium Risk')} risk, and "
                f"{ml_prediction_summary['revenue_opportunity'].get('predicted_score', revenue_opportunity_score):.0f}/100 revenue opportunity point to a {self._score_label(hybrid_launch_readiness_score)} launch case."
            )
            executive_verdict = self._build_product_impact_executive_verdict(
                launch_readiness_score=hybrid_launch_readiness_score,
                risk_score=hybrid_risk_score,
                market_demand_score=market_demand_score,
                enterprise_fit_score=strategic_fit_score,
                revenue_opportunity_score=hybrid_revenue_opportunity_score,
                competitive_advantage_score=competitive_advantage_score,
            )
            executive_verdict["prediction_summary"] = ml_prediction_summary
            executive_verdict["top_contributing_factors"] = {
                "launch_readiness": launch_factor_summary,
                "risk_classification": risk_factor_summary,
                "revenue_opportunity": revenue_factor_summary,
            }
            confidence_score = prediction_confidence
            executive_verdict["confidence_score"] = confidence_score
            recommended_priority = executive_verdict["verdict"]
        else:
            recommended_priority = executive_verdict["verdict"]
            executive_verdict["prediction_summary"] = ml_prediction_summary
            executive_verdict["top_contributing_factors"] = {
                "launch_readiness": launch_factor_summary,
                "risk_classification": risk_factor_summary,
                "revenue_opportunity": revenue_factor_summary,
            }
            executive_verdict["confidence_score"] = confidence_score

        rollout_plan = {
            "30_days": [
                {
                    "objective": f"Validate {feature_name} with 3-5 enterprise design partners.",
                    "expected_impact": "Confirms the use case, language, and buyer pain points before launch.",
                    "priority": "High",
                },
                {
                    "objective": "Define governance, security, and compliance guardrails for the feature.",
                    "expected_impact": "Reduces enterprise launch risk and strengthens trust.",
                    "priority": "High",
                },
            ],
            "60_days": [
                {
                    "objective": f"Release a controlled beta for {feature_name} tied to the strongest market opportunity.",
                    "expected_impact": "Turns initial interest into product feedback and pipeline evidence.",
                    "priority": "High",
                },
                {
                    "objective": "Build sales and customer success enablement around the launch narrative.",
                    "expected_impact": "Improves internal readiness and message consistency.",
                    "priority": "Medium",
                },
            ],
            "90_days": [
                {
                    "objective": "Scale the launch with customer proof, pricing, and case-study messaging.",
                    "expected_impact": "Converts the feature into a repeatable revenue motion.",
                    "priority": "High",
                },
                {
                    "objective": "Track adoption, revenue contribution, and competitor displacement signals.",
                    "expected_impact": "Shows whether the launch is creating measurable market lift.",
                    "priority": "Medium",
                },
            ],
        }

        return {
            "feature_name": feature_name,
            "feature_description": feature_description,
            "market_demand_score": market_demand_score,
            "enterprise_interest_score": enterprise_interest_score,
            "competitive_advantage_score": competitive_advantage_score,
            "expected_reach_score": expected_reach_score,
            "adoption_probability_score": adoption_probability_score,
            "revenue_opportunity_score": hybrid_revenue_opportunity_score,
            "strategic_fit_score": strategic_fit_score,
            "reach_score": expected_reach_score,
            "adoption_score": adoption_probability_score,
            "enterprise_fit_score": strategic_fit_score,
            "risk_score": hybrid_risk_score,
            "overall_launch_readiness_score": hybrid_launch_readiness_score,
            "predicted_launch_readiness_score": predicted_launch_readiness_score,
            "predicted_revenue_opportunity_score": predicted_revenue_opportunity_score,
            "predicted_risk_probability": risk_probability_score,
            "predicted_risk_score": predicted_risk_score,
            "risk_classification_label": risk_ml.get("predicted_label") or self._risk_band_from_probability(risk_probability_score),
            "recommended_launch_priority": recommended_priority,
            "launch_priority_level": launch_priority_level,
            "launch_priority_reason": launch_priority_reason,
            "executive_launch_readiness_report": executive_launch_readiness_report,
            "executive_verdict": executive_verdict,
            "confidence_score": confidence_score,
            "key_scores": key_scores,
            "heuristic_scores": {
                "market_demand": market_demand_score,
                "enterprise_fit": strategic_fit_score,
                "revenue_opportunity": revenue_opportunity_score,
                "competitive_advantage": competitive_advantage_score,
                "risk": risk_score,
                "launch_readiness": launch_readiness_score,
            },
            "ml_predictions": ml_prediction_summary,
            "top_opportunities": top_opportunities,
            "top_risks": top_risks,
            "recommended_next_actions": recommended_next_actions,
            "final_recommendation": final_recommendation,
            "top_contributing_factors": {
                "launch_readiness": launch_factor_summary,
                "risk_classification": risk_factor_summary,
                "revenue_opportunity": revenue_factor_summary,
            },
            "prediction_confidence": confidence_score,
            "scoring_method": "ML/analytics-based",
            "llm_used_for_score": False,
            "score_features": ml_inputs,
            "supporting_trends": trend_matches[:5],
            "supporting_competitors": competitor_matches[:5],
            "supporting_opportunities": opportunity_matches[:5],
            "supporting_keywords": feature_keywords[:10],
            "matched_trend_count": len(trend_matches),
            "matched_competitor_count": len(competitor_matches),
            "matched_opportunity_count": len(opportunity_matches),
            "rollout_plan": rollout_plan,
            "report_type": "product-impact",
            "context_type": "product-impact",
            "generated_at": now.isoformat(),
        }

    def _score_label(self, score: float) -> str:
        if score >= 75:
            return "strong"
        if score >= 50:
            return "moderate"
        return "early"

    def _risk_label(self, score: float) -> str:
        if score < 35:
            return "low"
        if score < 55:
            return "manageable"
        return "elevated"

    def _risk_band_from_probability(self, probability: float) -> str:
        if probability < 0.35:
            return "Low Risk"
        if probability < 0.65:
            return "Medium Risk"
        return "High Risk"

    def _summarize_contributing_factors(self, factors: list[dict[str, Any]] | list[Any], limit: int = 3) -> list[dict[str, Any]]:
        summary: list[dict[str, Any]] = []
        for item in (factors or [])[:limit]:
            if not isinstance(item, dict):
                continue
            summary.append(
                {
                    "factor": str(item.get("factor") or item.get("name") or "Factor"),
                    "impact": _safe_number(item.get("impact") or item.get("score") or 0.0),
                    "signed_impact": _safe_number(item.get("signed_impact") or item.get("signed_delta") or item.get("impact") or 0.0),
                    "signed_display": str(item.get("signed_display") or ""),
                    "direction": str(item.get("direction") or item.get("contribution_direction") or "Positive"),
                    "contribution_direction": str(item.get("contribution_direction") or item.get("direction") or "Positive"),
                    "business_explanation": str(item.get("business_explanation") or ""),
                    "model": str(item.get("model") or ""),
                }
            )
        return summary

    def _build_product_impact_ml_inputs(
        self,
        *,
        market_demand_score: float,
        enterprise_fit_score: float,
        revenue_opportunity_score: float,
        competitive_advantage_score: float,
        risk_score: float,
        trend_strength: float,
        competitor_density: float,
        opportunity_count: int,
        market_interest: float,
        adoption_probability_score: float,
        feature_keywords: list[str],
        competitor_matches: list[dict[str, Any]],
        trend_matches: list[dict[str, Any]],
        feature_name: str,
        feature_description: str,
    ) -> dict[str, Any]:
        compliance_complexity = max(
            0.0,
            min(
                100.0,
                (risk_score * 0.32)
                + max(0.0, 58.0 - enterprise_fit_score) * 0.7
                + len(feature_keywords) * 2.0
                + len(trend_matches) * 1.4,
            ),
        )
        security_risk_anchor = self._average([risk_score, market_demand_score, competitor_density]) or 0.0
        security_risk = max(
            0.0,
            min(
                100.0,
                (risk_score * 0.42) + max(0.0, 100.0 - security_risk_anchor) * 0.55 + len(competitor_matches) * 2.0,
            ),
        )
        adoption_anchor = self._average([market_interest, adoption_probability_score, trend_strength]) or 0.0
        adoption_difficulty = max(
            0.0,
            min(
                100.0,
                100.0 - (market_interest * 0.45) - (adoption_probability_score * 0.3) + max(0.0, 100.0 - adoption_anchor) * 0.25,
            ),
        )
        integration_anchor = self._average([enterprise_fit_score, market_demand_score, adoption_probability_score]) or 0.0
        integration_complexity = max(
            0.0,
            min(
                100.0,
                (len(feature_keywords) * 3.0)
                + len(feature_description.split()) * 0.05
                + max(0.0, 100.0 - integration_anchor) * 0.45,
            ),
        )
        market_competition = max(
            0.0,
            min(
                100.0,
                (competitor_density * 0.75) + max(0.0, 50.0 - competitive_advantage_score) * 0.4 + len(competitor_matches) * 2.5,
            ),
        )

        return {
            "market_demand": market_demand_score,
            "enterprise_fit": enterprise_fit_score,
            "revenue_opportunity": revenue_opportunity_score,
            "competitive_advantage": competitive_advantage_score,
            "risk_score": risk_score,
            "trend_strength": trend_strength,
            "competitor_density": competitor_density,
            "opportunity_count": float(opportunity_count),
            "compliance_complexity": compliance_complexity,
            "security_risk": security_risk,
            "adoption_difficulty": adoption_difficulty,
            "integration_complexity": integration_complexity,
            "market_competition": market_competition,
            "adoption_score": adoption_probability_score,
            "feature_name": feature_name,
            "feature_description": feature_description,
        }

    def _build_product_impact_executive_verdict(
        self,
        *,
        launch_readiness_score: float,
        risk_score: float,
        market_demand_score: float,
        enterprise_fit_score: float,
        revenue_opportunity_score: float,
        competitive_advantage_score: float,
    ) -> dict[str, Any]:
        if launch_readiness_score >= 75 and risk_score < 45:
            verdict = "Build Now"
        elif launch_readiness_score >= 55:
            verdict = "Pilot First"
        elif launch_readiness_score >= 35:
            verdict = "Validate First"
        else:
            verdict = "Do Not Proceed"

        explanation = (
            f"{verdict} - launch readiness is {launch_readiness_score:.0f}/100, with demand at {market_demand_score:.0f}/100 and enterprise fit at {enterprise_fit_score:.0f}/100. "
            f"Revenue opportunity is {revenue_opportunity_score:.0f}/100, while competitive advantage is {competitive_advantage_score:.0f}/100 and risk is {risk_score:.0f}/100."
        )
        return {
            "verdict": verdict,
            "confidence_score": self._build_product_impact_confidence(
                launch_readiness_score=launch_readiness_score,
                risk_score=risk_score,
                market_demand_score=market_demand_score,
                enterprise_fit_score=enterprise_fit_score,
                opportunity_count=0,
                trend_count=0,
                competitor_count=0,
            ),
            "explanation": explanation,
        }

    def _build_product_impact_confidence(
        self,
        *,
        launch_readiness_score: float,
        risk_score: float,
        market_demand_score: float,
        enterprise_fit_score: float,
        opportunity_count: int,
        trend_count: int,
        competitor_count: int,
    ) -> int:
        signal_strength = (
            launch_readiness_score * 0.35
            + market_demand_score * 0.2
            + enterprise_fit_score * 0.2
            + max(0.0, 100.0 - risk_score) * 0.15
            + min(15.0, (opportunity_count + trend_count + competitor_count) * 1.5)
        )
        return int(max(35, min(95, round(signal_strength))))

    def _build_product_impact_opportunities(
        self,
        opportunity_matches: list[dict[str, Any]],
        *,
        feature_name: str,
        market_demand_score: float,
        revenue_opportunity_score: float,
        enterprise_fit_score: float,
    ) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for opportunity in opportunity_matches[:3]:
            title = str(opportunity.get("title") or "Opportunity").strip()
            summary = str(opportunity.get("summary") or opportunity.get("detail") or "").strip()
            impact = summary or (
                f"Supports {feature_name} by linking enterprise fit and revenue motion."
                if enterprise_fit_score >= 60
                else f"Creates near-term commercial pull if the team proves demand."
            )
            items.append(
                {
                    "opportunity": title,
                    "business_impact": impact,
                }
            )
        if not items:
            items = [
                {
                    "opportunity": f"Package {feature_name} around a clear buyer pain.",
                    "business_impact": f"Improves launch odds by turning a feature into a value-led story when demand is {self._score_label(market_demand_score)}.",
                },
                {
                    "opportunity": "Use enterprise-fit positioning as the default narrative.",
                    "business_impact": f"Strengthens conversion if revenue opportunity stays at {revenue_opportunity_score:.0f}/100 or higher.",
                },
            ]
        return items[:3]

    def _build_product_impact_risks(
        self,
        *,
        risk_score: float,
        market_demand_score: float,
        enterprise_fit_score: float,
        competitive_advantage_score: float,
        launch_readiness_score: float,
    ) -> list[dict[str, Any]]:
        risks: list[dict[str, Any]] = []
        if market_demand_score < 60:
            risks.append(
                {
                    "risk": "Market demand is still forming.",
                    "mitigation": "Run a tight pilot with design partners before committing to broad build investment.",
                }
            )
        if enterprise_fit_score < 60:
            risks.append(
                {
                    "risk": "Enterprise fit is not yet strong enough for an easy sale.",
                    "mitigation": "Sharpen the use case, buyer persona, and proof points before launch.",
                }
            )
        if competitive_advantage_score < 55:
            risks.append(
                {
                    "risk": "Differentiation may be too shallow to defend the launch.",
                    "mitigation": "Lead with one hard-to-copy workflow or control advantage.",
                }
            )
        if risk_score >= 55 or launch_readiness_score < 50:
            risks.append(
                {
                    "risk": "Execution risk could outweigh the early upside.",
                    "mitigation": "Delay scale-up until the team has clearer evidence on demand and fit.",
                }
            )
        if not risks:
            risks = [
                {
                    "risk": "The main risk is overbuilding before there is a validated customer pull.",
                    "mitigation": "Keep the launch narrow and use a pilot to confirm urgency.",
                }
            ]
        return risks[:3]

    def _build_product_impact_next_actions(
        self,
        *,
        verdict: str,
        feature_name: str,
        market_demand_score: float,
        enterprise_fit_score: float,
        risk_score: float,
        opportunity: str,
    ) -> dict[str, list[str]]:
        immediate = [
            f"Validate {feature_name} with 3-5 target users or buyers.",
            "Confirm the core problem, buyer, and success metric before more build work.",
        ]
        short_term = [
            f"Turn {opportunity} into a one-page pilot brief and pricing hypothesis.",
            "Align product, sales, and customer success on the same launch story.",
        ]
        launch_actions = [
            "Launch a controlled release only after the pilot shows repeatable pull.",
            "Track adoption, conversion, and competitive displacement from day one.",
        ]

        if verdict == "Build Now":
            immediate[0] = f"Lock the launch scope for {feature_name} and assign an owner."
            short_term[0] = "Prepare the release plan, enablement, and customer proof package."
            launch_actions[0] = "Ship with a focused launch and measure revenue impact within 60-90 days."
        elif verdict == "Do Not Proceed":
            immediate[0] = f"Pause build investment on {feature_name} until the signal improves."
            short_term[0] = "Reframe the concept and revisit the buyer problem before re-scoping."
            launch_actions[0] = "Do not launch until demand and fit move out of the danger zone."
        elif risk_score >= 55:
            launch_actions[0] = "Keep the launch gated until risk drops and the pilot proves value."

        if market_demand_score < 50:
            immediate.append("Test the demand story with a small customer interview set.")
        if enterprise_fit_score < 50:
            short_term.append("Rewrite positioning around enterprise outcomes rather than features.")
        if risk_score < 35:
            launch_actions.append("Move faster on launch once the minimum governance checks are complete.")

        return {
            "immediate_actions": immediate[:3],
            "short_term_actions": short_term[:3],
            "launch_actions": launch_actions[:3],
        }

    def _build_product_impact_final_recommendation(
        self,
        *,
        verdict: str,
        feature_name: str,
        top_opportunity: str,
        top_risk: str,
    ) -> str:
        if verdict == "Build Now":
            return f"Build {feature_name} now and launch it with a narrow, high-signal pilot anchored on {top_opportunity}."
        if verdict == "Pilot First":
            return f"Run a pilot for {feature_name} first so the team can validate demand and reduce {top_risk} before scaling."
        if verdict == "Validate First":
            return f"Validate {feature_name} before building further, with the main goal of proving demand and de-risking {top_risk}."
        return f"Do not proceed with {feature_name} yet; the data points to more validation before any launch commitment."

    def _build_snapshot(self, now: datetime) -> dict[str, Any]:
        company = self._collect_company_signals(now)
        linkedin = self._collect_linkedin_intelligence(company, now)
        news = self._collect_news_intelligence(now)
        competitor_signals = self._collect_competitor_signals(now)
        live_trends = self._build_live_trends(company, linkedin, news, competitor_signals, now)
        keywords = self._build_keywords(company, linkedin, news, competitor_signals, live_trends, now)
        recommendations = self._build_recommendations(live_trends, linkedin, competitor_signals, now)
        competitor_cards = self._build_competitor_cards(company, linkedin, news, competitor_signals, live_trends, keywords, now)
        insights = self._build_insights(company, linkedin, news, competitor_cards, live_trends, now)
        company_row = self._build_company_row(company, linkedin, keywords, now)
        company_signals = {
            "company_name": COMPANY_NAME,
            "website": COMPANY_WEBSITE,
            "linkedin_url": COMPANY_LINKEDIN,
            "positioning": company_row["market_positioning"],
            "core_services": company_row["core_focus_areas"],
            "strategic_themes": company_row["strategic_themes"],
            "focus_keywords": company_row["focus_keywords"],
            "product_messaging": company_row["content_themes"],
            "source_notes": company_row["source_notes"],
            "last_updated": company_row["last_updated"].isoformat() if isinstance(company_row["last_updated"], datetime) else None,
        }
        opportunity_snapshot = {
            "company": company_row,
            "company_signals": company_signals,
            "linkedin": linkedin,
            "linkedin_posts": linkedin.get("posts", []),
            "linkedin_themes": linkedin.get("themes", {}),
            "news": news,
            "competitor_signals": competitor_signals,
            "live_trends": live_trends,
            "keywords": keywords,
            "recommendations": recommendations,
            "competitor_cards": competitor_cards,
            "insights": insights,
        }
        opportunities = self._build_opportunities(company, linkedin, news, competitor_cards, live_trends, keywords, opportunity_snapshot, now)
        report = self._build_report(live_trends, competitor_cards, insights, opportunities, recommendations, now)
        snapshot = {
            "company": company_row,
            "company_signals": company_signals,
            "linkedin": linkedin,
            "linkedin_posts": linkedin.get("posts", []),
            "linkedin_themes": linkedin.get("themes", {}),
            "news": news,
            "competitor_signals": competitor_signals,
            "live_trends": live_trends,
            "keywords": keywords,
            "recommendations": recommendations,
            "competitor_cards": competitor_cards,
            "insights": insights,
            "opportunities": opportunities,
            "report": report,
            "documents": self._build_rag_documents(company_signals, linkedin, news, competitor_signals, live_trends, insights, recommendations, opportunities, now),
        }
        self._capture_trend_history_snapshot(snapshot, now)
        return snapshot

    def _collect_company_signals(self, now: datetime) -> dict[str, Any]:
        source_items: list[dict[str, Any]] = []
        source_notes: list[str] = []
        text_blobs: list[str] = []

        for url in GIGGSO_PAGES:
            page = self._fetch_page(url)
            if page:
                source_items.append(page)
                text_blobs.append(page["content"])
                if page.get("summary"):
                    source_notes.append(page["summary"])

        bing_results = self._bing_search("Giggso AI governance enterprise AI security", site="giggso.com", limit=8)
        source_items.extend(bing_results)
        text_blobs.extend(item["content"] for item in bing_results if item.get("content"))
        for item in bing_results:
            if item.get("snippet"):
                source_notes.append(item["snippet"])

        combined_text = " ".join(text_blobs)
        keywords = self._extract_keywords(combined_text, minimum=8)
        focus_keywords = self._prioritize_keywords(
            keywords,
            preferred=[
                "ai governance",
                "ai security",
                "enterprise ai",
                "agentic ai",
                "llm security",
                "model monitoring",
                "ai compliance",
                "ai risk",
                "trustworthy ai",
                "shadow ai",
            ],
            limit=10,
        )
        strategic_themes = self._unique_ordered(
            [
                "Move AI from pilot to production",
                "Governance-first enterprise AI execution",
                "AI security and compliance controls",
                "Production monitoring and observability",
                "Trustworthy AI for regulated enterprises",
                "Secure agentic workflows",
            ]
            + self._sentences_to_phrases(source_notes),
            limit=8,
        )
        core_focus_areas = self._unique_ordered(
            [
                "AI Governance",
                "AI Security",
                "Enterprise AI",
                "Agentic AI",
                "LLM Security",
                "Model Monitoring",
                "AI Compliance",
                "AI Risk",
            ],
            limit=8,
        )
        product_messaging = self._unique_ordered(
            [
                "Move your AI from pilot to production",
                "Safe AI is fast AI",
                "Governance becomes a competitive advantage",
                "Secure, monitor, and optimize AI systems before vulnerabilities become business risks",
                "AI only creates value when it runs securely, at scale, and under governance",
            ]
            + self._sentences_to_phrases(source_notes),
            limit=8,
        )
        positioning = (
            "Giggso is a governance-first enterprise AI partner helping organizations move from AI pilots to secure, compliant production systems."
        )
        overview = (
            "Public signals show Giggso positioning around AI strategy, security, transformation, and data engineering, with a clear focus on governance, compliance, and production readiness."
        )
        company_size = self._infer_company_scale(source_notes)
        return {
            "company_name": COMPANY_NAME,
            "website": COMPANY_WEBSITE,
            "linkedin_url": COMPANY_LINKEDIN,
            "headquarters": "Troy, Michigan",
            "founded_year": 2017,
            "company_size": company_size,
            "overview": overview,
            "core_focus_areas": core_focus_areas,
            "industry_positioning": positioning,
            "strategic_themes": strategic_themes,
            "source_notes": self._unique_ordered(source_notes, limit=12),
            "recent_strategic_themes": strategic_themes[:6],
            "focus_keywords": focus_keywords,
            "market_positioning": "Governance-first enterprise AI platform and services partner.",
            "content_themes": product_messaging[:6],
            "company_summary": overview,
            "strategic_direction": "Expand governance, security, and monitoring across enterprise AI deployments and regulated buyers.",
            "market_narrative": "The market is rewarding vendors that can prove AI is safe, compliant, observable, and ready for production scale.",
            "last_updated": now,
            "created_at": now,
            "updated_at": now,
        }

    def _collect_linkedin_intelligence(self, company: dict[str, Any], now: datetime) -> dict[str, Any]:
        source_notes: list[str] = []
        source_coverage: list[str] = []
        posts: list[dict[str, Any]] = []
        snippets: list[str] = []

        apify_payload: dict[str, Any] | None = None
        apify_token = os.getenv("APIFY_API_TOKEN", "").strip()
        if apify_token:
            apify_payload, apify_error = self._fetch_apify_linkedin_data(apify_token)
            if apify_payload:
                posts = apify_payload.get("posts", [])
                snippets.extend(apify_payload.get("snippets", []))
                source_notes.extend(apify_payload.get("source_notes", []))
                source_coverage.append("Apify LinkedIn live")
            else:
                source_notes.append(f"Apify fetch failed: {apify_error}")

        if not posts:
            cached_posts = self._get_cached_linkedin_posts(limit=LINKEDIN_MAX_POSTS)
            if cached_posts:
                posts = cached_posts
                snippets.extend(item.get("content", "") for item in cached_posts)
                source_notes.append("Using stored LinkedIn posts cache.")
                source_coverage.append("Stored LinkedIn cache")

        if not posts:
            bing_posts = self._build_bing_linkedin_fallback(company, now)
            if bing_posts:
                posts = bing_posts
                snippets.extend(item.get("text", "") for item in bing_posts)
                source_notes.append("Using Bing snippet fallback for LinkedIn theme extraction.")
                source_coverage.append("Bing snippet fallback")

        if not posts:
            posts = self._build_linkedin_posts_fallback(company, snippets, now)
            source_notes.append("Using demo LinkedIn fallback because all live sources failed.")
            source_coverage.append("Demo LinkedIn fallback")

        if not source_coverage:
            source_coverage.append("Demo LinkedIn fallback")

        combined = " ".join(
            snippets
            + [item.get("text", "") for item in posts]
            + company.get("content_themes", [])
            + company.get("strategic_themes", [])
        )
        keywords = Counter(self._extract_keywords(combined, minimum=8))
        ranked_keywords = [{"keyword": item[0], "count": item[1]} for item in keywords.most_common(10)]
        preferred_topics = [
            "AI Governance",
            "Agentic AI",
            "LLM Security",
            "Model Monitoring",
            "AI Compliance",
            "AI Risk",
            "Enterprise AI",
            "Trustworthy AI",
            "Shadow AI",
        ]
        top_theme = next(
            (
                topic
                for topic in preferred_topics
                if topic.lower() in combined.lower()
                or any(topic.lower().replace(" ", "") in item["keyword"].replace(" ", "") for item in ranked_keywords)
            ),
            self._normalize_topic_name(ranked_keywords[0]["keyword"]) if ranked_keywords else "AI Governance",
        )
        emerging_theme = next(
            (
                topic
                for topic in preferred_topics[1:]
                if topic.lower() in combined.lower()
                or any(topic.lower().replace(" ", "") in item["keyword"].replace(" ", "") for item in ranked_keywords[1:])
            ),
            self._normalize_topic_name(ranked_keywords[1]["keyword"]) if len(ranked_keywords) > 1 else "Agentic AI",
        )
        trend_frequency = {self._normalize_topic_name(item["keyword"]): item["count"] for item in ranked_keywords}
        strategic_narrative = (
            f"Giggso's public social signals emphasize {top_theme.lower()}, with growing attention on {emerging_theme.lower()} and enterprise readiness."
        )
        source_label = source_coverage[0]
        if source_label == "Apify LinkedIn live":
            source_status = "apify"
        elif source_label == "Stored LinkedIn cache":
            source_status = "cache"
        elif source_label == "Bing snippet fallback":
            source_status = "bing"
        else:
            source_status = "fallback"

        normalized_posts = [self._normalize_linkedin_post(item, index=index + 1, source_label=source_label, now=now) for index, item in enumerate(posts[:LINKEDIN_MAX_POSTS])]
        self._persist_linkedin_posts(normalized_posts, source_label=source_label)
        return {
            "top_theme": top_theme,
            "emerging_theme": emerging_theme,
            "keyword_ranking": ranked_keywords,
            "trend_frequency": trend_frequency,
            "strategic_narrative": strategic_narrative,
            "source_status": source_status,
            "source_label": source_label,
            "source_coverage": source_coverage,
            "source_notes": self._unique_ordered(source_notes, limit=10),
            "posts": normalized_posts,
            "themes": {
                "top_theme": top_theme,
                "emerging_theme": emerging_theme,
                "keyword_ranking": ranked_keywords,
                "strategic_narrative": strategic_narrative,
                "trend_frequency": trend_frequency,
                "source_label": source_label,
                "source_status": source_status,
                "source_coverage": source_coverage,
            },
            "last_updated": now.isoformat(),
        }

    def _fetch_apify_linkedin_data(self, token: str) -> tuple[dict[str, Any] | None, str | None]:
        actor_candidates = [
            os.getenv("APIFY_LINKEDIN_ACTOR_ID", "").strip(),
            os.getenv("APIFY_LINKEDIN_ACTOR", "").strip(),
            "getdataforme/linkedin-company-posts-scraper",
            "apimaestro/linkedin-company-posts",
        ]
        actor_candidates = [actor for actor in actor_candidates if actor]
        if not actor_candidates:
            return None, "APIFY_LINKEDIN_ACTOR_ID is not configured"

        payload = {
            "startUrls": [{"url": COMPANY_LINKEDIN}],
            "maxItems": LINKEDIN_MAX_POSTS,
            "proxyConfiguration": {"useApifyProxy": True},
        }
        last_error: str | None = None
        data = None
        for actor_id in actor_candidates:
            actor_ref = actor_id.replace("/", "~")
            run_url = f"https://api.apify.com/v2/acts/{actor_ref}/run-sync-get-dataset-items"
            try:
                response = self.session.post(
                    run_url,
                    params={"token": token, "clean": "true"},
                    json=payload,
                    timeout=8,
                )
                response.raise_for_status()
                data = response.json()
                last_error = None
                break
            except Exception as exc:
                last_error = str(exc)
                continue

        if data is None:
            return None, last_error or "Apify request failed"

        if isinstance(data, dict):
            items = data.get("items") or data.get("data") or data.get("datasetItems") or []
        else:
            items = data

        if not isinstance(items, list):
            return None, "Apify did not return a dataset item list"

        posts: list[dict[str, Any]] = []
        snippets: list[str] = []
        source_notes: list[str] = []
        for index, item in enumerate(items[:LINKEDIN_MAX_POSTS], start=1):
            text = _clean_text(
                item.get("text")
                or item.get("content")
                or item.get("description")
                or item.get("postText")
                or item.get("title")
                or item.get("commentary")
            )
            if not text:
                continue
            post = {
                "post_id": _clean_text(item.get("id") or item.get("urn") or f"apify-{index}"),
                "content": text,
                "text": text,
                "title": _clean_text(item.get("title") or text[:120]),
                "linkedin_url": _clean_text(item.get("url") or item.get("postUrl") or item.get("link") or COMPANY_LINKEDIN),
                "published_date": _parse_datetime(item.get("publishedAt") or item.get("date") or item.get("createdAt")),
                "engagement": {
                    "reactions": _safe_int(item.get("reactions") or item.get("reactionCount") or item.get("likes") or item.get("likeCount")),
                    "comments": _safe_int(item.get("comments") or item.get("commentCount")),
                    "shares": _safe_int(item.get("shares") or item.get("shareCount")),
                },
                "reactions": _safe_int(item.get("reactions") or item.get("reactionCount") or item.get("likes") or item.get("likeCount")),
                "comments": _safe_int(item.get("comments") or item.get("commentCount")),
                "shares": _safe_int(item.get("shares") or item.get("shareCount")),
                "author": _clean_text(
                    item.get("author")
                    or item.get("actor")
                    or item.get("owner")
                    or item.get("companyName")
                    or COMPANY_NAME
                ),
                "source": "Apify LinkedIn live",
            }
            posts.append(post)
            snippets.append(text)
            source_notes.append(f"Apify post: {text[:120]}")

        if not posts:
            return None, "Apify returned no usable LinkedIn posts"

        themes = self._derive_linkedin_themes(posts, snippets)
        return {
            "posts": posts,
            "snippets": snippets,
            "source_notes": source_notes,
            "themes": themes,
        }, None

    def _get_cached_linkedin_posts(self, limit: int = 10) -> list[dict[str, Any]]:
        session = get_db_session()
        try:
            rows = (
                session.query(LinkedInPostRecord)
                .filter(LinkedInPostRecord.user_id == 0)
                .order_by(LinkedInPostRecord.created_at.desc(), LinkedInPostRecord.id.desc())
                .limit(limit)
                .all()
            )
            posts: list[dict[str, Any]] = []
            for row in rows:
                payload = row.payload or {}
                posts.append(
                    {
                        "post_id": _clean_text(payload.get("post_id") or f"cached-{row.id}"),
                        "content": _clean_text(payload.get("content") or row.post_text),
                        "text": _clean_text(payload.get("content") or row.post_text),
                        "linkedin_url": _clean_text(payload.get("linkedin_url") or payload.get("url") or COMPANY_LINKEDIN),
                        "published_date": _parse_datetime(payload.get("published_date") or payload.get("published_at") or row.created_at),
                        "engagement": {
                            "reactions": _safe_int(payload.get("reactions") or payload.get("likes")),
                            "comments": _safe_int(payload.get("comments")),
                            "shares": _safe_int(payload.get("shares")),
                        },
                        "reactions": _safe_int(payload.get("reactions") or payload.get("likes")),
                        "comments": _safe_int(payload.get("comments")),
                        "shares": _safe_int(payload.get("shares")),
                        "author": _clean_text(payload.get("author") or COMPANY_NAME),
                        "source": "Stored LinkedIn cache",
                    }
                )
            return posts
        finally:
            session.close()

    def _persist_linkedin_posts(self, posts: list[dict[str, Any]], source_label: str) -> None:
        session = get_db_session()
        try:
            session.query(LinkedInPostRecord).filter(LinkedInPostRecord.user_id == 0).delete()
            for post in posts:
                published = post.get("published_date")
                if not isinstance(published, datetime):
                    published = _parse_datetime(published) or _NOW()
                payload = {
                    "post_id": post.get("post_id"),
                    "content": post.get("content") or post.get("text") or "",
                    "linkedin_url": post.get("linkedin_url") or COMPANY_LINKEDIN,
                    "published_date": published.isoformat(),
                    "engagement": post.get("engagement") or {},
                    "reactions": post.get("reactions") or 0,
                    "comments": post.get("comments") or 0,
                    "shares": post.get("shares") or 0,
                    "author": post.get("author") or COMPANY_NAME,
                    "source": source_label,
                }
                session.add(
                    LinkedInPostRecord(
                        user_id=0,
                        analysis_id=None,
                        title=_clean_text(post.get("title") or (post.get("content") or "")[:120]),
                        post_text=_clean_text(post.get("content") or post.get("text") or ""),
                        payload=payload,
                        created_at=published,
                    )
                )
            session.commit()
        except Exception as exc:
            session.rollback()
            logger.warning("Failed to persist LinkedIn cache: %s", exc)
        finally:
            session.close()

    def _normalize_linkedin_post(self, item: dict[str, Any], index: int, source_label: str, now: datetime) -> dict[str, Any]:
        published = item.get("published_date") or item.get("published_at") or now
        if not isinstance(published, datetime):
            published = _parse_datetime(published) or now
        reactions = _safe_int(item.get("reactions") or item.get("engagement", {}).get("reactions") or item.get("engagement", {}).get("likes"))
        comments = _safe_int(item.get("comments") or item.get("engagement", {}).get("comments"))
        shares = _safe_int(item.get("shares") or item.get("engagement", {}).get("shares"))
        return {
            "post_id": _clean_text(item.get("post_id") or item.get("id") or f"{source_label.lower().replace(' ', '-')}-{index}"),
            "content": _clean_text(item.get("content") or item.get("text") or item.get("title")),
            "linkedin_url": _clean_text(item.get("linkedin_url") or item.get("url") or COMPANY_LINKEDIN),
            "published_date": published.isoformat(),
            "engagement": {
                "reactions": reactions,
                "comments": comments,
                "shares": shares,
            },
            "reactions": reactions,
            "comments": comments,
            "shares": shares,
            "author": _clean_text(item.get("author") or COMPANY_NAME),
            "source": source_label,
        }

    def _build_bing_linkedin_fallback(self, company: dict[str, Any], now: datetime) -> list[dict[str, Any]]:
        search_terms = [
            "Giggso LinkedIn AI governance",
            "Giggso LinkedIn agentic AI",
            "Giggso LinkedIn LLM security",
            "Giggso LinkedIn enterprise AI",
        ]
        snippets: list[str] = []
        for term in search_terms:
            for result in self._bing_search(term, site="linkedin.com/company/gogiggso/posts", limit=2):
                snippet = _clean_text(result.get("snippet"))
                if snippet:
                    snippets.append(snippet)
        if not snippets:
            return []
        posts: list[dict[str, Any]] = []
        themes = self._unique_ordered(company.get("recent_strategic_themes", []) + company.get("strategic_themes", []), limit=LINKEDIN_MAX_POSTS)
        for index, snippet in enumerate(snippets[:LINKEDIN_MAX_POSTS], start=1):
            theme = themes[(index - 1) % len(themes)] if themes else "AI Governance"
            posts.append(
                {
                    "post_id": f"bing-{index}",
                    "content": snippet,
                    "linkedin_url": COMPANY_LINKEDIN,
                    "published_date": now - timedelta(days=index),
                    "engagement": {"reactions": max(1, 10 - index), "comments": max(0, 3 - (index // 2)), "shares": max(0, 2 - (index // 3))},
                    "reactions": max(1, 10 - index),
                    "comments": max(0, 3 - (index // 2)),
                    "shares": max(0, 2 - (index // 3)),
                    "author": COMPANY_NAME,
                    "source": "Bing snippet fallback",
                    "title": theme,
                }
            )
        return posts

    def _build_linkedin_posts_fallback(self, company: dict[str, Any], snippets: list[str], now: datetime) -> list[dict[str, Any]]:
        themes = self._unique_ordered(company.get("recent_strategic_themes", []) + company.get("strategic_themes", []), limit=6)
        post_templates = [
            "AI Governance is becoming a production requirement, not a future aspiration.",
            "Security validation should be part of every enterprise AI rollout.",
            "Agentic AI needs guardrails, approvals, and monitoring from day one.",
            "Trustworthy AI is what turns pilot projects into enterprise value.",
            "Compliance evidence should move as fast as the AI workflow itself.",
        ]
        posts: list[dict[str, Any]] = []
        for index, template in enumerate(post_templates, start=1):
            theme = themes[(index - 1) % len(themes)] if themes else template
            post_text = f"{template} {theme}".strip()
            posts.append(
                {
                    "post_id": f"fallback-{index}",
                    "content": post_text,
                    "text": post_text,
                    "title": template,
                    "linkedin_url": COMPANY_LINKEDIN,
                    "published_date": now - timedelta(days=index * 2),
                    "engagement": {
                        "reactions": max(12, 48 - index * 4),
                        "comments": max(2, 14 - index),
                        "shares": max(1, 6 - (index // 2)),
                    },
                    "reactions": max(12, 48 - index * 4),
                    "comments": max(2, 14 - index),
                    "shares": max(1, 6 - (index // 2)),
                    "author": COMPANY_NAME,
                    "source": "fallback",
                }
            )
        if snippets:
            posts[0]["text"] = f"{posts[0]['text']} {snippets[0][:120]}".strip()
        return posts

    def _derive_linkedin_themes(self, posts: list[dict[str, Any]], snippets: list[str]) -> dict[str, Any]:
        combined = " ".join([item.get("text", "") for item in posts] + snippets)
        keywords = Counter(self._extract_keywords(combined, minimum=8))
        ranked_keywords = [{"keyword": item[0], "count": item[1]} for item in keywords.most_common(10)]
        preferred_topics = [
            "AI Governance",
            "Agentic AI",
            "LLM Security",
            "Model Monitoring",
            "AI Compliance",
            "AI Risk",
            "Enterprise AI",
            "Trustworthy AI",
            "Shadow AI",
        ]
        top_theme = next((topic for topic in preferred_topics if topic.lower() in combined.lower()), "AI Governance")
        emerging_theme = next((topic for topic in preferred_topics[1:] if topic.lower() in combined.lower()), "Enterprise AI")
        trend_frequency = {self._normalize_topic_name(item["keyword"]): item["count"] for item in ranked_keywords}
        strategic_narrative = (
            f"Recent LinkedIn signals emphasize {top_theme.lower()}, with growing attention on {emerging_theme.lower()} and enterprise deployment readiness."
        )
        return {
            "top_theme": top_theme,
            "emerging_theme": emerging_theme,
            "keyword_ranking": ranked_keywords,
            "trend_frequency": trend_frequency,
            "strategic_narrative": strategic_narrative,
        }

    def _collect_news_intelligence(self, now: datetime) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()
        for query in NEWS_QUERIES:
            feed = self._google_news_rss(query, limit=4)
            for entry in feed:
                key = (entry["headline"].lower(), entry["source"].lower())
                if key in seen:
                    continue
                seen.add(key)
                items.append(entry)
        items.sort(key=lambda item: (item.get("relevance_score", 0), item.get("date") or ""), reverse=True)
        return items[:24]

    def _collect_competitor_signals(self, now: datetime) -> list[dict[str, Any]]:
        competitors: list[dict[str, Any]] = []
        for item in COMPETITOR_CONFIG:
            search_results = self._bing_search(item["search_query"], site=item["domain"], limit=4)
            latest = search_results[0] if search_results else {}
            snippets = [result.get("snippet", "") for result in search_results if result.get("snippet")]
            titles = [result.get("title", "") for result in search_results if result.get("title")]
            activity_summary = self._build_competitor_activity_summary(item["name"], latest, snippets)
            competitors.append(
                {
                    "name": item["name"],
                    "focus_area": item["focus_area"],
                    "strategic_focus": item["focus_area"],
                    "latest_developments": self._unique_ordered(titles[:3], limit=3),
                    "activity_summary": activity_summary,
                    "positioning": item["positioning"],
                    "strategic_position": item["positioning"],
                    "momentum_score": self._score_competitor_momentum(search_results, item["name"]),
                    "source_notes": self._unique_ordered(snippets + titles, limit=6),
                    "last_updated": now.isoformat(),
                }
            )
        return competitors

    def _build_live_trends(
        self,
        company: dict[str, Any],
        linkedin: dict[str, Any],
        news: list[dict[str, Any]],
        competitors: list[dict[str, Any]],
        now: datetime,
    ) -> list[dict[str, Any]]:
        trend_payloads: list[dict[str, Any]] = []
        text_pool = " ".join(
            [
                company.get("overview", ""),
                company.get("industry_positioning", ""),
                company.get("strategic_direction", ""),
                linkedin.get("strategic_narrative", ""),
                " ".join(item.get("headline", "") for item in news),
                " ".join(" ".join(item.get("latest_developments", [])) for item in competitors),
            ]
        )
        counts = Counter(self._extract_keywords(text_pool, minimum=10))
        source_lookup = defaultdict(set)
        for item in news:
            for token in self._extract_keywords(f"{item.get('headline', '')} {item.get('summary', '')}", minimum=4):
                source_lookup[token].add("news")
        for item in competitors:
            for token in self._extract_keywords(f"{item.get('activity_summary', '')} {item.get('positioning', '')}", minimum=4):
                source_lookup[token].add("competitor")
        for phrase in company.get("focus_keywords", []):
            for token in self._extract_keywords(phrase, minimum=1):
                source_lookup[token].add("company")

        trend_specs = [
            ("AI Governance", "Governance"),
            ("Agentic AI", "Agentic AI"),
            ("LLM Security", "Security"),
            ("Model Monitoring", "Observability"),
            ("AI Compliance", "Compliance"),
            ("AI Risk", "Risk"),
            ("RAG", "Knowledge Systems"),
            ("Enterprise AI", "Enterprise Adoption"),
            ("Trustworthy AI", "Trust"),
            ("Shadow AI", "Risk"),
        ]
        for trend_name, category in trend_specs:
            keyword = self._normalize_topic_name(trend_name).lower()
            base_mentions = counts.get(keyword, 0)
            evidence_sources = len(source_lookup.get(keyword, set()))
            related_sources = {
                token
                for token in source_lookup
                if keyword in token or token in keyword or self._topic_overlap(keyword, token)
            }
            source_count = max(1, evidence_sources + len(related_sources))
            momentum = min(100.0, 45.0 + base_mentions * 10.0 + source_count * 8.0)
            growth = min(100.0, 35.0 + source_count * 10.0 + base_mentions * 6.0)
            summary = self._trend_summary_for(trend_name, company, linkedin, news, competitors)
            source_notes = self._trend_sources(trend_name, company, linkedin, news, competitors)
            article_count = sum(
                1
                for item in news
                if trend_name.lower() in f"{item.get('headline', '')} {item.get('summary', '')}".lower()
            )
            mention_count = sum(
                1
                for item in competitors
                if trend_name.lower() in f"{item.get('activity_summary', '')} {item.get('positioning', '')}".lower()
            )
            evidence_meta = self._evidence_metadata(
                article_count=article_count,
                mention_count=mention_count,
                source_notes=source_notes,
                source_count=source_count,
                last_updated=now,
            )
            score_features = self._search_score_features(
                company_hits=float(len(company.get("focus_keywords", [])) if company else 0),
                news_count=article_count,
                linkedin_count=len(linkedin.get("posts") or []),
                competitor_count=mention_count,
                rag_relevance=float(sum(1 for item in news if trend_name.lower() in f"{item.get('headline', '')} {item.get('summary', '')}".lower()) * 10.0),
                keyword_count=max(1, len(counts)),
                recency_score=10.0,
                query_type=category,
                query=trend_name,
            )
            momentum_result = industry_analytics_scoring_engine.score("momentum", score_features)
            growth_result = industry_analytics_scoring_engine.score("growth", score_features)
            trend_payloads.append(
                {
                    "trend_name": trend_name,
                    "category": category,
                    "momentum_score": momentum_result["score"],
                    "growth_score": growth_result["score"],
                    "source_count": source_count,
                    "evidence_count": evidence_meta["evidence_count"],
                    "last_updated": now,
                    "confidence_reason": evidence_meta["confidence_reason"],
                    "evidence_sources": evidence_meta["evidence_sources"],
                    "source_names": evidence_meta["source_names"],
                    "source_timestamps": evidence_meta["source_timestamps"],
                    "executive_summary": summary,
                    "signal_strength": self._signal_strength(momentum_result["score"]),
                    "score_features": score_features,
                    "scoring_method": momentum_result["scoring_method"],
                    "llm_used_for_score": False,
                    "source_notes": source_notes,
                    "created_at": now,
                    "updated_at": now,
                }
            )
        trend_payloads.sort(key=lambda item: (item["momentum_score"], item["growth_score"]), reverse=True)
        return trend_payloads

    def _build_keywords(
        self,
        company: dict[str, Any],
        linkedin: dict[str, Any],
        news: list[dict[str, Any]],
        competitors: list[dict[str, Any]],
        live_trends: list[dict[str, Any]],
        now: datetime,
    ) -> list[dict[str, Any]]:
        source_groups = {
            "Top AI Governance Keywords": [],
            "Fastest Growing Keywords": [],
            "Enterprise Adoption Keywords": [],
        }
        governance_terms = [
            "AI Governance",
            "Policy Controls",
            "Trustworthy AI",
            "AI Compliance",
            "AI Risk",
            "Model Monitoring",
        ]
        growth_terms = [
            "Agentic AI",
            "LLM Security",
            "Shadow AI",
            "RAG",
            "AI Security",
            "Observability",
        ]
        adoption_terms = [
            "Enterprise AI",
            "Production AI",
            "Secure Deployment",
            "Audit Trails",
            "Governance Automation",
            "AI Operations",
        ]
        keyword_rows: list[dict[str, Any]] = []
        for group_name, terms in (
            ("Top AI Governance Keywords", governance_terms),
            ("Fastest Growing Keywords", growth_terms),
            ("Enterprise Adoption Keywords", adoption_terms),
        ):
            for index, term in enumerate(terms, start=1):
                source_count = self._keyword_source_count(term, company, linkedin, news, competitors, live_trends)
                source_notes = self._keyword_sources(term, company, linkedin, news, competitors, live_trends)
                evidence_meta = self._evidence_metadata(
                    article_count=0,
                    mention_count=max(1, source_count),
                    source_notes=source_notes,
                    source_count=max(1, source_count),
                    last_updated=now,
                )
                recency_score = self._signal_recency_score(evidence_meta["source_timestamps"], evidence_meta["last_updated"])
                score_features = self._search_score_features(
                    company_hits=float(source_count),
                    news_count=len(news),
                    linkedin_count=len(linkedin.get("posts") or []),
                    competitor_count=len(competitors),
                    rag_relevance=float(len(source_notes) * 8.0),
                    keyword_count=max(1, len(term.split())),
                    recency_score=recency_score,
                    query_type=group_name,
                    query=term,
                )
                momentum_result = industry_analytics_scoring_engine.score("momentum", score_features)
                growth_result = industry_analytics_scoring_engine.score("growth", score_features)
                keyword_rows.append(
                    {
                        "keyword": term,
                        "keyword_group": group_name,
                        "momentum_score": momentum_result["score"],
                        "growth_score": growth_result["score"],
                        "source_count": max(1, source_count),
                        "evidence_count": evidence_meta["evidence_count"],
                        "last_updated": now,
                        "confidence_reason": evidence_meta["confidence_reason"],
                        "evidence_sources": evidence_meta["evidence_sources"],
                        "source_names": evidence_meta["source_names"],
                        "source_timestamps": evidence_meta["source_timestamps"],
                        "executive_summary": f"{term} is a {group_name.lower()} signal with support from company messaging, news, and competitor activity.",
                        "score_features": score_features,
                        "scoring_method": momentum_result["scoring_method"],
                        "llm_used_for_score": False,
                        "source_notes": source_notes,
                        "created_at": now,
                        "updated_at": now,
                    }
                )
        keyword_rows.sort(key=lambda item: (item["keyword_group"], item["growth_score"], item["momentum_score"]), reverse=True)
        return keyword_rows

    def _build_recommendations(
        self,
        live_trends: list[dict[str, Any]],
        linkedin: dict[str, Any],
        competitors: list[dict[str, Any]],
        now: datetime,
    ) -> list[dict[str, Any]]:
        recommendations: list[dict[str, Any]] = []
        ranked = live_trends[:5]
        for item in ranked:
            trend = item["trend_name"]
            reasoning = self._recommendation_reason(trend, item, linkedin, competitors)
            source_notes = [item.get("executive_summary", ""), linkedin.get("strategic_narrative", "")]
            evidence_meta = self._evidence_metadata(
                article_count=0,
                mention_count=_safe_int(item.get("source_count"), 0),
                source_notes=source_notes,
                source_count=_safe_int(item.get("source_count"), 0),
                last_updated=now,
            )
            recency_score = self._signal_recency_score(item.get("source_timestamps"), item.get("last_updated"), source_notes)
            trend_strength = self._clamp(
                _safe_number(item.get("momentum_score"), 0.0) * 0.6 + _safe_number(item.get("growth_score"), 0.0) * 0.4,
                0.0,
                100.0,
            )
            historical_relevance = self._clamp(_safe_number(item.get("growth_score"), 0.0), 0.0, 100.0)
            signal_consistency = self._signal_consistency_score([
                _safe_number(item.get("momentum_score"), 0.0),
                _safe_number(item.get("growth_score"), 0.0),
                _safe_number(item.get("source_count"), 0.0) * 10.0,
                _safe_number(item.get("evidence_count"), 0.0) * 8.0,
            ])
            score_features = self._search_score_features(
                company_hits=max(1.0, _safe_number(item.get("source_count"), 0.0)),
                news_count=max(1, len(source_notes) + len(item.get("source_names") or [])),
                linkedin_count=len(linkedin.get("posts") or []),
                competitor_count=len(competitors),
                rag_relevance=float(trend_strength + signal_consistency / 2.0),
                keyword_count=max(1, len(trend.split()) + len(item.get("source_names") or [])),
                recency_score=recency_score,
                query_type="Concept",
                query=trend,
            )
            recommendation_score = industry_analytics_scoring_engine.score("opportunity", score_features)
            confidence_score, insufficient_data = self._evidence_based_confidence(
                evidence_count=_safe_int(item.get("evidence_count"), 0),
                source_count=_safe_int(item.get("source_count"), 0),
                signal_consistency=signal_consistency,
                trend_strength=trend_strength,
                historical_relevance=historical_relevance,
                recency_score=recency_score,
            )
            score_features["insufficient_data"] = insufficient_data
            score_features["signal_consistency"] = round(signal_consistency, 2)
            score_features["trend_strength"] = round(trend_strength, 2)
            score_features["historical_relevance"] = round(historical_relevance, 2)
            score_features["recency_score"] = round(recency_score, 2)
            recommendations.append(
                {
                    "trend": trend,
                    "reason": reasoning,
                    "impact": self._recommendation_impact(trend),
                    "recommended_action": self._recommendation_action(trend),
                    "confidence_score": confidence_score if not insufficient_data else 0.0,
                    "evidence_count": evidence_meta["evidence_count"],
                    "source_count": evidence_meta["source_count"],
                    "last_updated": now,
                    "confidence_reason": "Insufficient data." if insufficient_data else (
                        f"Backed by {_safe_int(item.get('evidence_count'), 0)} evidence signals across {_safe_int(item.get('source_count'), 0)} sources; "
                        f"signal consistency is {signal_consistency:.0f}/100 and trend strength is {trend_strength:.0f}/100."
                    ),
                    "evidence_sources": evidence_meta["evidence_sources"],
                    "source_names": evidence_meta["source_names"],
                    "source_timestamps": evidence_meta["source_timestamps"],
                    "score_features": score_features,
                    "scoring_method": recommendation_score["scoring_method"],
                    "llm_used_for_score": False,
                    "source_notes": source_notes,
                    "created_at": now,
                    "updated_at": now,
                }
            )
        recommendations.sort(key=lambda item: item["confidence_score"], reverse=True)
        return recommendations

    def _build_competitor_cards(
        self,
        company: dict[str, Any],
        linkedin: dict[str, Any],
        news: list[dict[str, Any]],
        competitor_signals: list[dict[str, Any]],
        live_trends: list[dict[str, Any]],
        keywords: list[dict[str, Any]],
        now: datetime,
    ) -> list[dict[str, Any]]:
        cards: list[dict[str, Any]] = []
        snapshot = {
            "company": company,
            "company_signals": {
                "company_name": COMPANY_NAME,
                "website": COMPANY_WEBSITE,
                "linkedin_url": COMPANY_LINKEDIN,
                "positioning": company.get("industry_positioning", ""),
                "core_services": company.get("core_focus_areas", []),
                "strategic_themes": company.get("strategic_themes", []),
                "focus_keywords": company.get("focus_keywords", []),
                "product_messaging": company.get("content_themes", []),
                "source_notes": company.get("source_notes", []),
                "last_updated": company.get("last_updated").isoformat() if isinstance(company.get("last_updated"), datetime) else None,
            },
            "linkedin": linkedin,
            "news": news,
            "competitor_cards": competitor_signals,
            "live_trends": live_trends,
            "keywords": keywords,
        }
        company_analysis = self._build_search_intelligence(COMPANY_NAME, snapshot, persist_history=False)
        for item in competitor_signals:
            last_updated = _parse_datetime(item.get("last_updated")) or now
            competitor_query = item.get("name") or ""
            competitor_analysis = self._build_search_intelligence(competitor_query, snapshot, persist_history=False)
            left_type = company_analysis.get("query_type") or self.detect_query_type(COMPANY_NAME)
            right_type = competitor_analysis.get("query_type") or self.detect_query_type(competitor_query)
            strengths = self._comparison_strengths(COMPANY_NAME, competitor_query, company_analysis, competitor_analysis, left_type, right_type)
            weaknesses = self._comparison_weaknesses(COMPANY_NAME, competitor_query, company_analysis, competitor_analysis, left_type, right_type)
            gap_analysis = self._comparison_gap_analysis(
                left_query=COMPANY_NAME,
                right_query=competitor_query,
                left=company_analysis,
                right=competitor_analysis,
                left_type=left_type,
                right_type=right_type,
                strengths=strengths,
                weaknesses=weaknesses,
            )
            strategic_recommendations = self._comparison_strategic_recommendations(
                left_query=COMPANY_NAME,
                right_query=competitor_query,
                left=company_analysis,
                right=competitor_analysis,
                left_type=left_type,
                right_type=right_type,
                overlap=gap_analysis.get("summary") or [],
                gap_analysis=gap_analysis,
            )
            competitor_sources = self._evidence_source_names(
                competitor_analysis.get("source_names") or [],
                competitor_analysis.get("evidence_sources") or [],
                [item.get("name", "")],
                item.get("source_notes") or [],
                [news_item.get("source", "") for news_item in competitor_analysis.get("recent_news") or []],
            )
            competitor_timestamps = self._unique_ordered(
                [
                    *[news_item.get("published_date") or news_item.get("published_at") or news_item.get("date") for news_item in competitor_analysis.get("recent_news") or []],
                    *[mention.get("last_updated") for mention in competitor_analysis.get("competitor_mentions") or []],
                    item.get("last_updated"),
                ],
                limit=12,
            )
            competitor_evidence_count = _safe_int(competitor_analysis.get("evidence_count") or competitor_analysis.get("source_count") or 0)
            competitor_source_count = max(_safe_int(competitor_analysis.get("source_count") or 0), len(competitor_sources))
            if competitor_evidence_count <= 0 or competitor_source_count <= 0:
                continue
            recent_signals = self._unique_ordered(
                [
                    *[dev for dev in item.get("latest_developments", []) if dev],
                    *(news_item.get("headline", "") for news_item in competitor_analysis.get("recent_news") or [] if news_item.get("headline")),
                    competitor_analysis.get("executive_summary", ""),
                ],
                limit=6,
            )
            recency_score = self._signal_recency_score(competitor_timestamps, competitor_analysis.get("last_updated"), item.get("last_updated"))
            search_visibility = self._clamp(
                _safe_number(competitor_analysis.get("confidence_score"), 0.0) * 0.45
                + _safe_number(competitor_analysis.get("trend_score"), 0.0) * 0.35
                + _safe_number(item.get("momentum_score"), 0.0) * 0.20,
                0.0,
                100.0,
            )
            competitor_activity = self._clamp(
                _safe_number(item.get("momentum_score"), 0.0) * 0.5
                + _safe_number(competitor_analysis.get("momentum_score"), 0.0) * 0.3
                + _safe_number(competitor_analysis.get("trend_score"), 0.0) * 0.2,
                0.0,
                100.0,
            )
            trend_frequency = len(recent_signals) + len(competitor_analysis.get("recent_news") or []) + len(competitor_analysis.get("competitor_mentions") or [])
            market_relevance = self._clamp(
                max(
                    _safe_number(competitor_analysis.get("trend_score"), 0.0),
                    _safe_number(competitor_analysis.get("growth_score"), 0.0),
                    search_visibility,
                ),
                0.0,
                100.0,
            )
            historical_growth = self._clamp(
                max(
                    _safe_number(competitor_analysis.get("growth_score"), 0.0),
                    _safe_number(competitor_analysis.get("trend_score"), 0.0),
                ),
                0.0,
                100.0,
            )
            score_features = self._search_score_features(
                company_hits=company_analysis.get("evidence_count", 0) or company_analysis.get("source_count", 0) or 0,
                news_count=max(1, len(competitor_analysis.get("recent_news") or []) + len(recent_signals)),
                linkedin_count=max(0, len(competitor_analysis.get("competitor_mentions") or [])),
                competitor_count=max(1, len(recent_signals)),
                rag_relevance=max(competitor_evidence_count * 7.0, search_visibility, market_relevance),
                keyword_count=max(1, len(competitor_sources) + len(gap_analysis.get("market_positioning_gaps") or [])),
                recency_score=recency_score,
                query_type=right_type,
                query=competitor_query,
            )
            score_features["search_visibility"] = round(search_visibility, 2)
            score_features["trend_frequency"] = float(trend_frequency)
            score_features["competitor_activity"] = competitor_activity
            score_features["market_gap"] = max(0.0, 100.0 - len(gap_analysis.get("market_positioning_gaps") or []) * 18.0 - len(gap_analysis.get("enterprise_readiness_gaps") or []) * 12.0)
            score_features["historical_growth"] = historical_growth
            threat_result = industry_analytics_scoring_engine.score("threat", score_features)
            threat_score = threat_result["score"]
            signal_consistency = self._signal_consistency_score([
                threat_score,
                competitor_activity,
                market_relevance,
                historical_growth,
                search_visibility,
            ])
            confidence_score, insufficient_data = self._evidence_based_confidence(
                evidence_count=competitor_evidence_count,
                source_count=competitor_source_count,
                signal_consistency=signal_consistency,
                trend_strength=market_relevance,
                historical_relevance=historical_growth,
                recency_score=recency_score,
            )
            score_features["insufficient_data"] = insufficient_data
            score_features["signal_consistency"] = round(signal_consistency, 2)
            score_features["trend_strength"] = round(market_relevance, 2)
            score_features["historical_relevance"] = round(historical_growth, 2)
            score_features["recency_score"] = round(recency_score, 2)
            score_reason = (
                "Insufficient data."
                if insufficient_data
                else (
                    f"Threat score combines {competitor_evidence_count} evidence signals, {competitor_source_count} sources, "
                    f"competitor activity {competitor_activity:.0f}/100, search visibility {search_visibility:.0f}/100, "
                    f"and market gap {score_features['market_gap']:.0f}/100."
                )
            )
            cards.append(
                {
                    "name": item["name"],
                    "focus_area": item["focus_area"],
                    "activity_summary": item["activity_summary"],
                    "momentum_score": self._clamp(
                        _safe_number(item.get("momentum_score"), 0.0) * 0.55
                        + _safe_number(competitor_analysis.get("growth_score"), 0.0) * 0.25
                        + search_visibility * 0.20,
                        0.0,
                        100.0,
                    ),
                    "strategic_position": item["strategic_position"],
                    "threat_score": threat_score,
                    "confidence_score": confidence_score if not insufficient_data else 0.0,
                    "evidence_count": competitor_evidence_count,
                    "source_count": competitor_source_count,
                    "source_names": competitor_sources,
                    "source_timestamps": competitor_timestamps,
                    "recent_signals": recent_signals,
                    "strengths": strengths,
                    "weaknesses": weaknesses,
                    "strategic_recommendations": strategic_recommendations[:3],
                    "gap_analysis": gap_analysis,
                    "score_reason": score_reason,
                    "score_features": score_features,
                    "scoring_method": threat_result["scoring_method"],
                    "llm_used_for_score": False,
                    "last_updated": last_updated,
                    "source_notes": item["source_notes"],
                    "created_at": now,
                    "updated_at": now,
                }
            )
        cards.sort(key=lambda item: (_safe_number(item.get("threat_score"), 0.0), _safe_number(item.get("momentum_score"), 0.0)), reverse=True)
        return cards[:6]

    def _build_insights(
        self,
        company: dict[str, Any],
        linkedin: dict[str, Any],
        news: list[dict[str, Any]],
        competitors: list[dict[str, Any]],
        live_trends: list[dict[str, Any]],
        now: datetime,
    ) -> list[dict[str, Any]]:
        payload = {
            "company": company,
            "linkedin": linkedin,
            "news": news[:10],
            "competitors": competitors,
            "trends": live_trends[:6],
        }
        prompt = (
            "You are an executive industry intelligence analyst. "
            "Use the supplied live signals for Giggso to produce 4 concise executive insight cards. "
            "Return ONLY valid JSON as a list of objects with keys: insight_title, what_is_trending, why_it_matters, business_impact, recommended_action, priority, insight_type."
            "\nSignals:\n"
            f"{json.dumps(payload, default=str, ensure_ascii=False, indent=2)}"
        )
        parsed = self._generate_gemini_json(prompt)
        if isinstance(parsed, list) and parsed:
            try:
                normalized = self._normalize_insight_items(parsed, now)
                for item in normalized:
                    notes = item.get("source_notes") or []
                    evidence_meta = self._evidence_metadata(
                        article_count=0,
                        mention_count=max(1, len(notes)),
                        source_notes=notes,
                        source_count=max(1, len(notes)),
                        last_updated=now,
                    )
                    item.update(
                        {
                            "evidence_count": evidence_meta["evidence_count"],
                            "source_count": evidence_meta["source_count"],
                            "confidence_reason": evidence_meta["confidence_reason"],
                            "evidence_sources": evidence_meta["evidence_sources"],
                            "source_names": evidence_meta["source_names"],
                            "source_timestamps": evidence_meta["source_timestamps"],
                            "last_updated": evidence_meta["last_updated"],
                        }
                    )
                return normalized
            except Exception as exc:
                logger.warning("Gemini executive insight normalization failed: %s", exc)
        return self._fallback_insights(company, linkedin, news, competitors, live_trends, now)

    def _build_opportunities(
        self,
        company: dict[str, Any],
        linkedin: dict[str, Any],
        news: list[dict[str, Any]],
        competitors: list[dict[str, Any]],
        live_trends: list[dict[str, Any]],
        keywords: list[dict[str, Any]],
        snapshot: dict[str, Any],
        now: datetime,
    ) -> list[dict[str, Any]]:
        opportunity_specs = [
            {
                "opportunity_name": "Governance assessment package",
                "trend_name": "AI Governance",
                "search_query": "AI Governance",
                "summary": "Enterprises are formalizing governance reviews before scaling AI deployments.",
                "business_value": "Creates a faster path from review to production by packaging policy, controls, and audit readiness.",
                "recommended_action": "Lead with governance checkpoints, approval workflows, and audit-ready reporting.",
                "target_buyer": "Chief Risk Officer / AI Governance leader",
                "theme_terms": ["AI Governance", "Governance", "Compliance", "Policy", "Audit"],
            },
            {
                "opportunity_name": "LLM security testing offer",
                "trend_name": "LLM Security",
                "search_query": "LLM Security",
                "summary": "Security validation remains a high-friction step in enterprise LLM deployment.",
                "business_value": "Helps security teams unblock AI rollouts with testing, controls, and evidence for approval.",
                "recommended_action": "Package red-teaming, prompt-injection testing, and deployment guardrails.",
                "target_buyer": "CISO / AppSec lead",
                "theme_terms": ["LLM Security", "Security", "Red Team", "Prompt Injection", "Model Risk"],
            },
            {
                "opportunity_name": "Model monitoring dashboard",
                "trend_name": "Model Monitoring",
                "search_query": "Model Monitoring",
                "summary": "Production teams need drift, quality, and incident visibility after launch.",
                "business_value": "Turns post-launch monitoring into a paid control layer for enterprise AI operations.",
                "recommended_action": "Show drift alerts, traceability, and quality monitoring as the default control plane.",
                "target_buyer": "ML engineering / Platform team",
                "theme_terms": ["Model Monitoring", "Monitoring", "Observability", "Drift", "Traceability"],
            },
            {
                "opportunity_name": "RAG assurance program",
                "trend_name": "RAG",
                "search_query": "RAG",
                "summary": "Enterprise copilots need grounded retrieval, citations, and traceability to earn adoption.",
                "business_value": "Improves answer quality and trust for retrieval-based enterprise assistants.",
                "recommended_action": "Position grounding, citation coverage, and retrieval quality as launch requirements.",
                "target_buyer": "Enterprise AI product owner",
                "theme_terms": ["RAG", "Retrieval", "Grounding", "Citations", "Enterprise AI"],
            },
            {
                "opportunity_name": "Agentic AI controls layer",
                "trend_name": "Agentic AI",
                "search_query": "Agentic AI",
                "summary": "Agent rollouts are moving from experiments to controlled enterprise execution.",
                "business_value": "Creates a control layer for approvals, monitoring, and explanation before broad agent deployment.",
                "recommended_action": "Sell governance, guardrails, and approval trails as the agent rollout enabler.",
                "target_buyer": "AI platform owner / product leader",
                "theme_terms": ["Agentic AI", "Agents", "Workflow", "Autonomous", "Orchestration"],
            },
        ]

        company_text = " ".join(
            [
                str(company.get("overview", "")),
                str(company.get("industry_positioning", "")),
                str(company.get("market_narrative", "")),
                str(linkedin.get("strategic_narrative", "")),
                " ".join(company.get("core_focus_areas", []) or []),
                " ".join(company.get("strategic_themes", []) or []),
            ]
        ).lower()
        opportunities: list[dict[str, Any]] = []

        def theme_match_score(text: str, terms: list[str]) -> float:
            haystack = text.lower()
            score = 0.0
            for term in terms:
                normalized = self._normalize_topic_name(term).lower()
                if not normalized:
                    continue
                if normalized in haystack:
                    score += 2.0
                elif self._topic_overlap(normalized, haystack):
                    score += 1.0
            return score

        for spec in opportunity_specs:
            terms = spec["theme_terms"]
            matched_trends = [
                item
                for item in live_trends
                if theme_match_score(
                    " ".join(
                        [
                            item.get("trend_name", ""),
                            item.get("category", ""),
                            item.get("executive_summary", ""),
                            " ".join(item.get("source_notes", []) or []),
                        ]
                    ),
                    terms,
                )
            ]
            matched_keywords = [
                item
                for item in keywords
                if theme_match_score(
                    " ".join(
                        [
                            item.get("keyword", ""),
                            item.get("keyword_group", ""),
                            item.get("executive_summary", ""),
                            " ".join(item.get("source_notes", []) or []),
                        ]
                    ),
                    terms,
                )
            ]
            matched_competitors = [
                item
                for item in competitors
                if theme_match_score(
                    " ".join(
                        [
                            item.get("name", ""),
                            item.get("focus_area", ""),
                            item.get("activity_summary", ""),
                            item.get("strategic_position", ""),
                            " ".join(item.get("source_notes", []) or []),
                        ]
                    ),
                    terms,
                )
            ]
            search_result = self._build_search_intelligence(f"Giggso {spec['search_query']}", snapshot, persist_history=False)

            search_source_names = self._evidence_source_names(
                search_result.get("source_names") or [],
                search_result.get("evidence_sources") or [],
                [item.get("source", "") for item in search_result.get("recent_news") or []],
                [item.get("name", "") for item in search_result.get("competitor_mentions") or []],
            )
            trend_source_names = self._evidence_source_names(
                [item.get("trend_name", "") for item in matched_trends],
                [item.get("keyword", "") for item in matched_keywords],
                [item.get("name", "") for item in matched_competitors],
                [company.get("company_name", COMPANY_NAME), linkedin.get("top_theme", "")],
            )
            source_names = self._unique_ordered([*search_source_names, *trend_source_names], limit=12)
            source_timestamps = self._unique_ordered(
                [
                    *[item.get("last_updated") for item in matched_trends],
                    *[item.get("last_updated") for item in matched_keywords],
                    *[item.get("last_updated") for item in matched_competitors],
                    *search_result.get("source_timestamps", []),
                    *[item.get("published_date") or item.get("published_at") or item.get("date") for item in search_result.get("recent_news") or []],
                ],
                limit=12,
            )

            trend_strength = self._average(
                [
                    _safe_number(item.get("momentum_score"), 0.0) * 0.65 + _safe_number(item.get("growth_score"), 0.0) * 0.35
                    for item in matched_trends
                ]
            ) if matched_trends else _safe_number((live_trends[0] if live_trends else {}).get("momentum_score"), 0.0)
            trend_frequency = float(len(matched_trends) * 2 + len(matched_keywords) + len(matched_competitors) * 2)
            search_relevance = _safe_number(search_result.get("trend_score"), 0.0)
            search_confidence = _safe_number(search_result.get("confidence_score"), 0.0)
            search_evidence_count = _safe_int(search_result.get("evidence_count") or search_result.get("source_count") or 0)
            search_source_count = _safe_int(search_result.get("source_count") or len(search_source_names))

            enterprise_fit = min(
                100.0,
                42.0
                + theme_match_score(company_text, terms) * 8.0
                + min(20.0, theme_match_score(str(linkedin.get("strategic_narrative", "")), terms) * 6.0)
                + min(18.0, len(matched_keywords) * 3.0)
                + min(18.0, len(matched_trends) * 4.0),
            )
            competitor_density = min(100.0, (len(matched_competitors) * 18.0) + (_safe_number(search_result.get("competitor_mention_count"), 0.0) * 10.0))
            competitive_advantage = max(
                0.0,
                min(
                    100.0,
                    (enterprise_fit * 0.45)
                    + max(0.0, 82.0 - competitor_density) * 0.35
                    + min(18.0, len(search_result.get("competitor_mentions") or []) * 4.0),
                ),
            )
            market_demand = max(
                0.0,
                min(
                    100.0,
                    (search_relevance * 0.5)
                    + (trend_strength * 0.25)
                    + min(20.0, trend_frequency * 3.5)
                    + (search_confidence * 0.1),
                ),
            )
            risk_score = max(
                0.0,
                min(
                    100.0,
                    100.0 - (enterprise_fit * 0.38) - (market_demand * 0.26) + (competitor_density * 0.32),
                ),
            )
            adoption_score = max(
                0.0,
                min(100.0, (market_demand * 0.42) + (enterprise_fit * 0.28) + (trend_strength * 0.2) - (risk_score * 0.1)),
            )
            revenue_opportunity_score = max(
                0.0,
                min(
                    100.0,
                    (market_demand * 0.34)
                    + (enterprise_fit * 0.22)
                    + (competitive_advantage * 0.22)
                    + (adoption_score * 0.16)
                    + (search_relevance * 0.06),
                ),
            )
            opportunity_count = max(
                1,
                len(matched_trends)
                + len(matched_keywords)
                + len(matched_competitors)
                + len(search_result.get("recent_news") or [])
                + len(search_result.get("competitor_mentions") or []),
            )
            ml_inputs = self._build_product_impact_ml_inputs(
                market_demand_score=market_demand,
                enterprise_fit_score=enterprise_fit,
                revenue_opportunity_score=revenue_opportunity_score,
                competitive_advantage_score=competitive_advantage,
                risk_score=risk_score,
                trend_strength=trend_strength,
                competitor_density=competitor_density,
                opportunity_count=opportunity_count,
                market_interest=search_relevance,
                adoption_probability_score=adoption_score,
                feature_keywords=terms,
                competitor_matches=matched_competitors or search_result.get("competitor_mentions") or [],
                trend_matches=matched_trends or [search_result],
                feature_name=spec["opportunity_name"],
                feature_description=spec["summary"],
            )
            ml_predictions = product_impact_ml_engine.predict(ml_inputs)
            launch_prediction = ml_predictions.get("launch_readiness") or {}
            risk_prediction = ml_predictions.get("risk_classification") or {}
            revenue_prediction = ml_predictions.get("revenue_opportunity") or {}
            launch_score = _safe_number(launch_prediction.get("predicted_score"), revenue_opportunity_score)
            launch_confidence = _safe_number(launch_prediction.get("confidence_score"), 0.0)
            revenue_score = _safe_number(revenue_prediction.get("predicted_score"), revenue_opportunity_score)
            revenue_confidence = _safe_number(revenue_prediction.get("confidence_score"), 0.0)
            risk_probability = _safe_number(risk_prediction.get("risk_probability"), risk_score / 100.0)
            risk_label = risk_prediction.get("predicted_label") or "Medium Risk"

            evidence_count = max(search_evidence_count, len(source_names), len(matched_trends) + len(matched_keywords) + len(matched_competitors))
            source_count = max(search_source_count, len(source_names))
            if evidence_count <= 0 or source_count <= 0:
                continue

            mention_count = len(matched_trends) + len(matched_keywords) + len(matched_competitors)
            score_features = {
                "mention_count": float(mention_count),
                "source_count": float(source_count),
                "evidence_count": float(evidence_count),
                "recency_score": 10.0,
                "trend_frequency": float(trend_frequency),
                "keyword_relevance": float(search_relevance),
                "competitor_activity": float(competitor_density),
                "market_gap": float(max(0.0, 100.0 - competitor_density)),
                "historical_growth": float(trend_strength),
            }
            opportunity_result = industry_analytics_scoring_engine.score("opportunity", score_features)
            product_impact_result = industry_analytics_scoring_engine.score("product_impact", score_features)
            opportunity_score = opportunity_result["score"]
            confidence_score = max(opportunity_result["confidence_score"], _safe_number(product_impact_result.get("confidence_score"), 0.0))
            if confidence_score < 45.0 and evidence_count < 2:
                continue

            impact_summary = (
                f"{spec['business_value']} Live signals show {search_result.get('momentum', 'moderate').lower()} market activity, "
                f"{len(matched_trends)} trend matches, and {len(matched_competitors)} competitor signals."
            )
            confidence_reason = (
                f"Backed by {evidence_count} evidence signals across {source_count} sources; "
                f"search relevance is {search_relevance:.0f}/100, trend strength is {trend_strength:.0f}/100, "
                f"and ML launch readiness is {launch_score:.0f}/100."
            )

            supporting_evidence = [
                {
                    "label": "Trend frequency",
                    "value": f"+ {len(matched_trends)} trend matches, {len(matched_keywords)} keyword matches",
                    "contribution_direction": "Positive",
                    "business_explanation": f"The market is already clustering around {spec['trend_name']} signals in live trends and keyword activity.",
                },
                {
                    "label": "Search intelligence relevance",
                    "value": f"+ {search_relevance:.0f}/100 relevance from {search_source_count} sources",
                    "contribution_direction": "Positive" if search_relevance >= 50 else "Negative",
                    "business_explanation": "Search intelligence confirms whether the theme is present in current company, news, and competitor signals.",
                },
                {
                    "label": "Competitor gap",
                    "value": f"- {competitor_density:.0f}/100 density" if competitor_density >= 50 else f"+ {100.0 - competitor_density:.0f}/100 gap",
                    "contribution_direction": "Negative" if competitor_density >= 50 else "Positive",
                    "business_explanation": "Lower competitor density leaves more room to win; higher density means the market is crowded and harder to differentiate.",
                },
                {
                    "label": "Product impact readiness",
                    "value": f"+ {launch_score:.0f}/100 launch readiness, + {revenue_score:.0f}/100 revenue opportunity",
                    "contribution_direction": "Positive" if launch_score >= 50 else "Negative",
                    "business_explanation": "ML predictions show whether the opportunity looks launchable and commercially attractive once the live signals are combined.",
                },
            ]

            source_notes = self._unique_ordered(
                [
                    *(company.get("source_notes") or []),
                    *(linkedin.get("source_notes") or []),
                    *(item.get("executive_summary", "") for item in matched_trends),
                    *(item.get("executive_summary", "") for item in matched_keywords),
                    *(item.get("activity_summary", "") for item in matched_competitors),
                    search_result.get("executive_summary", ""),
                    search_result.get("recommendation", ""),
                    " | ".join([item.get("headline", "") for item in search_result.get("recent_news") or [] if item.get("headline")]),
                ],
                limit=12,
            )

            opportunities.append(
                {
                    "opportunity_name": spec["opportunity_name"],
                    "trend_name": spec["trend_name"],
                    "summary": impact_summary,
                    "target_buyer": spec["target_buyer"],
                    "business_value": spec["business_value"],
                    "recommended_action": spec["recommended_action"],
                    "urgency": "High" if opportunity_score >= 75 or confidence_score >= 75 else "Medium" if opportunity_score >= 55 else "Low",
                    "opportunity_score": opportunity_score,
                    "confidence_score": confidence_score,
                    "confidence_reason": confidence_reason,
                    "evidence_count": int(evidence_count),
                    "source_count": int(source_count),
                    "source_names": source_names,
                    "source_timestamps": source_timestamps,
                    "evidence_sources": source_names,
                    "supporting_evidence": supporting_evidence,
                    "product_impact_score": product_impact_result["score"],
                    "score_features": score_features,
                    "scoring_method": opportunity_result["scoring_method"],
                    "llm_used_for_score": False,
                    "signal_inputs": {
                        "market_demand": round(market_demand, 2),
                        "enterprise_fit": round(enterprise_fit, 2),
                        "revenue_opportunity": round(revenue_opportunity_score, 2),
                        "competitive_advantage": round(competitive_advantage, 2),
                        "risk_score": round(risk_score, 2),
                        "trend_strength": round(trend_strength, 2),
                        "competitor_density": round(competitor_density, 2),
                        "opportunity_count": opportunity_count,
                        "search_relevance": round(search_relevance, 2),
                        "search_confidence": round(search_confidence, 2),
                        "search_evidence_count": search_evidence_count,
                        "launch_prediction": launch_prediction,
                        "risk_prediction": risk_prediction,
                        "revenue_prediction": revenue_prediction,
                        "risk_label": risk_label,
                        "risk_probability": round(risk_probability, 4),
                        "matched_trends": [
                            {
                                "trend_name": item.get("trend_name"),
                                "momentum_score": item.get("momentum_score"),
                                "growth_score": item.get("growth_score"),
                            }
                            for item in matched_trends[:3]
                        ],
                        "matched_keywords": [item.get("keyword") for item in matched_keywords[:5]],
                        "matched_competitors": [item.get("name") for item in matched_competitors[:3]],
                    },
                    "source_notes": source_notes,
                    "created_at": now,
                    "updated_at": now,
                }
            )

        opportunities.sort(
            key=lambda item: (
                _safe_number(item.get("confidence_score"), 0.0),
                _safe_number(item.get("opportunity_score"), 0.0),
                len(item.get("source_names") or []),
            ),
            reverse=True,
        )
        return opportunities[:5]

    def _build_report(
        self,
        live_trends: list[dict[str, Any]],
        competitors: list[dict[str, Any]],
        insights: list[dict[str, Any]],
        opportunities: list[dict[str, Any]],
        recommendations: list[dict[str, Any]],
        now: datetime,
    ) -> dict[str, Any]:
        top_trends = [
            {
                "title": item["trend_name"],
                "summary": item["executive_summary"],
                "detail": f"Momentum {item['momentum_score']:.0f}% | Growth {item['growth_score']:.0f}% | Sources {item['source_count']}",
            }
            for item in live_trends[:5]
        ]
        competitor_highlights = [
            {
                "title": item["name"],
                "summary": item["activity_summary"],
                "detail": f"Strategic position: {item['strategic_position']}",
            }
            for item in competitors[:4]
        ]
        strategic_risks = [
            {
                "title": "Shadow AI is expanding faster than policy coverage",
                "summary": "Enterprise AI adoption is outpacing governance controls in many organizations.",
                "detail": "Position policy automation and audit trails as a business accelerator, not just a compliance layer.",
            },
            {
                "title": "LLM security reviews can slow deployment",
                "summary": "Security concerns still delay production use in regulated environments.",
                "detail": "Lead with security validation, prompt-injection protection, and controlled rollout checklists.",
            },
            {
                "title": "Competitors are bundling AI into broad enterprise suites",
                "summary": "Platforms with larger distribution can compress buying cycles.",
                "detail": "Differentiate on governance depth, observability, and evidence-rich compliance.",
            },
        ]
        strategic_opportunities = [
            {
                "title": item["opportunity_name"],
                "summary": item["summary"],
                "detail": item["business_value"],
            }
            for item in opportunities[:5]
        ]
        exec_recs = [
            {
                "title": item["trend"],
                "summary": item["reason"],
                "detail": item["recommended_action"],
            }
            for item in recommendations
        ]
        week_label = f"Week of {now.date().isoformat()}"
        return {
            "report_key": "weekly-industry-report",
            "week_label": week_label,
            "top_trends": top_trends,
            "competitor_highlights": competitor_highlights,
            "strategic_risks": strategic_risks,
            "strategic_opportunities": strategic_opportunities,
            "executive_recommendations": exec_recs,
            "generated_at": now,
            "source_notes": [
                "Derived from live company signals, LinkedIn public search proxies, current AI news, and competitor search signals.",
            ],
            "created_at": now,
            "updated_at": now,
        }

    def _build_company_row(self, company: dict[str, Any], linkedin: dict[str, Any], keywords: list[dict[str, Any]], now: datetime) -> dict[str, Any]:
        summary = (
            f"{COMPANY_NAME} is signaling a governance-first enterprise AI strategy centered on safe deployment, security, compliance, and production readiness."
        )
        strategic_direction = (
            f"Use {linkedin.get('top_theme', 'AI Governance')} as the entry point and expand toward enterprise AI controls, monitoring, and regulated-industry adoption."
        )
        market_narrative = (
            f"The market narrative favors vendors that can prove AI is safe, secure, auditable, and ready for enterprise scale."
        )
        focus_keywords = [item["keyword"] for item in keywords[:10]]
        return {
            "company_name": COMPANY_NAME,
            "website": COMPANY_WEBSITE,
            "linkedin_url": COMPANY_LINKEDIN,
            "headquarters": "Troy, Michigan",
            "founded_year": 2017,
            "company_size": company.get("company_size") or "51-200 employees",
            "overview": company["overview"],
            "core_focus_areas": company["core_focus_areas"],
            "industry_positioning": company["industry_positioning"],
            "strategic_themes": company["strategic_themes"],
            "source_notes": company["source_notes"],
            "recent_strategic_themes": company["recent_strategic_themes"],
            "focus_keywords": focus_keywords,
            "market_positioning": company["market_positioning"],
            "content_themes": company["content_themes"],
            "company_summary": summary,
            "strategic_direction": strategic_direction,
            "market_narrative": market_narrative,
            "last_updated": now,
            "created_at": now,
            "updated_at": now,
        }

    def _build_rag_documents(
        self,
        company_signals: dict[str, Any],
        linkedin: dict[str, Any],
        news: list[dict[str, Any]],
        competitors: list[dict[str, Any]],
        trends: list[dict[str, Any]],
        insights: list[dict[str, Any]],
        recommendations: list[dict[str, Any]],
        opportunities: list[dict[str, Any]],
        now: datetime,
    ) -> list[dict[str, Any]]:
        documents: list[dict[str, Any]] = []
        documents.append(
                {
                    "doc_type": "company_signals",
                    "source_name": COMPANY_NAME,
                    "title": "Giggso company signals",
                    "content": json.dumps(company_signals, default=str, ensure_ascii=False),
                    "metadata_json": {"focus": company_signals.get("focus_keywords", [])},
                    "relevance_score": 1.0,
                    "created_at": now,
                    "updated_at": now,
                }
        )
        documents.append(
                {
                    "doc_type": "linkedin_intelligence",
                    "source_name": COMPANY_NAME,
                    "title": "Giggso LinkedIn intelligence",
                    "content": json.dumps(linkedin, default=str, ensure_ascii=False),
                    "metadata_json": {"top_theme": linkedin.get("top_theme")},
                    "relevance_score": 1.0,
                    "created_at": now,
                    "updated_at": now,
                }
        )
        for item in news[:12]:
            documents.append(
                {
                    "doc_type": "news_intelligence",
                    "source_name": item.get("source", "News"),
                    "title": item.get("headline", ""),
                    "content": item.get("summary", ""),
                    "metadata_json": {"topic": item.get("topic"), "url": item.get("url")},
                    "relevance_score": item.get("relevance_score", 0.0),
                    "created_at": now,
                    "updated_at": now,
                }
            )
        for item in competitors:
            documents.append(
                {
                    "doc_type": "competitor_signals",
                    "source_name": item.get("name", "Competitor"),
                    "title": item.get("name", ""),
                    "content": item.get("activity_summary", ""),
                    "metadata_json": {"positioning": item.get("strategic_position")},
                    "relevance_score": item.get("momentum_score", 0.0),
                    "created_at": now,
                    "updated_at": now,
                }
            )
        for item in trends[:8]:
            documents.append(
                {
                    "doc_type": "trend_reasoning",
                    "source_name": item.get("trend_name", "Trend"),
                    "title": item.get("trend_name", ""),
                    "content": item.get("executive_summary", ""),
                    "metadata_json": {"category": item.get("category")},
                    "relevance_score": item.get("momentum_score", 0.0),
                    "created_at": now,
                    "updated_at": now,
                }
            )
        for item in insights[:8]:
            documents.append(
                {
                    "doc_type": "executive_insight",
                    "source_name": COMPANY_NAME,
                    "title": item.get("insight_title", ""),
                    "content": item.get("why_it_matters", ""),
                    "metadata_json": {"priority": item.get("priority")},
                    "relevance_score": 0.9,
                    "created_at": now,
                    "updated_at": now,
                }
            )
        for item in recommendations[:8]:
            documents.append(
                {
                    "doc_type": "executive_recommendation",
                    "source_name": COMPANY_NAME,
                    "title": item.get("trend", ""),
                    "content": item.get("recommended_action", ""),
                    "metadata_json": {"confidence": item.get("confidence_score")},
                    "relevance_score": item.get("confidence_score", 0.0),
                    "created_at": now,
                    "updated_at": now,
                }
            )
        for item in opportunities[:8]:
            documents.append(
                {
                    "doc_type": "market_opportunity",
                    "source_name": COMPANY_NAME,
                    "title": item.get("opportunity_name", ""),
                    "content": item.get("summary", ""),
                    "metadata_json": {"trend_name": item.get("trend_name")},
                    "relevance_score": item.get("opportunity_score", 0.0),
                    "created_at": now,
                    "updated_at": now,
                }
            )
        return documents

    def _persist_snapshot(self, snapshot: dict[str, Any]) -> None:
        session = get_db_session()
        try:
            for model in (
                IndustryCompany,
                IndustryTrend,
                IndustryLiveTrend,
                IndustryKeyword,
                IndustryCompetitorActivity,
                IndustryInsight,
                IndustryRecommendation,
                IndustryOpportunity,
                IndustryReport,
                IndustryRAGDocument,
            ):
                session.query(model).delete()

            session.add(IndustryCompany(**snapshot["company"]))
            session.add_all(
                [
                    IndustryTrend(
                        trend_name=row["trend_name"],
                        category=row["category"],
                        summary=row["executive_summary"],
                        business_impact=row["executive_summary"],
                        recommended_action=self._recommendation_action(row["trend_name"]),
                        momentum_score=row["momentum_score"],
                        signal_strength=row["signal_strength"],
                        scoring_method=row.get("scoring_method", "ML/analytics-based"),
                        llm_used_for_score=row.get("llm_used_for_score", False),
                        score_features=row.get("score_features", {}),
                        source_notes=row["source_notes"],
                        created_at=row["created_at"],
                        updated_at=row["updated_at"],
                    )
                    for row in snapshot["live_trends"]
                ]
            )
            session.add_all(
                [
                    IndustryLiveTrend(
                        trend_name=row["trend_name"],
                        category=row["category"],
                        momentum_score=row["momentum_score"],
                        growth_score=row["growth_score"],
                        source_count=row["source_count"],
                        last_updated=row["last_updated"],
                        executive_summary=row["executive_summary"],
                        signal_strength=row["signal_strength"],
                        scoring_method=row.get("scoring_method", "ML/analytics-based"),
                        llm_used_for_score=row.get("llm_used_for_score", False),
                        score_features=row.get("score_features", {}),
                        source_notes=row["source_notes"],
                        created_at=row["created_at"],
                        updated_at=row["updated_at"],
                    )
                    for row in snapshot["live_trends"]
                ]
            )
            session.add_all(
                [
                    IndustryCompetitor(
                        competitor_name=row["name"],
                        focus_area=row["focus_area"],
                        activity_summary=row["activity_summary"],
                        market_momentum_score=row["momentum_score"],
                        positioning=row["strategic_position"],
                        source_notes=row["source_notes"],
                        created_at=row["created_at"],
                        updated_at=row["updated_at"],
                    )
                    for row in snapshot["competitor_cards"]
                ]
            )
            session.add_all(
                [
                    IndustryKeyword(
                        keyword=row["keyword"],
                        keyword_group=row["keyword_group"],
                        momentum_score=row["momentum_score"],
                        growth_score=row["growth_score"],
                        source_count=row["source_count"],
                        last_updated=row["last_updated"],
                        executive_summary=row["executive_summary"],
                        scoring_method=row.get("scoring_method", "ML/analytics-based"),
                        llm_used_for_score=row.get("llm_used_for_score", False),
                        score_features=row.get("score_features", {}),
                        source_notes=row["source_notes"],
                        created_at=row["created_at"],
                        updated_at=row["updated_at"],
                    )
                    for row in snapshot["keywords"]
                ]
            )
            session.add_all(
                [
                    IndustryCompetitorActivity(
                        name=row["name"],
                        focus_area=row["focus_area"],
                        activity_summary=row["activity_summary"],
                        momentum_score=row["momentum_score"],
                        strategic_position=row["strategic_position"],
                        threat_score=row.get("threat_score", row["momentum_score"]),
                        confidence_score=row.get("confidence_score", row.get("threat_score", row["momentum_score"])),
                        evidence_count=row.get("evidence_count", 0),
                        source_count=row.get("source_count", 0),
                        source_names=row.get("source_names", []),
                        source_timestamps=row.get("source_timestamps", []),
                        recent_signals=row.get("recent_signals", []),
                        strengths=row.get("strengths", []),
                        weaknesses=row.get("weaknesses", []),
                        strategic_recommendations=row.get("strategic_recommendations", []),
                        gap_analysis=row.get("gap_analysis", {}),
                        score_reason=row.get("score_reason", ""),
                        scoring_method=row.get("scoring_method", "ML/analytics-based"),
                        llm_used_for_score=row.get("llm_used_for_score", False),
                        score_features=row.get("score_features", {}),
                        last_updated=row["last_updated"],
                        source_notes=row["source_notes"],
                        created_at=row["created_at"],
                        updated_at=row["updated_at"],
                    )
                    for row in snapshot["competitor_cards"]
                ]
            )
            session.add_all(
                [
                    IndustryInsight(
                        insight_title=row["insight_title"],
                        what_is_trending=row["what_is_trending"],
                        why_it_matters=row["why_it_matters"],
                        business_impact=row["business_impact"],
                        recommended_action=row["recommended_action"],
                        priority=row["priority"],
                        insight_type=row["insight_type"],
                        source_notes=row["source_notes"],
                    )
                    for row in snapshot["insights"]
                ]
            )
            session.add_all(
                [
                    IndustryRecommendation(
                        trend=row["trend"],
                        reason=row["reason"],
                        impact=row["impact"],
                        recommended_action=row["recommended_action"],
                        confidence_score=row["confidence_score"],
                        scoring_method=row.get("scoring_method", "ML/analytics-based"),
                        llm_used_for_score=row.get("llm_used_for_score", False),
                        score_features=row.get("score_features", {}),
                        last_updated=row["last_updated"],
                        source_notes=row["source_notes"],
                        created_at=row["created_at"],
                        updated_at=row["updated_at"],
                    )
                    for row in snapshot["recommendations"]
                ]
            )
            session.add_all(
                [
                    IndustryOpportunity(
                        opportunity_name=row["opportunity_name"],
                        trend_name=row["trend_name"],
                        summary=row["summary"],
                        target_buyer=row["target_buyer"],
                        business_value=row["business_value"],
                        urgency=row["urgency"],
                        opportunity_score=row["opportunity_score"],
                        confidence_score=row.get("confidence_score", row["opportunity_score"]),
                        confidence_reason=row.get("confidence_reason", ""),
                        evidence_count=row.get("evidence_count", 0),
                        source_count=row.get("source_count", 0),
                        source_names=row.get("source_names", []),
                        source_timestamps=row.get("source_timestamps", []),
                        evidence_sources=row.get("evidence_sources", []),
                        supporting_evidence=row.get("supporting_evidence", []),
                        signal_inputs=row.get("signal_inputs", {}),
                        scoring_method=row.get("scoring_method", "ML/analytics-based"),
                        llm_used_for_score=row.get("llm_used_for_score", False),
                        score_features=row.get("score_features", {}),
                        source_notes=row["source_notes"],
                        created_at=row.get("created_at"),
                        updated_at=row.get("updated_at"),
                    )
                    for row in snapshot["opportunities"]
                ]
            )
            session.add(IndustryReport(**snapshot["report"]))
            session.add_all([IndustryRAGDocument(**row) for row in snapshot["documents"]])
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def _retrieve_rag_documents(self, query: str, limit: int = 6) -> list[dict[str, Any]]:
        session = get_db_session()
        try:
            rows = session.query(IndustryRAGDocument).order_by(IndustryRAGDocument.relevance_score.desc(), IndustryRAGDocument.id.desc()).all()
            query_tokens = set(self._extract_keywords(query, minimum=2))
            scored: list[dict[str, Any]] = []
            for row in rows:
                haystack = " ".join([row.title or "", row.content or "", json.dumps(row.metadata_json or {}, default=str)])
                score = self._document_score(query_tokens, haystack, row.relevance_score or 0.0)
                if score <= 0:
                    continue
                scored.append(
                    {
                        "doc_type": row.doc_type,
                        "source_name": row.source_name,
                        "title": row.title,
                        "content": row.content,
                        "metadata": row.metadata_json or {},
                        "relevance_score": round(score, 2),
                        "created_at": row.created_at.isoformat() if row.created_at else None,
                    }
                )
            scored.sort(key=lambda item: item["relevance_score"], reverse=True)
            return scored[:limit]
        finally:
            session.close()

    def _build_rag_analysis(self, query: str, documents: list[dict[str, Any]], snapshot: dict[str, Any]) -> dict[str, Any]:
        context = json.dumps(documents, ensure_ascii=False, indent=2)
        prompt = (
            "You are the Industry Intelligence RAG engine for an AI governance and enterprise AI dashboard. "
            "Use the provided documents to answer with executive reasoning. "
            "Return ONLY valid JSON with these keys: trend_reasoning, competitor_reasoning, executive_recommendations, conclusion.\n"
            f"Query: {query}\n"
            f"Documents:\n{context}\n"
            "Use the context to explain what the market signal means for Giggso."
        )
        parsed = self._generate_gemini_json(prompt)
        if isinstance(parsed, dict):
            return {
                "query": query,
                "documents": documents,
                "trend_reasoning": _clean_text(parsed.get("trend_reasoning")) or self._default_rag_reasoning(query, documents, snapshot),
                "competitor_reasoning": _clean_text(parsed.get("competitor_reasoning")) or "Competitor movement confirms that governance and security are now part of the enterprise AI buying process.",
                "executive_recommendations": self._normalize_text_list(parsed.get("executive_recommendations")) or self._default_rag_recommendations(snapshot),
                "conclusion": _clean_text(parsed.get("conclusion")) or "Giggso should position governance controls as a growth lever for enterprise AI adoption.",
                "generated_at": _NOW().isoformat(),
            }
        return {
            "query": query,
            "documents": documents,
            "trend_reasoning": self._default_rag_reasoning(query, documents, snapshot),
            "competitor_reasoning": "Competitors are moving toward safe, enterprise-ready AI platforms, which increases demand for governance proof and security validation.",
            "executive_recommendations": self._default_rag_recommendations(snapshot),
            "conclusion": "The strongest near-term opportunity is to lead with governance, security, and monitoring as the path to production AI.",
            "generated_at": _NOW().isoformat(),
        }

    def _build_search_intelligence(self, query: str, snapshot: dict[str, Any], persist_history: bool = True) -> dict[str, Any]:
        query_tokens = self._extract_keywords(query, minimum=2)
        query_type = self.detect_query_type(query)
        alias_terms = self._search_alias_terms(query, query_type=query_type)
        search_terms = self._unique_ordered([query, *query_tokens, *alias_terms], limit=16)
        query_lower = query.lower()
        company = snapshot.get("company") or {}
        company_signals = snapshot.get("company_signals") or {}
        linkedin_posts = snapshot.get("linkedin_posts") or []
        news = snapshot.get("news") or []
        competitor_cards = snapshot.get("competitor_cards") or []
        keywords = snapshot.get("keywords") or []

        keyword_weights: dict[str, float] = {}

        def add_keyword(term: str, weight: float) -> None:
            normalized = _clean_text(term)
            if not normalized:
                return
            key = normalized.lower()
            keyword_weights[key] = max(keyword_weights.get(key, 0.0), weight)

        def boost_keywords(items: list[str], base_weight: float = 1.0) -> None:
            for item in items:
                for token in self._extract_keywords(item, minimum=1):
                    add_keyword(token, base_weight)

        company_blob = " ".join(
            [
                company.get("company_name", ""),
                company.get("overview", ""),
                company.get("industry_positioning", ""),
                company.get("strategic_direction", ""),
                company.get("market_narrative", ""),
                " ".join(company.get("focus_keywords", [])),
                " ".join(company.get("content_themes", [])),
                " ".join(company.get("strategic_themes", [])),
                " ".join(company_signals.get("core_services", [])),
            ]
        )
        company_hits = self._search_hit_score(company_blob, search_terms)
        boost_keywords(company.get("focus_keywords", []), 2.0)
        boost_keywords(company.get("strategic_themes", []), 1.6)
        boost_keywords(company.get("content_themes", []), 1.4)
        boost_keywords(alias_terms, 3.4)
        for alias in alias_terms:
            add_keyword(alias, 12.0)
        for term in self._expected_keywords_for_query(query):
            add_keyword(term, 11.0)

        query_support_terms = {
            "claude": ["AI Safety", "Trustworthy AI", "Enterprise AI", "Claude 4"],
            "chatgpt": ["OpenAI", "Enterprise AI", "AI Assistant", "GPT-4o"],
            "gemini": ["Google DeepMind", "Enterprise AI", "Multimodal AI", "Model Monitoring"],
            "openai": ["GPT-4o", "Agentic AI", "Enterprise AI", "AI Governance"],
            "anthropic": ["Claude", "AI Safety", "Trustworthy AI", "Enterprise AI"],
            "rag": ["Retrieval", "Grounding", "Citations", "Enterprise AI"],
            "mcp": ["Model Context Protocol", "Agentic AI", "Workflow Orchestration", "AI Workflows"],
            "agentic ai": ["AI Agents", "Multi-Agent Systems", "MCP", "AI Workflows"],
            "autonomous systems": ["Agentic AI", "AI Agents", "MCP", "Multi-Agent Systems", "AI Workflows"],
        }
        for needle, terms in query_support_terms.items():
            if needle in query_lower:
                boost_keywords(terms, 2.6)
                for term in terms:
                    add_keyword(term, 10.5)

        matched_keywords: list[dict[str, Any]] = []
        for item in keywords:
            keyword_text = item.get("keyword", "")
            haystack = " ".join(
                [
                    keyword_text,
                    item.get("keyword_group", ""),
                    item.get("executive_summary", ""),
                    " ".join(item.get("source_notes", []) or []),
                ]
            )
            score = self._search_hit_score(haystack, search_terms)
            if score <= 0 and query_lower not in keyword_text.lower():
                continue
            matched_keywords.append(item)
            add_keyword(keyword_text, 8.0 + score + _safe_number(item.get("momentum_score"), 0.0) / 20.0)

        matched_keyword_names = [item.get("keyword", "") for item in matched_keywords]

        matched_posts: list[dict[str, Any]] = []
        for item in linkedin_posts:
            haystack = " ".join([item.get("content", ""), item.get("title", ""), item.get("author", ""), item.get("source", "")])
            score = self._search_hit_score(haystack, search_terms)
            if score <= 0:
                continue
            matched_posts.append({**item, "_score": score})
            boost_keywords([item.get("content", ""), item.get("title", "")], 1.2 + score / 2.0)

        matched_news: list[dict[str, Any]] = []
        for item in news:
            haystack = " ".join([item.get("headline", ""), item.get("summary", ""), item.get("source", "")])
            score = self._search_hit_score(haystack, search_terms)
            if score <= 0:
                continue
            matched_news.append({**item, "_score": score})
            boost_keywords([item.get("headline", ""), item.get("summary", "")], 1.3 + score / 2.0)

        live_news = self._google_news_rss(query, limit=5)
        if "autonomous systems" in query_lower or ("autonomous" in query_lower and query_type == "Technology"):
            supplemental_queries = [
                "Agentic AI enterprise",
                "AI agents enterprise",
                "MCP enterprise AI",
                "multi-agent systems enterprise AI",
            ]
            for supplemental_query in supplemental_queries:
                live_news.extend(self._google_news_rss(supplemental_query, limit=2))
        for item in live_news:
            haystack = " ".join([item.get("headline", ""), item.get("summary", ""), item.get("source", "")])
            score = self._search_hit_score(haystack, search_terms)
            domain_alignment = self._news_domain_alignment(query, haystack)
            if score <= 0 and query_lower not in haystack.lower() and domain_alignment <= 0:
                continue
            if domain_alignment < -10.0:
                continue
            matched_news.append({**item, "_score": score + 2.0 + domain_alignment / 5.0})
            boost_keywords([item.get("headline", ""), item.get("summary", "")], 1.6 + score / 2.0)

        unique_news = self._dedupe_search_items(matched_news, key_fields=("headline", "source"), limit=5)
        if not unique_news and live_news:
            unique_news = self._dedupe_search_items(live_news, key_fields=("headline", "source"), limit=5)

        matched_competitors: list[dict[str, Any]] = []
        for item in competitor_cards:
            haystack = " ".join(
                [
                    item.get("name", ""),
                    item.get("focus_area", ""),
                    item.get("activity_summary", ""),
                    item.get("strategic_position", ""),
                    " ".join(item.get("source_notes", []) or []),
                ]
            )
            score = self._search_hit_score(haystack, search_terms)
            if score <= 0 and not self._competitor_query_overlap(query_lower, haystack):
                continue
            matched_competitors.append({**item, "_score": score})
            add_keyword(item.get("name", ""), 10.0 + score)
            boost_keywords([item.get("focus_area", ""), item.get("strategic_position", ""), item.get("activity_summary", "")], 1.2 + score / 2.0)

        if not matched_competitors:
            live_competitor_snippets = self._bing_search(query, limit=5)
            for item in live_competitor_snippets:
                haystack = " ".join([item.get("title", ""), item.get("snippet", ""), item.get("content", "")])
                score = self._search_hit_score(haystack, search_terms)
                if score <= 0:
                    continue
                for competitor in COMPETITOR_CONFIG:
                    competitor_terms = " ".join([competitor["name"], competitor["focus_area"], competitor["positioning"], competitor["search_query"]])
                    if self._search_hit_score(competitor_terms, search_terms) <= 0 and competitor["name"].lower() not in haystack.lower():
                        continue
                    matched_competitors.append(
                        {
                            "name": competitor["name"],
                            "focus_area": competitor["focus_area"],
                            "activity_summary": item.get("snippet") or item.get("title") or competitor["positioning"],
                            "momentum_score": industry_analytics_scoring_engine.score(
                                "momentum",
                                self._search_score_features(
                                    company_hits=1.0,
                                    news_count=1,
                                    linkedin_count=0,
                                    competitor_count=1,
                                    rag_relevance=score * 10.0,
                                    keyword_count=1,
                                    recency_score=10.0,
                                    query_type="Company",
                                    query=competitor["name"],
                                ),
                            )["score"],
                            "strategic_position": competitor["positioning"],
                            "last_updated": _NOW().isoformat(),
                            "source_notes": [item.get("title", ""), item.get("snippet", "")],
                            "_score": score,
                        }
                    )
                    add_keyword(competitor["name"], 10.0 + score)
                    break

        if not matched_competitors:
            for item in COMPETITOR_CONFIG:
                if self._search_hit_score(" ".join([item["name"], item["focus_area"], item["positioning"]]), search_terms) > 0:
                    matched_competitors.append(
                        {
                            "name": item["name"],
                            "focus_area": item["focus_area"],
                            "activity_summary": item["positioning"],
                            "momentum_score": industry_analytics_scoring_engine.score(
                                "momentum",
                                self._search_score_features(
                                    company_hits=1.0,
                                    news_count=0,
                                    linkedin_count=0,
                                    competitor_count=1,
                                    rag_relevance=25.0,
                                    keyword_count=1,
                                    recency_score=8.0,
                                    query_type="Company",
                                    query=item["name"],
                                ),
                            )["score"],
                            "strategic_position": item["positioning"],
                            "last_updated": _NOW().isoformat(),
                            "source_notes": [item["search_query"]],
                            "_score": 1.0,
                        }
                    )

        rag_documents = self._retrieve_rag_documents(query, limit=8)
        rag_relevance = max([_safe_number(doc.get("relevance_score"), 0.0) for doc in rag_documents], default=0.0)
        for doc in rag_documents:
            add_keyword(doc.get("title", ""), 1.0 + _safe_number(doc.get("relevance_score"), 0.0) / 20.0)
            boost_keywords([doc.get("title", ""), doc.get("content", "")], 0.8 + _safe_number(doc.get("relevance_score"), 0.0) / 30.0)

        if company_hits > 0:
            boost_keywords(company.get("focus_keywords", []), 2.5)

        related_keywords = self._rank_related_keywords(keyword_weights, matched_keyword_names, query_tokens, search_terms)
        query_priority_terms = {
            "claude": ["Anthropic", "Claude 4", "AI Safety", "Trustworthy AI"],
            "chatgpt": ["OpenAI", "GPT-4o", "AI Assistant", "Enterprise AI"],
            "gemini": ["Google DeepMind", "Multimodal AI", "Enterprise AI", "Model Monitoring"],
            "openai": ["GPT-4o", "Enterprise AI", "Agentic AI", "AI Governance"],
            "anthropic": ["Claude", "AI Safety", "Trustworthy AI", "Enterprise AI"],
            "rag": ["Retrieval", "Grounding", "Citations", "Enterprise AI"],
            "mcp": ["Model Context Protocol", "Agentic AI", "Workflow Orchestration", "AI Workflows"],
            "agentic ai": ["AI Agents", "Multi-Agent Systems", "MCP", "AI Workflows"],
            "autonomous systems": ["Agentic AI", "AI Agents", "MCP", "Multi-Agent Systems", "AI Workflows"],
        }
        for needle, terms in query_priority_terms.items():
            if needle in query_lower:
                related_keywords = self._unique_ordered(
                    [*terms, *self._expected_keywords_for_query(query), *related_keywords],
                    limit=8,
                )
                break
        recency_score = self._search_recency_score(unique_news, matched_posts, matched_competitors)
        source_coverage = self._search_source_coverage(
            company_hits=company_hits,
            news_count=len(unique_news),
            linkedin_count=len(matched_posts),
            competitor_count=len(matched_competitors),
            rag_count=len(rag_documents),
            keyword_count=len(matched_keywords),
        )
        article_count = len(unique_news)
        mention_count = len(matched_posts) + len(matched_competitors) + len(matched_keywords)
        evidence_count = article_count + mention_count + len(rag_documents)
        evidence_sources = self._unique_ordered(
            [
                *source_coverage,
                *(item.get("source", "") for item in unique_news),
                *(item.get("source", "") for item in matched_posts),
                *(item.get("name", "") for item in matched_competitors),
                *(item.get("title", "") for item in rag_documents),
            ],
            limit=12,
        )
        evidence_timestamps = [
            item.get("published_date") or item.get("published_at") or item.get("date") or item.get("last_updated")
            for item in [
                *unique_news,
                *matched_posts,
                *matched_competitors,
                *rag_documents,
            ]
        ]
        evidence_timestamps = [value for value in evidence_timestamps if value]

        if evidence_count < 2 or not source_coverage:
            insufficient = self._insufficient_evidence_response(
                query=query,
                query_type=query_type,
                recent_news=unique_news,
                competitor_mentions=self._dedupe_search_items(matched_competitors, key_fields=("name",), limit=6),
                source_names=evidence_sources or source_coverage,
                timestamp=_NOW().isoformat(),
                source_count=len(source_coverage),
                evidence_count=evidence_count,
            )
            insufficient["article_count"] = article_count
            insufficient["mention_count"] = mention_count
            insufficient["source_timestamps"] = self._unique_ordered(
                [(_parse_datetime(value) or _NOW()).isoformat() for value in evidence_timestamps if value],
                limit=12,
            )
            insufficient["confidence_reason"] = "Insufficient evidence available."
            return insufficient

        trend_score = self._calculate_search_trend_score(
            company_hits=company_hits,
            news_count=len(unique_news),
            linkedin_count=len(matched_posts),
            competitor_count=len(matched_competitors),
            rag_relevance=rag_relevance,
            keyword_count=len(matched_keywords),
            recency_score=recency_score,
            query_type=query_type,
            query=query,
        )
        growth_score = self._calculate_search_growth_score(
            trend_score=trend_score,
            news_count=len(unique_news),
            linkedin_count=len(matched_posts),
            competitor_count=len(matched_competitors),
            recency_score=recency_score,
        )
        momentum = self._trend_momentum_label(trend_score)
        confidence_score = self._calculate_search_confidence(
            trend_score=trend_score,
            source_count=len(source_coverage),
            matched_items=len(unique_news) + len(matched_posts) + len(matched_competitors) + len(matched_keywords) + len(rag_documents),
            recency_score=recency_score,
            query_type=query_type,
        )
        score_features = self._search_score_features(
            company_hits=company_hits,
            news_count=len(unique_news),
            linkedin_count=len(matched_posts),
            competitor_count=len(matched_competitors),
            rag_relevance=rag_relevance,
            keyword_count=len(matched_keywords),
            recency_score=recency_score,
            query_type=query_type,
            query=query,
        )

        executive_summary = self._generate_search_executive_summary(
            query=query,
            trend_score=trend_score,
            growth_score=growth_score,
            momentum=momentum,
            related_keywords=related_keywords,
            news=unique_news,
            competitor_mentions=matched_competitors,
            rag_documents=rag_documents,
            company=company,
        )
        recommendation = self._generate_search_recommendation(
            query=query,
            momentum=momentum,
            related_keywords=related_keywords,
            competitor_mentions=matched_competitors,
            company=company,
        )
        evidence_meta = self._evidence_metadata(
            article_count=article_count,
            mention_count=mention_count,
            source_notes=evidence_sources,
            source_timestamps=evidence_timestamps,
            source_count=len(source_coverage),
            recency_score=recency_score,
            last_updated=_NOW().isoformat(),
        )

        result = {
            "query": query,
            "query_type": query_type,
            "trend_score": trend_score,
            "momentum": momentum,
            "growth_score": growth_score,
            "related_keywords": related_keywords,
            "recent_news": unique_news,
            "competitor_mentions": self._dedupe_search_items(matched_competitors, key_fields=("name",), limit=6),
            "executive_summary": executive_summary,
            "recommendation": recommendation,
            "confidence_score": confidence_score,
            "source_coverage": source_coverage,
            "source_count": evidence_meta["source_count"],
            "news_count": len(unique_news),
            "rag_match_count": len(rag_documents),
            "competitor_mention_count": len(matched_competitors),
            "article_count": evidence_meta["article_count"],
            "mention_count": evidence_meta["mention_count"],
            "evidence_count": evidence_meta["evidence_count"],
            "evidence_sources": evidence_meta["evidence_sources"],
            "source_names": evidence_meta["source_names"],
            "source_timestamps": evidence_meta["source_timestamps"],
            "last_updated": evidence_meta["last_updated"],
            "timestamp": evidence_meta["timestamp"],
            "confidence_reason": evidence_meta["confidence_reason"],
            "score_features": score_features,
            "scoring_method": "ML/analytics-based",
            "llm_used_for_score": False,
        }
        if persist_history:
            self._capture_trend_history_entry(result)
        return result

    def _capture_trend_history_entry(self, result: dict[str, Any]) -> None:
        keyword = _clean_text(result.get("query"))
        if not keyword:
            return
        save_trend_history([
            {
                "keyword": keyword,
                "trend_score": result.get("trend_score"),
                "growth_score": result.get("growth_score"),
                "confidence_score": result.get("confidence_score"),
                "momentum": result.get("momentum"),
                "source_count": result.get("source_count"),
                "news_count": result.get("news_count"),
                "rag_match_count": result.get("rag_match_count"),
                "competitor_mention_count": result.get("competitor_mention_count"),
                "timestamp": _parse_datetime(result.get("timestamp")) or _NOW(),
            }
        ])

    def _capture_trend_history_snapshot(self, snapshot: dict[str, Any], now: datetime) -> None:
        keywords = [
            "ChatGPT",
            "Claude",
            "Gemini",
            "OpenAI",
            "Anthropic",
            "RAG",
            "MCP",
            "Agentic AI",
            "Autonomous Systems",
            "AI Governance",
            "AI Security",
            "LLM Security",
            "Enterprise AI",
            "Model Monitoring",
            "Trustworthy AI",
        ]
        entries: list[dict[str, Any]] = []
        for keyword in keywords:
            analysis = self._build_search_intelligence(keyword, snapshot, persist_history=False)
            entries.append(
                {
                    "keyword": keyword,
                    "trend_score": analysis.get("trend_score"),
                    "growth_score": analysis.get("growth_score"),
                    "confidence_score": analysis.get("confidence_score"),
                    "momentum": analysis.get("momentum"),
                    "source_count": analysis.get("source_count"),
                    "news_count": analysis.get("news_count"),
                    "rag_match_count": analysis.get("rag_match_count"),
                    "competitor_mention_count": analysis.get("competitor_mention_count"),
                    "timestamp": now,
                }
            )
        save_trend_history(entries)

    def detect_query_type(self, query: str) -> str:
        text = _clean_text(query).lower()
        if not text:
            return "Concept"

        security_terms = (
            "security",
            "safe",
            "safety",
            "prompt injection",
            "red team",
            "guardrail",
            "vulnerability",
            "llm security",
        )
        governance_terms = (
            "governance",
            "compliance",
            "policy",
            "audit",
            "risk",
            "trustworthy",
        )
        model_terms = (
            "gpt",
            "claude",
            "gemini",
            "llama",
            "mistral",
            "deepseek",
            "qwen",
            "model",
        )
        company_terms = (
            "openai",
            "anthropic",
            "google",
            "deepmind",
            "microsoft",
            "perplexity",
            "cohere",
            "giggso",
        )
        technology_terms = (
            "mcp",
            "rag",
            "agent",
            "agentic",
            "multi-agent",
            "autonomous",
            "workflow",
            "orchestration",
            "vector",
            "embedding",
            "retrieval",
        )

        if any(term in text for term in security_terms):
            return "Security"
        if any(term in text for term in governance_terms):
            return "Governance"
        if any(term in text for term in model_terms):
            return "AI Model"
        if any(term in text for term in company_terms):
            return "Company"
        if any(term in text for term in technology_terms):
            return "Technology"
        return "Concept"

    def _generate_gemini_json(self, prompt: str) -> Any:
        if self.gemini_service._client is None:
            return None

        try:
            model = self.gemini_service._client.GenerativeModel("gemini-2.5-flash")
            response = model.generate_content(prompt)
            parsed = self._parse_json(getattr(response, "text", ""))
            if parsed is not None:
                return parsed
        except Exception as exc:
            logger.warning("Gemini generation failed: %s", exc)
        return None

    def _default_rag_reasoning(self, query: str, documents: list[dict[str, Any]], snapshot: dict[str, Any]) -> str:
        top_docs = ", ".join(doc.get("title", "") for doc in documents[:3]) or "current intelligence documents"
        return (
            f"The query '{query}' is strongly supported by {top_docs}, reinforcing the theme that AI governance, security, and compliance are converging into a production requirement for enterprise buyers."
        )

    def _default_rag_recommendations(self, snapshot: dict[str, Any]) -> list[str]:
        return [
            "Package governance, security, and compliance checks into one enterprise story.",
            "Use monitoring and auditability to shorten regulated buyer evaluation cycles.",
            "Frame agentic AI adoption as safe only when controls and evidence are visible.",
        ]

    def _search_alias_terms(self, query: str, query_type: str | None = None) -> list[str]:
        query_lower = _clean_text(query).lower()
        aliases = {
            "claude": ["Anthropic", "Claude 4", "Claude AI", "AI safety"],
            "chatgpt": ["OpenAI", "GPT-4o", "GPT-5", "enterprise AI"],
            "gemini": ["Google", "Google DeepMind", "Gemini 2.5", "multimodal AI"],
            "mcp": ["Model Context Protocol", "tool calling", "agentic workflows"],
            "autonomous systems": ["Agentic AI", "Multi-Agent Systems", "MCP", "AI workflows", "autonomous agents"],
            "rag": ["retrieval augmented generation", "grounded retrieval", "citations"],
            "agentic ai": ["agents", "autonomous workflows", "workflow orchestration"],
            "ai governance": ["policy controls", "audit trails", "compliance", "trustworthy ai"],
            "llm security": ["prompt injection", "model security", "red teaming"],
            "ai compliance": ["regulatory", "auditability", "controls"],
            "ai risk": ["model risk", "data risk", "operational risk"],
            "perplexity": ["AI search", "answer engine", "enterprise search"],
        }
        terms: list[str] = []
        for needle, values in aliases.items():
            if needle in query_lower:
                terms.extend(values)
        query_type_key = _clean_text(query_type).lower()
        type_terms = {
            "ai model": ["model", "version", "release", "benchmark", "training", "capabilities"],
            "company": ["strategy", "positioning", "funding", "enterprise AI", "product messaging"],
            "technology": ["architecture", "stack", "integration", "workflow", "orchestration", "MCP", "RAG"],
            "concept": ["use cases", "adoption", "industry trends", "enterprise AI", "operations"],
            "governance": ["policy controls", "audit trails", "compliance", "governance", "risk"],
            "security": ["threats", "red team", "prompt injection", "model security", "guardrails"],
        }
        if query_type_key in type_terms:
            terms.extend(type_terms[query_type_key])
        return self._unique_ordered(terms, limit=12)

    def _query_signal_boost(self, query_type: str, query: str) -> float:
        query_lower = _clean_text(query).lower()
        boosts = {
            "AI Model": 18.0,
            "Company": 16.0,
            "Technology": 14.0,
            "Concept": 10.0,
            "Governance": 15.0,
            "Security": 15.0,
        }
        boost = boosts.get(query_type, 8.0)
        if any(term in query_lower for term in ("claude", "chatgpt", "gemini", "openai", "anthropic", "mcp", "agentic ai")):
            boost += 6.0
        return boost

    def _search_recency_score(
        self,
        news: list[dict[str, Any]],
        linkedin: list[dict[str, Any]],
        competitors: list[dict[str, Any]],
    ) -> float:
        def item_age_score(value: Any) -> float:
            dt = _parse_datetime(value)
            if not dt:
                return 0.0
            age_days = max(0.0, (_NOW() - dt).total_seconds() / 86400.0)
            if age_days <= 2:
                return 10.0
            if age_days <= 7:
                return 7.0
            if age_days <= 14:
                return 4.0
            if age_days <= 30:
                return 2.0
            return 0.0

        scores = []
        for item in (news or [])[:5]:
            scores.append(item_age_score(item.get("published_date") or item.get("date") or item.get("last_updated")))
        for item in (linkedin or [])[:5]:
            scores.append(item_age_score(item.get("published_date") or item.get("date") or item.get("last_updated")))
        for item in (competitors or [])[:5]:
            scores.append(item_age_score(item.get("last_updated") or item.get("published_date") or item.get("date")))
        return min(20.0, sum(scores))

    def _search_hit_score(self, text: str, terms: list[str]) -> float:
        if not text:
            return 0.0
        lowered = str(text).lower()
        score = 0.0
        for term in terms:
            term_text = _clean_text(term).lower()
            if not term_text:
                continue
            if term_text in lowered:
                score += 1.0 + min(2.5, len(term_text) / 12.0)
        return score

    def _competitor_query_overlap(self, query_lower: str, text: str) -> bool:
        text_lower = _clean_text(text).lower()
        if not query_lower or not text_lower:
            return False
        if query_lower in text_lower or text_lower in query_lower:
            return True
        query_bits = {part for part in re.split(r"[\s,/.-]+", query_lower) if len(part) > 2}
        text_bits = {part for part in re.split(r"[\s,/.-]+", text_lower) if len(part) > 2}
        return bool(query_bits & text_bits)

    def _rank_related_keywords(
        self,
        keyword_weights: dict[str, float],
        matched_keyword_names: list[str],
        query_tokens: list[str],
        search_terms: list[str],
    ) -> list[str]:
        generic_terms = {
            "ai",
            "for",
            "systems",
            "model",
            "models",
            "version",
            "release",
            "strategy",
            "solution",
            "platform",
            "technology",
            "tools",
            "tech",
            "service",
            "services",
            "company",
            "software",
            "product",
            "products",
            "enterprise",
            "content",
        }
        for token in query_tokens:
            key = _clean_text(token).lower()
            if key:
                keyword_weights[key] = max(keyword_weights.get(key, 0.0), 8.0)
        for term in search_terms:
            key = _clean_text(term).lower()
            if key:
                keyword_weights[key] = max(keyword_weights.get(key, 0.0), 6.0)
        for keyword in matched_keyword_names:
            key = _clean_text(keyword).lower()
            if key:
                keyword_weights[key] = max(keyword_weights.get(key, 0.0), 10.0)
        ordered = sorted(keyword_weights.items(), key=lambda item: item[1], reverse=True)
        ranked: list[str] = []
        for term, _score in ordered:
            display = self._display_search_keyword(term)
            if not display:
                continue
            if display.lower() in generic_terms and len(ranked) >= 3:
                continue
            if display.lower() in generic_terms and len(keyword_weights) > 6:
                continue
            ranked.append(display)
        return self._unique_ordered(ranked, limit=8)

    def _display_search_keyword(self, term: str) -> str:
        normalized = _clean_text(term)
        if not normalized:
            return ""
        lower = normalized.lower()
        special = {
            "ai": "AI",
            "ai safety": "AI Safety",
            "llm": "LLM",
            "rag": "RAG",
            "mcp": "MCP",
            "claude": "Claude",
            "claude ai": "Claude AI",
            "chatgpt": "ChatGPT",
            "gemini": "Gemini",
            "openai": "OpenAI",
            "anthropic": "Anthropic",
            "google deepmind": "Google DeepMind",
            "perplexity": "Perplexity",
            "trustworthy ai": "Trustworthy AI",
            "model context protocol": "Model Context Protocol",
            "workflow orchestration": "Workflow Orchestration",
            "multi-agent systems": "Multi-Agent Systems",
            "ai agents": "AI Agents",
            "ai workflows": "AI Workflows",
        }
        if lower in special:
            return special[lower]
        display = normalized.title()
        display = re.sub(r"\bAi\b", "AI", display)
        return display

    def _search_source_coverage(
        self,
        *,
        company_hits: float,
        news_count: int,
        linkedin_count: int,
        competitor_count: int,
        rag_count: int,
        keyword_count: int,
    ) -> list[str]:
        coverage = []
        if company_hits > 0:
            coverage.append("Company Signals")
        if news_count > 0:
            coverage.append("Industry News")
        if linkedin_count > 0:
            coverage.append("LinkedIn Intelligence")
        if competitor_count > 0:
            coverage.append("Competitor Signals")
        if rag_count > 0:
            coverage.append("Industry RAG Documents")
        if keyword_count > 0:
            coverage.append("Keywords Database")
        return coverage

    def _evidence_source_names(self, *values: Any) -> list[str]:
        names: list[str] = []
        for value in values:
            if isinstance(value, (list, tuple, set)):
                for item in value:
                    text = _clean_text(item)
                    if text:
                        names.append(text)
            else:
                text = _clean_text(value)
                if text:
                    names.append(text)
        return self._unique_ordered(names, limit=12)

    def _latest_evidence_timestamp(self, *values: Any) -> str:
        timestamps: list[datetime] = []
        for value in values:
            if isinstance(value, (list, tuple, set)):
                for item in value:
                    dt = _parse_datetime(item)
                    if dt:
                        timestamps.append(dt)
            else:
                dt = _parse_datetime(value)
                if dt:
                    timestamps.append(dt)
        latest = max(timestamps) if timestamps else _NOW()
        return latest.isoformat()

    def _confidence_reason_text(
        self,
        *,
        article_count: int,
        mention_count: int,
        source_names: list[str],
        recency_score: float,
        insufficient: bool = False,
    ) -> str:
        if insufficient:
            return "Insufficient evidence available."
        parts = []
        if article_count:
            parts.append(f"{article_count} articles")
        if mention_count:
            parts.append(f"{mention_count} mentions")
        if source_names:
            parts.append(", ".join(source_names[:4]))
        if recency_score:
            parts.append(f"recency score {min(20.0, float(recency_score)):.0f}/20")
        if not parts:
            return "Insufficient evidence available."
        return "Evidence-backed from " + "; ".join(parts) + "."

    def _insufficient_evidence_response(
        self,
        *,
        query: str,
        query_type: str,
        recent_news: list[dict[str, Any]] | None = None,
        competitor_mentions: list[dict[str, Any]] | None = None,
        source_names: list[str] | None = None,
        timestamp: str | None = None,
        source_count: int = 0,
        evidence_count: int = 0,
    ) -> dict[str, Any]:
        return {
            "query": query,
            "query_type": query_type,
            "trend_score": 0,
            "momentum": "Low",
            "growth_score": 0,
            "related_keywords": [],
            "recent_news": recent_news or [],
            "competitor_mentions": competitor_mentions or [],
            "executive_summary": "Insufficient evidence available.",
            "recommendation": "Insufficient evidence available.",
            "confidence_score": 0,
            "source_coverage": source_names or [],
            "source_count": source_count,
            "evidence_count": evidence_count,
            "evidence_sources": source_names or [],
            "article_count": len(recent_news or []),
            "mention_count": len(competitor_mentions or []),
            "last_updated": timestamp or _NOW().isoformat(),
            "timestamp": timestamp or _NOW().isoformat(),
            "confidence_reason": "Insufficient evidence available.",
        }

    def _evidence_metadata(
        self,
        *,
        article_count: int = 0,
        mention_count: int = 0,
        source_notes: list[str] | None = None,
        source_timestamps: list[Any] | None = None,
        source_count: int = 0,
        recency_score: float = 0.0,
        last_updated: Any | None = None,
        insufficient: bool = False,
    ) -> dict[str, Any]:
        source_names = self._evidence_source_names(source_notes or [])
        timestamps: list[str] = []
        for value in source_timestamps or []:
            dt = _parse_datetime(value)
            if dt:
                timestamps.append(dt.isoformat())
        normalized_last_updated = _parse_datetime(last_updated) if last_updated is not None else None
        last_updated_text = (normalized_last_updated or _NOW()).isoformat()
        evidence_count = max(article_count + mention_count, source_count, len(source_names), len(timestamps))
        confidence_reason = (
            "Insufficient evidence available."
            if insufficient
            else self._confidence_reason_text(
                article_count=article_count,
                mention_count=mention_count,
                source_names=source_names,
                recency_score=recency_score,
            )
        )
        return {
            "article_count": article_count,
            "mention_count": mention_count,
            "source_count": source_count,
            "evidence_count": evidence_count,
            "source_names": source_names,
            "evidence_sources": source_names,
            "source_timestamps": self._unique_ordered(timestamps, limit=12),
            "last_updated": last_updated_text,
            "timestamp": last_updated_text,
            "confidence_reason": confidence_reason,
        }

    def _signal_recency_score(self, *values: Any) -> float:
        timestamps: list[datetime] = []
        for value in values:
            if isinstance(value, (list, tuple, set)):
                for item in value:
                    dt = _parse_datetime(item)
                    if dt:
                        timestamps.append(dt)
            else:
                dt = _parse_datetime(value)
                if dt:
                    timestamps.append(dt)
        if not timestamps:
            return 0.0
        latest = max(timestamps)
        age_days = max(0.0, (_NOW() - latest).total_seconds() / 86400.0)
        return self._clamp(12.0 - min(12.0, age_days * 1.2), 0.0, 12.0)

    def _signal_consistency_score(self, values: list[Any]) -> float:
        filtered = [self._clamp(_safe_number(value), 0.0, 100.0) for value in values if value is not None]
        if not filtered:
            return 0.0
        if len(filtered) == 1:
            return max(35.0, filtered[0])
        spread = pstdev(filtered)
        return self._clamp(100.0 - min(55.0, spread * 2.2), 0.0, 100.0)

    def _evidence_based_confidence(
        self,
        *,
        evidence_count: int,
        source_count: int,
        signal_consistency: float,
        trend_strength: float,
        historical_relevance: float,
        recency_score: float = 0.0,
    ) -> tuple[float, bool]:
        if evidence_count < 2 or source_count < 2:
            return 0.0, True
        evidence_band = self._clamp(evidence_count * 16.0, 0.0, 100.0)
        source_band = self._clamp(source_count * 12.0, 0.0, 100.0)
        trend_band = self._clamp(trend_strength, 0.0, 100.0)
        history_band = self._clamp(historical_relevance, 0.0, 100.0)
        recency_band = self._clamp(recency_score * 8.0, 0.0, 100.0)
        confidence = (
            evidence_band * 0.26
            + source_band * 0.18
            + signal_consistency * 0.20
            + trend_band * 0.18
            + history_band * 0.10
            + recency_band * 0.08
        )
        return round(self._clamp(confidence, 0.0, 100.0), 1), False

    def _calculate_search_trend_score(
        self,
        *,
        company_hits: float,
        news_count: int,
        linkedin_count: int,
        competitor_count: int,
        rag_relevance: float,
        keyword_count: int,
        recency_score: float = 0.0,
        query_type: str = "Concept",
        query: str = "",
    ) -> int:
        features = self._search_score_features(
            company_hits=company_hits,
            news_count=news_count,
            linkedin_count=linkedin_count,
            competitor_count=competitor_count,
            rag_relevance=rag_relevance,
            keyword_count=keyword_count,
            recency_score=recency_score,
            query_type=query_type,
            query=query,
        )
        return int(round(industry_analytics_scoring_engine.score("momentum", features)["score"]))

    def _calculate_search_growth_score(
        self,
        *,
        trend_score: int,
        news_count: int,
        linkedin_count: int,
        competitor_count: int,
        recency_score: float = 0.0,
    ) -> int:
        features = self._search_score_features(
            company_hits=max(0.0, trend_score / 12.0),
            news_count=news_count,
            linkedin_count=linkedin_count,
            competitor_count=competitor_count,
            rag_relevance=max(0.0, trend_score * 0.8),
            keyword_count=max(1.0, news_count + linkedin_count),
            recency_score=recency_score,
            query_type="Concept",
            query="growth",
        )
        return int(round(industry_analytics_scoring_engine.score("growth", features)["score"]))

    def _calculate_search_confidence(self, *, trend_score: int, source_count: int, matched_items: int, recency_score: float = 0.0, query_type: str = "Concept") -> int:
        features = self._search_score_features(
            company_hits=max(0.0, trend_score / 10.0),
            news_count=matched_items,
            linkedin_count=0,
            competitor_count=0,
            rag_relevance=source_count * 8.0,
            keyword_count=max(1.0, matched_items),
            recency_score=recency_score,
            query_type=query_type,
            query="confidence",
        )
        return int(round(industry_analytics_scoring_engine.score("product_impact", features)["confidence_score"]))

    def _trend_momentum_label(self, score: int) -> str:
        if score >= 75:
            return "High"
        if score >= 45:
            return "Moderate"
        return "Low"

    def _search_score_features(
        self,
        *,
        company_hits: float,
        news_count: int,
        linkedin_count: int,
        competitor_count: int,
        rag_relevance: float,
        keyword_count: int,
        recency_score: float = 0.0,
        query_type: str = "Concept",
        query: str = "",
    ) -> dict[str, float]:
        mention_count = max(0.0, company_hits + news_count + linkedin_count + competitor_count)
        source_count = max(0.0, company_hits + news_count + linkedin_count + competitor_count + keyword_count)
        evidence_count = max(1.0, source_count + max(0.0, rag_relevance / 10.0))
        trend_frequency = max(0.0, news_count + linkedin_count + competitor_count + keyword_count)
        keyword_relevance = max(0.0, min(100.0, (company_hits * 8.0) + (keyword_count * 9.0) + rag_relevance * 0.5))
        competitor_activity = max(0.0, min(100.0, competitor_count * 12.0 + max(0.0, rag_relevance * 0.1)))
        market_gap = max(0.0, min(100.0, 100.0 - competitor_activity - (keyword_count * 1.8)))
        historical_growth = max(0.0, min(100.0, (news_count * 6.0) + (linkedin_count * 5.0) + (competitor_count * 3.0) + recency_score * 1.2))
        return {
            "mention_count": mention_count,
            "source_count": source_count,
            "evidence_count": evidence_count,
            "recency_score": recency_score,
            "trend_frequency": trend_frequency,
            "keyword_relevance": keyword_relevance,
            "competitor_activity": competitor_activity,
            "market_gap": market_gap,
            "historical_growth": historical_growth,
            "query_type": query_type,
            "query_length": float(len(query or "")),
        }

    def _generate_search_executive_summary(
        self,
        *,
        query: str,
        trend_score: int,
        growth_score: int,
        momentum: str,
        related_keywords: list[str],
        news: list[dict[str, Any]],
        competitor_mentions: list[dict[str, Any]],
        rag_documents: list[dict[str, Any]],
        company: dict[str, Any],
    ) -> str:
        news_titles = [item.get("headline", "") for item in news[:4] if item.get("headline")]
        competitor_names = [item.get("name", "") for item in competitor_mentions[:4] if item.get("name")]
        rag_titles = [item.get("title", "") for item in rag_documents[:3] if item.get("title")]
        prompt = (
            "You are the executive search engine for an AI governance and enterprise AI intelligence dashboard. "
            "Return ONLY valid JSON with keys: executive_summary, recommendation. "
            "Write concise executive-level language.\n"
            f"Query: {query}\n"
            f"Trend score: {trend_score}\n"
            f"Growth score: {growth_score}\n"
            f"Momentum: {momentum}\n"
            f"Related keywords: {related_keywords}\n"
            f"News signals: {news_titles}\n"
            f"Competitor signals: {competitor_names}\n"
            f"RAG context: {rag_titles}\n"
            f"Company context: {company.get('market_narrative', '')}\n"
            "Explain why the topic is trending, why it matters, business impact, and strategic outlook."
        )
        parsed = self._generate_gemini_json(prompt)
        if isinstance(parsed, dict):
            summary = _clean_text(parsed.get("executive_summary"))
            if summary:
                return summary
        return self._fallback_search_summary(query, trend_score, momentum, related_keywords, news, competitor_mentions, rag_documents)

    def _generate_search_recommendation(
        self,
        *,
        query: str,
        momentum: str,
        related_keywords: list[str],
        competitor_mentions: list[dict[str, Any]],
        company: dict[str, Any],
    ) -> str:
        lower = query.lower()
        top_competitor = competitor_mentions[0].get("name", "the market") if competitor_mentions else ""
        top_focus = competitor_mentions[0].get("focus_area", "") if competitor_mentions else ""
        theme = related_keywords[0] if related_keywords else ""
        if any(term in lower for term in ("governance", "compliance", "risk", "security")):
            return "Position governance controls, auditability, and security evidence as the business advantage in enterprise buying conversations."
        if "agent" in lower:
            return "Frame agentic AI as safe only when approvals, guardrails, monitoring, and rollback controls are visible."
        if "rag" in lower:
            return "Lead with grounding, citations, retrieval quality, and data freshness to improve trust in enterprise assistants."
        if competitor_mentions:
            if any(term in lower for term in ("anthropic", "claude", "openai", "chatgpt", "gemini")):
                return (
                    f"Position governance, compliance, and observability capabilities against {top_competitor}'s {top_focus or 'enterprise AI'} messaging, "
                    f"and anchor the story in {theme or 'enterprise AI readiness'}."
                )
            return f"Use {top_competitor} as a market reference and show where {COMPANY_NAME} provides deeper governance control, deployment support, and evidence."
        if related_keywords:
            return f"Anchor the response in {related_keywords[0]} and tie it back to enterprise AI readiness, operating controls, and measurable business impact."
        if momentum == "High":
            return "Move quickly with a governance-first narrative, a practical implementation checklist, and an executive proof point for risk reduction."
        return company.get("strategic_direction") or "Use the signal to reinforce enterprise AI readiness, governance proof, and operational control."

    def _fallback_search_summary(
        self,
        query: str,
        trend_score: int,
        momentum: str,
        related_keywords: list[str],
        news: list[dict[str, Any]],
        competitor_mentions: list[dict[str, Any]],
        rag_documents: list[dict[str, Any]],
    ) -> str:
        lead_keyword = related_keywords[0] if related_keywords else query
        news_count = len(news)
        competitor_count = len(competitor_mentions)
        rag_count = len(rag_documents)
        return (
            f"{query} is trending at a {momentum.lower()} pace with a score of {trend_score}/100. "
            f"The signal is being reinforced by {news_count} recent news items, {competitor_count} competitor mentions, and {rag_count} RAG matches. "
            f"The strongest related theme is {lead_keyword}, which points to enterprise AI buying interest around governance, security, and deployment readiness."
        )

    def _comparison_strengths(
        self,
        left_query: str,
        right_query: str,
        left: dict[str, Any],
        right: dict[str, Any],
        left_type: str,
        right_type: str,
    ) -> list[str]:
        strengths: list[str] = []
        left_score = _safe_number(left.get("trend_score"))
        right_score = _safe_number(right.get("trend_score"))
        left_name = left.get("query") or left_query
        right_name = right.get("query") or right_query
        left_keywords = {self._normalize_overlap_keyword(item) for item in (left.get("related_keywords") or [])}
        right_keywords = {self._normalize_overlap_keyword(item) for item in (right.get("related_keywords") or [])}
        shared_themes = self._comparison_theme_overlap(left_query, right_query, left_keywords, right_keywords)

        if left_score > right_score + 5:
            strengths.append(f"{left_name} has the stronger current momentum signal.")
        elif right_score > left_score + 5:
            strengths.append(f"{right_name} has the stronger current momentum signal.")
        else:
            strengths.append("Both signals are moving at a similar pace, which suggests active market attention.")

        if left_type == "AI Model" and right_type != "AI Model":
            strengths.append(f"{left_name} is closer to model-layer differentiation and benchmark visibility.")
        if right_type == "AI Model" and left_type != "AI Model":
            strengths.append(f"{right_name} is closer to model-layer differentiation and benchmark visibility.")

        if left_type == "Company" and right_type != "Company":
            strengths.append(f"{left_name} benefits from broader platform, enterprise, and go-to-market context.")
        if right_type == "Company" and left_type != "Company":
            strengths.append(f"{right_name} benefits from broader platform, enterprise, and go-to-market context.")

        if any(term in left_query.lower() for term in ("governance", "security", "risk", "compliance")):
            strengths.append(f"{left_name} has a stronger trust, controls, and governance narrative.")
        if any(term in right_query.lower() for term in ("governance", "security", "risk", "compliance")):
            strengths.append(f"{right_name} has a stronger trust, controls, and governance narrative.")

        if shared_themes:
            strengths.append(f"Both signals share {shared_themes[0]}, which keeps the comparison relevant for enterprise buyers.")

        return self._unique_ordered(strengths, limit=4)

    def _comparison_weaknesses(
        self,
        left_query: str,
        right_query: str,
        left: dict[str, Any],
        right: dict[str, Any],
        left_type: str,
        right_type: str,
    ) -> list[str]:
        weaknesses: list[str] = []
        left_score = _safe_number(left.get("growth_score"))
        right_score = _safe_number(right.get("growth_score"))
        left_name = left.get("query") or left_query
        right_name = right.get("query") or right_query
        left_keywords = {self._normalize_overlap_keyword(item) for item in (left.get("related_keywords") or [])}
        right_keywords = {self._normalize_overlap_keyword(item) for item in (right.get("related_keywords") or [])}
        shared_themes = self._comparison_theme_overlap(left_query, right_query, left_keywords, right_keywords)

        if left_score + 5 < right_score:
            weaknesses.append(f"{left_name} appears less differentiated on growth and expansion signals.")
        if right_score + 5 < left_score:
            weaknesses.append(f"{right_name} appears less differentiated on growth and expansion signals.")

        if left_type == "AI Model" and right_type == "Company":
            weaknesses.append(f"{left_name} may need stronger enterprise positioning to compete with platform narratives.")
        if right_type == "AI Model" and left_type == "Company":
            weaknesses.append(f"{right_name} may need stronger enterprise positioning to compete with platform narratives.")

        if left_type in {"Technology", "Concept"}:
            weaknesses.append(f"{left_name} may need clearer productization or vendor ownership to convert attention into deals.")
        if right_type in {"Technology", "Concept"}:
            weaknesses.append(f"{right_name} may need clearer productization or vendor ownership to convert attention into deals.")

        if left_type == "Company" and right_type == "Company":
            if "giggso" in left_query.lower():
                weaknesses.append(f"{left_name} will need broader market proof beyond governance depth to compete with larger enterprise AI platforms.")
            elif "giggso" in right_query.lower():
                weaknesses.append(f"{right_name} will need broader market proof beyond governance depth to compete with larger enterprise AI platforms.")
            else:
                weaknesses.append(f"{left_name} and {right_name} both need stronger proof of enterprise deployment outcomes and customer traction.")

        if left_type == "AI Model" or right_type == "AI Model":
            model_name = left_name if left_type == "AI Model" else right_name
            company_name = right_name if left_type == "AI Model" else left_name
            weaknesses.append(f"{model_name} still depends on {company_name} to translate model capability into enterprise controls, support, and compliance evidence.")

        if any(term in left_query.lower() for term in ("autonomous", "agent", "rag")) and not any(
            term in left_query.lower() for term in ("security", "governance", "compliance")
        ):
            weaknesses.append(f"{left_name} could be exposed without explicit governance and security guardrails.")
        if any(term in right_query.lower() for term in ("autonomous", "agent", "rag")) and not any(
            term in right_query.lower() for term in ("security", "governance", "compliance")
        ):
            weaknesses.append(f"{right_name} could be exposed without explicit governance and security guardrails.")

        if not shared_themes:
            weaknesses.append("The comparison has limited shared enterprise themes, which reduces strategic comparability.")

        return self._unique_ordered(weaknesses, limit=4)

    def _generate_compare_executive_summary(
        self,
        *,
        left_query: str,
        right_query: str,
        left: dict[str, Any],
        right: dict[str, Any],
        overlap: list[str],
        strengths: list[str],
        weaknesses: list[str],
    ) -> str:
        prompt = (
            "You are the executive comparison engine for an AI governance and enterprise AI intelligence dashboard. "
            "Return ONLY valid JSON with keys: executive_summary. "
            "Write a concise board-style comparison in 2-4 sentences.\n"
            f"Compare: {left_query} vs {right_query}\n"
            f"Left signal: {left}\n"
            f"Right signal: {right}\n"
            f"Keyword overlap: {overlap}\n"
            f"Strengths: {strengths}\n"
            f"Weaknesses: {weaknesses}\n"
            "Explain which signal is stronger, why the comparison matters, and the strategic takeaway."
        )
        parsed = self._generate_gemini_json(prompt)
        if isinstance(parsed, dict):
            summary = _clean_text(parsed.get("executive_summary"))
            if summary:
                return summary

        left_score = _safe_number(left.get("trend_score"))
        right_score = _safe_number(right.get("trend_score"))
        winner = left_query if left_score >= right_score else right_query
        challenger = right_query if winner == left_query else left_query
        overlap_text = ", ".join(overlap[:4]) if overlap else "limited overlap"
        return (
            f"{winner} currently shows the stronger near-term signal versus {challenger}. "
            f"The comparison is most relevant around {overlap_text}, where both signals intersect on enterprise AI buying behavior. "
            f"Strategically, the clearer win is whichever side pairs momentum with governance, security, and deployment readiness."
        )

    def _comparison_display_name(self, query: str, fallback: str) -> str:
        text = _clean_text(query) or _clean_text(fallback)
        if not text:
            return "Signal"
        if "giggso" in text.lower():
            return "Giggso"
        return text

    def _comparison_advantage_points(self, query: str, query_type: str, score_delta: float = 0.0) -> list[str]:
        text = query.lower()
        points: list[str] = []
        if query_type == "AI Model":
            points.extend(["Model innovation", "Developer adoption", "Brand visibility"])
        elif query_type == "Company":
            points.extend(["Enterprise controls", "Go-to-market reach", "Procurement fit"])
        elif query_type == "Technology":
            points.extend(["Workflow integration", "Implementation flexibility", "Platform extensibility"])
        elif query_type == "Concept":
            points.extend(["Narrative breadth", "Cross-functional relevance", "Adoption timing"])
        elif query_type == "Governance":
            points.extend(["Policy automation", "Audit readiness", "Control coverage"])
        elif query_type == "Security":
            points.extend(["Protection depth", "Risk reduction", "Red-team readiness"])
        else:
            points.extend(["Enterprise credibility", "Deployment clarity", "Market relevance"])

        if any(term in text for term in ("governance", "compliance", "risk", "audit")):
            points.extend(["Governance", "Compliance", "Audit readiness"])
        if any(term in text for term in ("security", "safety", "guardrail", "trustworthy")):
            points.extend(["Security posture", "Trust controls", "Operational safety"])
        if any(term in text for term in ("enterprise", "b2b", "platform", "controls")):
            points.extend(["Enterprise controls", "Buyer confidence", "Operational readiness"])
        if score_delta >= 8:
            points.append("Current momentum advantage")
        elif score_delta <= -8:
            points.append("Needs momentum catch-up")

        return self._unique_ordered(points, limit=4)

    def _comparison_gap_analysis(
        self,
        *,
        left_query: str,
        right_query: str,
        left: dict[str, Any],
        right: dict[str, Any],
        left_type: str,
        right_type: str,
        strengths: list[str],
        weaknesses: list[str],
    ) -> dict[str, Any]:
        left_name = self._comparison_display_name(left_query, left.get("query") or left_query)
        right_name = self._comparison_display_name(right_query, right.get("query") or right_query)
        left_score = _safe_number(left.get("trend_score"))
        right_score = _safe_number(right.get("trend_score"))
        score_delta = left_score - right_score

        left_wins = self._comparison_advantage_points(left_query, left_type, score_delta)
        right_wins = self._comparison_advantage_points(right_query, right_type, -score_delta)

        if left_score > right_score + 5:
            left_wins.insert(0, "Stronger current momentum")
        elif right_score > left_score + 5:
            right_wins.insert(0, "Stronger current momentum")

        if "giggso" in left_query.lower():
            left_wins = self._unique_ordered([*["Governance", "Compliance", "Enterprise controls", "Audit readiness"], *left_wins], limit=4)
            right_wins = self._unique_ordered([*["Model innovation", "Developer adoption", "Brand visibility"], *right_wins], limit=4)
        elif "giggso" in right_query.lower():
            right_wins = self._unique_ordered([*["Governance", "Compliance", "Enterprise controls", "Audit readiness"], *right_wins], limit=4)
            left_wins = self._unique_ordered([*["Model innovation", "Developer adoption", "Brand visibility"], *left_wins], limit=4)

        missing_capabilities = self._unique_ordered(
            [
                "Public benchmarks",
                "Enterprise case studies",
                "Analyst visibility",
                "Deployment proof",
                "Customer-ready evidence",
            ],
            limit=5,
        )
        if left_type == "AI Model" or right_type == "AI Model":
            missing_capabilities = self._unique_ordered(
                [*missing_capabilities, "Enterprise packaging", "Compliance evidence", "Support model clarity"],
                limit=6,
            )
        if "giggso" in left_query.lower() or "giggso" in right_query.lower():
            missing_capabilities = self._unique_ordered(
                [*missing_capabilities, "Analyst visibility", "Public benchmarks", "Customer proof points"],
                limit=6,
            )

        market_positioning_gaps = self._unique_ordered(
            [
                f"{left_name} leans more into model differentiation than enterprise proof." if left_type == "AI Model" else f"{left_name} needs clearer positioning around enterprise buying criteria.",
                f"{right_name} leans more into model differentiation than enterprise proof." if right_type == "AI Model" else f"{right_name} needs clearer positioning around enterprise buying criteria.",
                "The market gap is strongest where governance and controls are not yet framed as a competitive advantage.",
            ],
            limit=3,
        )
        enterprise_readiness_gaps = self._unique_ordered(
            [
                "Enterprise case studies are limited compared with product buzz.",
                "Operational proof and procurement artifacts are not yet front and center.",
                "Security and compliance evidence needs to be easier for buyers to consume.",
            ],
            limit=3,
        )

        return {
            "left_label": left_name,
            "right_label": right_name,
            "left_wins": left_wins,
            "right_wins": right_wins,
            "missing_capabilities": missing_capabilities,
            "market_positioning_gaps": market_positioning_gaps,
            "enterprise_readiness_gaps": enterprise_readiness_gaps,
            "summary": strengths[:3] + weaknesses[:2],
        }

    def _comparison_strategic_recommendations(
        self,
        *,
        left_query: str,
        right_query: str,
        left: dict[str, Any],
        right: dict[str, Any],
        left_type: str,
        right_type: str,
        overlap: list[str],
        gap_analysis: dict[str, Any],
    ) -> list[dict[str, Any]]:
        left_name = self._comparison_display_name(left_query, left.get("query") or left_query)
        right_name = self._comparison_display_name(right_query, right.get("query") or right_query)
        overlap_theme = overlap[0] if overlap else "enterprise AI"
        left_is_giggso = "giggso" in left_query.lower()
        right_is_giggso = "giggso" in right_query.lower()
        governance_side = left_name if left_is_giggso or (left_type in {"Company", "Governance"} and any(term in left_query.lower() for term in ("governance", "compliance", "security"))) else right_name
        other_side = right_name if governance_side == left_name else left_name

        recommendations = [
            {
                "priority": "Priority 1",
                "initiative": f"Position {governance_side}'s governance and compliance controls against {other_side}'s model-first narrative.",
                "business_impact": "Sharpens differentiation in enterprise buying conversations and procurement reviews.",
                "expected_outcome": "Higher trust with regulated buyers and clearer executive positioning.",
            },
            {
                "priority": "Priority 2",
                "initiative": f"Publish benchmark proof and customer evidence around {overlap_theme}.",
                "business_impact": "Increases credibility where buyers want evidence instead of claims.",
                "expected_outcome": "Better analyst, buyer, and partner confidence.",
            },
            {
                "priority": "Priority 3",
                "initiative": "Package security, observability, and deployment-readiness artifacts into a repeatable enterprise motion.",
                "business_impact": "Reduces sales friction and accelerates proof-to-purchase conversion.",
                "expected_outcome": "Shorter enterprise evaluation cycles and stronger conversion rates.",
            },
        ]
        return recommendations

    def _comparison_action_plan(
        self,
        *,
        left_query: str,
        right_query: str,
        gap_analysis: dict[str, Any],
        strategic_recommendations: list[dict[str, Any]],
    ) -> dict[str, list[dict[str, Any]]]:
        left_name = gap_analysis.get("left_label") or self._comparison_display_name(left_query, left_query)
        right_name = gap_analysis.get("right_label") or self._comparison_display_name(right_query, right_query)
        immediate = [
            {
                "objective": f"Publish a {left_name} vs {right_name} executive comparison brief.",
                "expected_impact": "Creates a board-ready narrative and sharpens market positioning.",
                "priority": "High",
            },
            {
                "objective": "Package the strongest enterprise proof points into one customer-facing asset.",
                "expected_impact": "Improves trust in procurement and security reviews.",
                "priority": "High",
            },
        ]
        next_actions = [
            {
                "objective": "Launch a proof pack with benchmarks, controls, and implementation evidence.",
                "expected_impact": "Lowers adoption friction and strengthens sales enablement.",
                "priority": "Medium",
            },
            {
                "objective": "Align messaging with the shared enterprise AI theme from the comparison.",
                "expected_impact": "Keeps the narrative focused on buyer priorities instead of generic feature claims.",
                "priority": "Medium",
            },
        ]
        long_term = [
            {
                "objective": "Expand the comparison into a repeatable competitive intelligence motion.",
                "expected_impact": "Turns ad hoc comparisons into an ongoing market strategy asset.",
                "priority": "Medium",
            },
            {
                "objective": "Build case-study depth and analyst visibility around enterprise outcomes.",
                "expected_impact": "Strengthens credibility against larger or better-known competitors.",
                "priority": "High",
            },
        ]
        if strategic_recommendations:
            immediate.insert(
                0,
                {
                    "objective": strategic_recommendations[0]["initiative"],
                    "expected_impact": strategic_recommendations[0]["business_impact"],
                    "priority": strategic_recommendations[0]["priority"],
                },
            )
        return {
            "immediate_actions": self._unique_dicts(immediate, key_fields=("objective",)),
            "next_actions": self._unique_dicts(next_actions, key_fields=("objective",)),
            "long_term_actions": self._unique_dicts(long_term, key_fields=("objective",)),
        }

    def _comparison_roadmap(
        self,
        *,
        left_query: str,
        right_query: str,
        strategic_recommendations: list[dict[str, Any]],
        action_plan: dict[str, list[dict[str, Any]]],
    ) -> dict[str, list[dict[str, Any]]]:
        left_name = self._comparison_display_name(left_query, left_query)
        right_name = self._comparison_display_name(right_query, right_query)
        primary_theme = strategic_recommendations[0]["initiative"] if strategic_recommendations else f"Differentiate {left_name} versus {right_name} on enterprise readiness."
        roadmap = {
            "30_days": [
                {
                    "objective": f"Publish the executive comparison brief for {left_name} vs {right_name}.",
                    "expected_impact": "Quick visibility win for sales and leadership.",
                    "priority": "High",
                },
                {
                    "objective": "Ship a one-page governance and compliance proof sheet.",
                    "expected_impact": "Supports immediate buyer conversations.",
                    "priority": "High",
                },
            ],
            "60_days": [
                {
                    "objective": "Launch the benchmark and evidence pack tied to the comparison theme.",
                    "expected_impact": "Improves trust and enterprise readiness messaging.",
                    "priority": "High",
                },
                {
                    "objective": f"Operationalize the primary recommendation: {primary_theme}",
                    "expected_impact": "Converts the strategy into repeatable field execution.",
                    "priority": "Medium",
                },
            ],
            "90_days": [
                {
                    "objective": "Expand the competitive narrative into analyst and partner enablement.",
                    "expected_impact": "Improves market visibility and share of voice.",
                    "priority": "Medium",
                },
                {
                    "objective": "Track win/loss and adoption outcomes against the new positioning.",
                    "expected_impact": "Shows whether the strategy is creating commercial lift.",
                    "priority": "High",
                },
            ],
        }
        if action_plan.get("immediate_actions"):
            roadmap["30_days"].insert(
                0,
                {
                    "objective": action_plan["immediate_actions"][0]["objective"],
                    "expected_impact": action_plan["immediate_actions"][0]["expected_impact"],
                    "priority": action_plan["immediate_actions"][0]["priority"],
                },
            )
        return roadmap

    def _comparison_business_impact_forecast(
        self,
        *,
        left: dict[str, Any],
        right: dict[str, Any],
        left_type: str,
        right_type: str,
        overlap: list[str],
        competitive_gap_analysis: dict[str, Any],
    ) -> dict[str, Any]:
        trend_average = (_safe_number(left.get("trend_score")) + _safe_number(right.get("trend_score"))) / 2.0
        overlap_bonus = min(6.0, len(overlap) * 1.5)
        model_bonus = 4.0 if left_type == "AI Model" or right_type == "AI Model" else 0.0
        enterprise_bonus = 5.0 if any("enterprise" in str(item).lower() for item in overlap) else 0.0
        visibility_gain = max(5.0, min(25.0, round(8.0 + trend_average / 12.0 + model_bonus + overlap_bonus, 1)))
        buyer_trust_gain = max(5.0, min(30.0, round(10.0 + len(competitive_gap_analysis.get("enterprise_readiness_gaps", [])) * 1.5 + enterprise_bonus, 1)))
        competitive_advantage_gain = max(5.0, min(25.0, round(7.0 + abs(_safe_number(left.get("trend_score")) - _safe_number(right.get("trend_score"))) / 4.0 + overlap_bonus / 2.0, 1)))
        enterprise_adoption_impact = max(5.0, min(30.0, round(10.0 + _safe_number(left.get("confidence_score")) / 12.0 + _safe_number(right.get("confidence_score")) / 12.0 + enterprise_bonus, 1)))
        return {
            "market_visibility_gain": visibility_gain,
            "buyer_trust_gain": buyer_trust_gain,
            "competitive_advantage_gain": competitive_advantage_gain,
            "enterprise_adoption_impact": enterprise_adoption_impact,
            "summary": "The comparison indicates measurable upside if the winning narrative is anchored in enterprise trust, deployment proof, and market visibility.",
        }

    def _comparison_executive_readiness_score(
        self,
        *,
        left: dict[str, Any],
        right: dict[str, Any],
        left_type: str,
        right_type: str,
        overlap: list[str],
        gap_analysis: dict[str, Any],
    ) -> dict[str, Any]:
        overlap_bonus = min(6.0, len(overlap) * 1.5)
        gap_blob = " ".join([*(gap_analysis.get("left_wins") or []), *(gap_analysis.get("right_wins") or []), *(gap_analysis.get("missing_capabilities") or []), *(gap_analysis.get("enterprise_readiness_gaps") or [])]).lower()
        overlap_blob = " ".join(overlap).lower()
        governance_readiness = max(40.0, min(95.0, round(72.0 + overlap_bonus + (6.0 if any(term in gap_blob for term in ("governance", "audit", "compliance")) else 0.0), 1)))
        compliance_readiness = max(40.0, min(95.0, round(70.0 + overlap_bonus + (5.0 if any(term in overlap_blob for term in ("compliance", "governance", "audit")) else 0.0), 1)))
        security_readiness = max(40.0, min(95.0, round(68.0 + overlap_bonus + (6.0 if any(term in overlap_blob for term in ("security", "safety", "trust")) else 0.0), 1)))
        enterprise_readiness = max(40.0, min(95.0, round(70.0 + (6.0 if left_type == "Company" or right_type == "Company" else 0.0) + overlap_bonus, 1)))
        overall = round((governance_readiness + compliance_readiness + security_readiness + enterprise_readiness) / 4.0, 1)
        return {
            "governance_readiness": governance_readiness,
            "compliance_readiness": compliance_readiness,
            "security_readiness": security_readiness,
            "enterprise_readiness": enterprise_readiness,
            "overall_executive_readiness_score": overall,
        }

    def _comparison_board_recommendations(
        self,
        *,
        left_query: str,
        right_query: str,
        gap_analysis: dict[str, Any],
        business_impact_forecast: dict[str, Any],
        executive_readiness_score: dict[str, Any],
    ) -> list[dict[str, Any]]:
        left_name = gap_analysis.get("left_label") or self._comparison_display_name(left_query, left_query)
        right_name = gap_analysis.get("right_label") or self._comparison_display_name(right_query, right_query)
        return self._unique_dicts(
            [
                {
                    "focus": "Growth",
                    "priority": "High",
                    "recommendation": f"Use {left_name} vs {right_name} to sharpen market visibility and create a repeatable executive narrative.",
                },
                {
                    "focus": "Risk",
                    "priority": "High",
                    "recommendation": f"Close the enterprise readiness gap highlighted by the comparison before expanding the story externally.",
                },
                {
                    "focus": "Governance",
                    "priority": "High",
                    "recommendation": "Lead with governance, compliance, and audit evidence to convert interest into trust.",
                },
                {
                    "focus": "Enterprise Adoption",
                    "priority": "Medium",
                    "recommendation": f"Package the comparison into a buyer-ready proof point for enterprise teams evaluating {left_name} and {right_name}.",
                },
                {
                    "focus": "Competitive Positioning",
                    "priority": "Medium",
                    "recommendation": f"Use the forecasted visibility gain of {business_impact_forecast.get('market_visibility_gain', 0):.0f}% and overall readiness of {executive_readiness_score.get('overall_executive_readiness_score', 0):.0f}% as board signals.",
                },
            ],
            key_fields=("focus",),
        )

    def _unique_dicts(self, items: list[dict[str, Any]], key_fields: tuple[str, ...] = ("title",)) -> list[dict[str, Any]]:
        seen: set[tuple[str, ...]] = set()
        values: list[dict[str, Any]] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            key = tuple(_clean_text(item.get(field)).lower() for field in key_fields)
            if not any(key):
                key = tuple(sorted(_clean_text(value).lower() for value in item.values() if isinstance(value, str)))[: len(key_fields)]
            if key in seen:
                continue
            seen.add(key)
            values.append(item)
        return values

    def _validate_search_case(self, query: str, snapshot: dict[str, Any]) -> dict[str, Any]:
        analysis = self._build_search_intelligence(query, snapshot)
        query_lower = query.lower()
        expected_keywords = self._expected_keywords_for_query(query)
        related_keywords = [self._normalize_overlap_keyword(item) for item in analysis.get("related_keywords") or []]
        related_keywords = [item for item in related_keywords if item]
        news_items = analysis.get("recent_news") or []
        news_quality = self._validate_news_quality(news_items)
        keyword_quality = self._validate_keyword_quality(query, related_keywords, expected_keywords)
        trend_quality = self._validate_trend_score_quality(query, analysis.get("trend_score", 0), analysis.get("query_type", "Concept"))
        confidence_score = min(95, int(_safe_number(analysis.get("confidence_score"), 0.0)))
        confidence_quality = 100 if confidence_score <= 95 else 0
        executive_quality = self._validate_executive_quality(analysis.get("executive_summary", ""), analysis.get("recommendation", ""), query_lower)
        evidence_count = _safe_int(analysis.get("evidence_count") or analysis.get("source_count") or 0)
        evidence_quality = 100 if evidence_count >= 2 and analysis.get("confidence_reason") != "Insufficient evidence available." else 0
        overall = self._average([keyword_quality, news_quality, trend_quality, confidence_quality, executive_quality, evidence_quality])

        passed_checks: list[str] = []
        failed_checks: list[str] = []
        if trend_quality >= 70:
            passed_checks.append(f"{query}: trend score calibrated")
        else:
            failed_checks.append(f"{query}: trend score needs calibration")
        if keyword_quality >= 70:
            passed_checks.append(f"{query}: keyword relevance")
        else:
            failed_checks.append(f"{query}: keyword relevance needs improvement")
        if news_quality >= 70:
            passed_checks.append(f"{query}: news relevance")
        else:
            failed_checks.append(f"{query}: news relevance needs improvement")
        if confidence_score <= 95:
            passed_checks.append(f"{query}: confidence capped at 95")
        else:
            failed_checks.append(f"{query}: confidence exceeds cap")
        if executive_quality >= 70:
            passed_checks.append(f"{query}: executive insight quality")
        else:
            failed_checks.append(f"{query}: executive insight needs stronger specificity")
        if evidence_quality >= 70:
            passed_checks.append(f"{query}: evidence support available")
        else:
            failed_checks.append(f"{query}: insufficient evidence support")

        recommended_fixes: list[str] = []
        if keyword_quality < 70:
            recommended_fixes.append(f"Improve keyword filtering and strengthen domain terms for {query}.")
        if news_quality < 70:
            recommended_fixes.append(f"Raise enterprise relevance filtering for news linked to {query}.")
        if trend_quality < 70:
            recommended_fixes.append(f"Increase signal weighting for high-value AI topics such as {query}.")
        if executive_quality < 70:
            recommended_fixes.append(f"Make the executive summary for {query} more specific and business-focused.")
        if evidence_quality < 70:
            recommended_fixes.append(f"Require at least two live evidence signals before surfacing {query}.")

        return {
            "query": query,
            "query_type": analysis.get("query_type", "Concept"),
            "trend_score": analysis.get("trend_score", 0),
            "confidence_score": confidence_score,
            "keyword_quality": round(keyword_quality, 1),
            "news_quality": round(news_quality, 1),
            "executive_insight_quality": round(executive_quality, 1),
            "evidence_quality": round(evidence_quality, 1),
            "overall_accuracy_score": round(overall, 1),
            "related_keywords": related_keywords[:8],
            "evidence_count": evidence_count,
            "source_count": _safe_int(analysis.get("source_count") or 0),
            "confidence_reason": analysis.get("confidence_reason") or "",
            "passed_checks": passed_checks,
            "failed_checks": failed_checks,
            "recommended_fixes": recommended_fixes,
        }

    def _validate_comparison_case(self, left_query: str, right_query: str, snapshot: dict[str, Any]) -> dict[str, Any]:
        comparison = self.compare_intelligence(left_query, right_query)
        left_analysis = self._build_search_intelligence(left_query, snapshot)
        right_analysis = self._build_search_intelligence(right_query, snapshot)
        overlap = [self._normalize_overlap_keyword(item) for item in comparison.get("keyword_overlap") or []]
        overlap = [item for item in overlap if item]
        keyword_quality = 100.0 if overlap and any(theme in " ".join(overlap).lower() for theme in ("enterprise ai", "governance", "security", "compliance", "trustworthy ai", "model monitoring")) else 55.0 if overlap else 20.0
        summary_quality = self._validate_executive_quality(comparison.get("executive_summary", ""), "", f"{left_query} {right_query}")
        strength_quality = 100.0 if comparison.get("strengths") else 40.0
        weakness_quality = 100.0 if comparison.get("weaknesses") else 35.0
        evidence_count = _safe_int(comparison.get("evidence_count") or 0)
        evidence_quality = 100.0 if evidence_count >= 3 and comparison.get("confidence_reason") != "Insufficient evidence available." else 0.0
        overall = self._average([keyword_quality, summary_quality, strength_quality, weakness_quality, evidence_quality])

        passed_checks = []
        failed_checks = []
        if keyword_quality >= 70:
            passed_checks.append(f"{left_query} vs {right_query}: comparison themes aligned")
        else:
            failed_checks.append(f"{left_query} vs {right_query}: comparison themes need improvement")
        if summary_quality >= 70:
            passed_checks.append(f"{left_query} vs {right_query}: executive summary quality")
        else:
            failed_checks.append(f"{left_query} vs {right_query}: executive summary needs more specificity")
        if comparison.get("strengths"):
            passed_checks.append(f"{left_query} vs {right_query}: strengths identified")
        else:
            failed_checks.append(f"{left_query} vs {right_query}: strengths missing")
        if comparison.get("weaknesses"):
            passed_checks.append(f"{left_query} vs {right_query}: weaknesses identified")
        else:
            failed_checks.append(f"{left_query} vs {right_query}: weaknesses missing")
        if evidence_quality >= 70:
            passed_checks.append(f"{left_query} vs {right_query}: evidence support available")
        else:
            failed_checks.append(f"{left_query} vs {right_query}: insufficient evidence support")

        recommended_fixes = []
        if keyword_quality < 70:
            recommended_fixes.append(f"Shift overlap for {left_query} vs {right_query} toward enterprise themes instead of entity names.")
        if summary_quality < 70:
            recommended_fixes.append(f"Increase specificity in the board-style summary for {left_query} vs {right_query}.")
        if evidence_quality < 70:
            recommended_fixes.append(f"Require more live evidence before generating a comparison for {left_query} vs {right_query}.")

        return {
            "pair": f"{left_query} vs {right_query}",
            "trend_score": comparison.get("trend_score", 0),
            "momentum": comparison.get("momentum", "Moderate"),
            "growth_score": comparison.get("growth_score", 0),
            "keyword_overlap": overlap[:8],
            "keyword_quality": round(keyword_quality, 1),
            "summary_quality": round(summary_quality, 1),
            "evidence_quality": round(evidence_quality, 1),
            "overall_accuracy_score": round(overall, 1),
            "evidence_count": evidence_count,
            "source_count": _safe_int(comparison.get("source_count") or 0),
            "confidence_reason": comparison.get("confidence_reason") or "",
            "passed_checks": passed_checks,
            "failed_checks": failed_checks,
            "recommended_fixes": recommended_fixes,
            "left_query_type": left_analysis.get("query_type"),
            "right_query_type": right_analysis.get("query_type"),
        }

    def _expected_keywords_for_query(self, query: str) -> list[str]:
        lower = query.lower()
        mapping = {
            "claude": ["Anthropic", "Claude 4", "AI Safety", "Enterprise AI"],
            "chatgpt": ["OpenAI", "GPT-4o", "AI Assistant", "Enterprise AI"],
            "gemini": ["Google DeepMind", "Multimodal AI", "Enterprise AI"],
            "openai": ["GPT-4o", "Enterprise AI", "Agentic AI"],
            "anthropic": ["Claude", "AI Safety", "Trustworthy AI"],
            "rag": ["Retrieval", "Grounding", "Citations", "Enterprise AI"],
            "mcp": ["Model Context Protocol", "Agentic AI", "Workflow Orchestration"],
            "agentic ai": ["AI Agents", "Multi-Agent Systems", "MCP", "AI Workflows"],
            "autonomous systems": ["Agentic AI", "AI Agents", "MCP", "Multi-Agent Systems", "AI Workflows"],
        }
        for needle, values in mapping.items():
            if needle in lower:
                return values
        return ["Enterprise AI", "Governance", "Security"]

    def _validate_keyword_quality(self, query: str, related_keywords: list[str], expected_keywords: list[str]) -> float:
        lower_keywords = [item.lower() for item in related_keywords]
        expected_hits = sum(1 for item in expected_keywords if item.lower() in lower_keywords)
        relevant_bonus = min(30.0, expected_hits * 15.0)
        generic_penalty = sum(1 for item in lower_keywords if item in {"ai", "for", "systems", "company", "platform", "technology"}) * 8.0
        duplicate_penalty = max(0, len(lower_keywords) - len(set(lower_keywords))) * 10.0
        query_tokens = [token for token in query.lower().split() if len(token) > 2]
        query_match_bonus = min(20.0, sum(8.0 for token in query_tokens if any(token in item for item in lower_keywords)))
        score = 45.0 + relevant_bonus + query_match_bonus - generic_penalty - duplicate_penalty
        return max(0.0, min(100.0, score))

    def _validate_news_quality(self, news_items: list[dict[str, Any]]) -> float:
        if not news_items:
            return 35.0
        scores = []
        for item in news_items[:5]:
            title = f"{item.get('headline', '')} {item.get('summary', '')}".lower()
            score = _safe_number(item.get("relevance_score"), 0.0)
            if any(term in title for term in ("enterprise", "governance", "security", "compliance", "agent", "rag", "llm", "openai", "anthropic", "claude", "chatgpt", "gemini", "mcp")):
                score += 12.0
            if any(term in title for term in ("military", "defense", "aerospace", "robot")):
                score -= 18.0
            scores.append(score)
        return max(0.0, min(100.0, self._average(scores)))

    def _validate_trend_score_quality(self, query: str, trend_score: Any, query_type: str) -> float:
        score = _safe_number(trend_score, 0.0)
        high_signal = any(term in query.lower() for term in ("claude", "chatgpt", "gemini", "openai", "anthropic", "agentic ai", "mcp"))
        if high_signal:
            target = 70.0 <= score <= 95.0
            return 100.0 if target else max(35.0, 100.0 - abs(score - 82.0))
        if query_type == "Technology":
            return 100.0 if 45.0 <= score <= 90.0 else max(35.0, 100.0 - abs(score - 68.0))
        return 100.0 if score <= 95.0 else 0.0

    def _validate_executive_quality(self, summary: str, recommendation: str, query_text: str) -> float:
        combined = f"{summary} {recommendation}".lower()
        score = 45.0
        if len(summary.split()) >= 16:
            score += 20.0
        if any(term in combined for term in ("enterprise", "governance", "security", "compliance", "business", "buyer", "deployment", "risk")):
            score += 20.0
        if any(term in combined for term in ("action", "position", "recommend", "lead with", "compare", "tie it back", "operating controls")):
            score += 10.0
        if any(term in combined for term in ("comparison point", "use", "generic", "broad platform")) and "enterprise" not in combined:
            score -= 20.0
        if query_text and query_text in combined:
            score += 5.0
        return max(0.0, min(100.0, score))

    def _average(self, values: list[float]) -> float:
        filtered = [float(value) for value in values if value is not None]
        return sum(filtered) / len(filtered) if filtered else 0.0

    def _normalize_overlap_keyword(self, value: Any) -> str:
        text = self._display_search_keyword(value)
        lower = text.lower()
        if lower in {"ai", "for", "systems", "model", "company", "platform", "technology", "enterprise"}:
            return ""
        return text

    def _comparison_theme_overlap(
        self,
        left_query: str,
        right_query: str,
        left_keywords: set[str],
        right_keywords: set[str],
    ) -> list[str]:
        theme_map = {
            "Enterprise AI": {"enterprise ai", "enterprise", "deployment", "workflow", "platform"},
            "Governance": {"governance", "policy controls", "audit trails", "compliance", "risk"},
            "Security": {"security", "llm security", "prompt injection", "red teaming", "guardrails"},
            "Compliance": {"compliance", "auditability", "regulatory", "controls"},
            "Trustworthy AI": {"trustworthy ai", "safety", "reliability", "responsible ai"},
            "Model Monitoring": {"model monitoring", "observability", "drift", "incident"},
            "Agentic AI": {"agentic ai", "agents", "multi-agent systems", "mcp", "workflow"},
            "RAG": {"rag", "retrieval", "grounding", "citations"},
        }
        left_blob = " ".join([left_query, *left_keywords]).lower()
        right_blob = " ".join([right_query, *right_keywords]).lower()
        shared: list[str] = []
        for label, terms in theme_map.items():
            if any(term in left_blob for term in terms) and any(term in right_blob for term in terms):
                shared.append(label)
        enterprise_bucket = ("Enterprise AI", "Governance", "Security", "Compliance", "Trustworthy AI", "Model Monitoring", "AI Risk")
        if not shared:
            if any(name in left_query.lower() for name in ("openai", "anthropic", "giggso", "cohere", "claude", "chatgpt", "gemini")) and any(
                name in right_query.lower() for name in ("openai", "anthropic", "giggso", "cohere", "claude", "chatgpt", "gemini")
            ):
                shared = [item for item in enterprise_bucket if item.lower() in (left_blob + " " + right_blob)]
            else:
                shared = [item for item in enterprise_bucket if item.lower() in left_blob or item.lower() in right_blob]
        if not shared and "company" in (self.detect_query_type(left_query).lower() + self.detect_query_type(right_query).lower()):
            shared = ["Enterprise AI", "Governance", "Security"]
        return self._unique_ordered(shared, limit=4)

    def _dedupe_search_items(self, items: list[dict[str, Any]], key_fields: tuple[str, ...], limit: int = 5) -> list[dict[str, Any]]:
        seen: set[str] = set()
        unique: list[dict[str, Any]] = []
        for item in sorted(items, key=lambda row: (_safe_number(row.get("_score"), 0.0), _safe_number(row.get("momentum_score"), 0.0)), reverse=True):
            key = " | ".join(_clean_text(item.get(field, "")).lower() for field in key_fields if item.get(field))
            if not key or key in seen:
                continue
            seen.add(key)
            copy = dict(item)
            copy.pop("_score", None)
            unique.append(copy)
            if len(unique) >= limit:
                break
        return unique

    def _normalize_insight_items(self, items: list[dict[str, Any]], now: datetime) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        for index, item in enumerate(items[:5], start=1):
            source_notes = [json.dumps(item, ensure_ascii=False)]
            evidence_meta = self._evidence_metadata(
                article_count=0,
                mention_count=1,
                source_notes=source_notes,
                source_count=1,
                last_updated=now,
            )
            normalized.append(
                {
                    "insight_title": _clean_text(item.get("insight_title") or f"Executive Insight {index}"),
                    "what_is_trending": _clean_text(item.get("what_is_trending") or item.get("trend_reasoning") or ""),
                    "why_it_matters": _clean_text(item.get("why_it_matters") or item.get("competitor_reasoning") or ""),
                    "business_impact": _clean_text(item.get("business_impact") or ""),
                    "recommended_action": _clean_text(item.get("recommended_action") or ""),
                    "priority": _clean_text(item.get("priority") or "High"),
                    "insight_type": _clean_text(item.get("insight_type") or "Executive"),
                    "source_notes": source_notes,
                    "evidence_count": evidence_meta["evidence_count"],
                    "source_count": evidence_meta["source_count"],
                    "confidence_reason": evidence_meta["confidence_reason"],
                    "evidence_sources": evidence_meta["evidence_sources"],
                    "source_names": evidence_meta["source_names"],
                    "source_timestamps": evidence_meta["source_timestamps"],
                    "last_updated": evidence_meta["last_updated"],
                    "created_at": now,
                    "updated_at": now,
                }
            )
        return normalized

    def _fallback_insights(
        self,
        company: dict[str, Any],
        linkedin: dict[str, Any],
        news: list[dict[str, Any]],
        competitors: list[dict[str, Any]],
        live_trends: list[dict[str, Any]],
        now: datetime,
    ) -> list[dict[str, Any]]:
        top_trend = live_trends[0]["trend_name"] if live_trends else "AI Governance"
        competitor_name = competitors[0]["name"] if competitors else "OpenAI"
        return [
            {
                "insight_title": "Governance is now a buying trigger",
                "what_is_trending": f"{top_trend} and related controls are showing up across company messaging and current AI news.",
                "why_it_matters": "Enterprise buyers want a clear path from AI experimentation to production with policy, security, and evidence built in.",
                "business_impact": "This shortens trust-building for regulated buyers and creates a more durable enterprise sales story.",
                "recommended_action": "Lead every enterprise conversation with governance controls, auditability, and operational monitoring.",
                "priority": "High",
                "insight_type": "Market",
                "source_notes": [company.get("market_narrative", ""), linkedin.get("strategic_narrative", "")],
                "evidence_count": 2,
                "source_count": 2,
                "confidence_reason": self._confidence_reason_text(
                    article_count=0,
                    mention_count=2,
                    source_names=self._evidence_source_names(company.get("market_narrative", ""), linkedin.get("strategic_narrative", "")),
                    recency_score=0.0,
                ),
                "evidence_sources": self._evidence_source_names(company.get("market_narrative", ""), linkedin.get("strategic_narrative", "")),
                "source_names": self._evidence_source_names(company.get("market_narrative", ""), linkedin.get("strategic_narrative", "")),
                "source_timestamps": [now.isoformat()],
                "last_updated": now.isoformat(),
                "created_at": now,
                "updated_at": now,
            },
            {
                "insight_title": "Agentic AI is moving into controlled deployment",
                "what_is_trending": "Buyer attention is shifting from demos to controlled execution, approvals, and monitoring.",
                "why_it_matters": "Autonomous workflows create new operational and risk questions that governance products can answer.",
                "business_impact": "Governance tooling can become a gatekeeper for agent rollout decisions.",
                "recommended_action": "Show how the platform constrains agent behavior and records decision trails.",
                "priority": "High",
                "insight_type": "Product",
                "source_notes": [json.dumps(news[:3], default=str, ensure_ascii=False)],
                "evidence_count": max(1, len(news[:3])),
                "source_count": max(1, len(news[:3])),
                "confidence_reason": self._confidence_reason_text(
                    article_count=min(3, len(news)),
                    mention_count=0,
                    source_names=self._evidence_source_names("Industry News"),
                    recency_score=0.0,
                ),
                "evidence_sources": self._evidence_source_names("Industry News"),
                "source_names": self._evidence_source_names("Industry News"),
                "source_timestamps": [now.isoformat()],
                "last_updated": now.isoformat(),
                "created_at": now,
                "updated_at": now,
            },
            {
                "insight_title": f"{competitor_name} is intensifying enterprise AI pressure",
                "what_is_trending": f"{competitor_name} and peers are using security, governance, and enterprise features to win budgets.",
                "why_it_matters": "The market is rewarding vendors that combine capability with trust and deployment readiness.",
                "business_impact": "Giggso needs to make governance depth a differentiator instead of a compliance side note.",
                "recommended_action": "Compare Giggso against broad platforms on governance depth, validation, and compliance evidence.",
                "priority": "Medium",
                "insight_type": "Competitive",
                "source_notes": [json.dumps(competitors[:2], default=str, ensure_ascii=False)],
                "evidence_count": max(1, len(competitors[:2])),
                "source_count": max(1, len(competitors[:2])),
                "confidence_reason": self._confidence_reason_text(
                    article_count=0,
                    mention_count=min(2, len(competitors)),
                    source_names=self._evidence_source_names(competitor_name, "Competitor Signals"),
                    recency_score=0.0,
                ),
                "evidence_sources": self._evidence_source_names(competitor_name, "Competitor Signals"),
                "source_names": self._evidence_source_names(competitor_name, "Competitor Signals"),
                "source_timestamps": [now.isoformat()],
                "last_updated": now.isoformat(),
                "created_at": now,
                "updated_at": now,
            },
            {
                "insight_title": "Regulated industries are driving compliance-led demand",
                "what_is_trending": "AI compliance, model monitoring, and security validation are appearing across current news coverage.",
                "why_it_matters": "These are the exact areas where Giggso can win enterprise trust and accelerate procurement.",
                "business_impact": "Compliance-readiness can reduce sales friction and increase enterprise conversion rates.",
                "recommended_action": "Translate technical controls into board-level risk and evidence language.",
                "priority": "High",
                "insight_type": "Board",
                "source_notes": [json.dumps(news[:5], default=str, ensure_ascii=False)],
                "evidence_count": max(1, len(news[:5])),
                "source_count": max(1, len(news[:5])),
                "confidence_reason": self._confidence_reason_text(
                    article_count=min(5, len(news)),
                    mention_count=0,
                    source_names=self._evidence_source_names("Industry News"),
                    recency_score=0.0,
                ),
                "evidence_sources": self._evidence_source_names("Industry News"),
                "source_names": self._evidence_source_names("Industry News"),
                "source_timestamps": [now.isoformat()],
                "last_updated": now.isoformat(),
                "created_at": now,
                "updated_at": now,
            },
        ]

    def _fetch_page(self, url: str, allow_redirects: bool = True) -> dict[str, Any] | None:
        try:
            response = self.session.get(url, timeout=20, allow_redirects=allow_redirects)
            response.raise_for_status()
        except Exception as exc:
            logger.debug("Failed to fetch %s: %s", url, exc)
            return None
        soup = BeautifulSoup(response.text, "html.parser")
        title = self._meta_content(soup, "property", "og:title") or self._meta_content(soup, "name", "title") or self._extract_title(soup)
        description = self._meta_content(soup, "property", "og:description") or self._meta_content(soup, "name", "description")
        headings = [self._normalize_sentence(node.get_text(" ", strip=True)) for node in soup.find_all(["h1", "h2", "h3"])[:10]]
        paragraphs = [self._normalize_sentence(node.get_text(" ", strip=True)) for node in soup.find_all("p")[:12]]
        page_text = " ".join([title or "", description or "", *headings, *paragraphs])
        page_text = _clean_text(page_text)
        if not page_text:
            page_text = f"{COMPANY_NAME} page at {url}"
        return {
            "url": url,
            "final_url": response.url,
            "title": title or self._extract_title(soup) or COMPANY_NAME,
            "description": description or "",
            "content": page_text,
            "summary": self._page_summary(url, title, description, page_text),
        }

    def _bing_search(self, query: str, site: str | None = None, limit: int = 5) -> list[dict[str, Any]]:
        search_query = query
        if site:
            search_query = f"site:{site} {query}"
        url = f"https://www.bing.com/search?q={quote_plus(search_query)}&count={max(5, limit)}&setlang=en-US"
        try:
            response = self.session.get(url, timeout=20)
            response.raise_for_status()
        except Exception as exc:
            logger.debug("Bing search failed for %s: %s", query, exc)
            return []
        soup = BeautifulSoup(response.text, "html.parser")
        results: list[dict[str, Any]] = []
        for item in soup.select("li.b_algo")[:limit]:
            title_node = item.select_one("h2 a")
            snippet_node = item.select_one(".b_caption p")
            if not title_node:
                continue
            title = _clean_text(title_node.get_text(" ", strip=True))
            snippet = _clean_text(snippet_node.get_text(" ", strip=True) if snippet_node else "")
            href = _clean_text(title_node.get("href"))
            results.append(
                {
                    "title": title,
                    "snippet": snippet,
                    "url": href,
                    "content": f"{title} {snippet}",
                    "summary": snippet or title,
                }
            )
        return results

    def _google_news_rss(self, query: str, limit: int = 4) -> list[dict[str, Any]]:
        url = (
            "https://news.google.com/rss/search?q="
            + quote_plus(query)
            + "&hl=en-US&gl=US&ceid=US:en"
        )
        try:
            response = self.session.get(url, timeout=20)
            response.raise_for_status()
            root = ET.fromstring(response.content)
        except Exception as exc:
            logger.debug("Google News RSS failed for %s: %s", query, exc)
            return []
        items: list[dict[str, Any]] = []
        for entry in root.findall(".//item")[:limit]:
            title = self._sanitize_rss_text(self._xml_text(entry, "title"))
            if not title:
                continue
            source = self._sanitize_rss_text(self._xml_source(entry)) or "Google News"
            published_at = _parse_datetime(self._xml_text(entry, "pubDate"))
            summary = self._sanitize_rss_text(self._xml_text(entry, "description"))
            source_link = self._sanitize_url(self._xml_text(entry, "link"))
            relevance = self._news_relevance(query, title, summary, published_at)
            items.append(
                {
                    "headline": title,
                    "title": title,
                    "source": source,
                    "date": published_at.isoformat() if published_at else _NOW().isoformat(),
                    "published_date": published_at.isoformat() if published_at else _NOW().isoformat(),
                    "summary": summary or title,
                    "relevance_score": relevance,
                    "topic": query,
                    "url": source_link,
                }
            )
        return items

    def _meta_content(self, soup: BeautifulSoup, attribute: str, value: str) -> str:
        if attribute == "property":
            node = soup.select_one(f'meta[property="{value}"]')
        else:
            node = soup.select_one(f'meta[name="{value}"]')
        return _clean_text(node.get("content")) if node and node.get("content") else ""

    def _normalize_sentence(self, text: str) -> str:
        if not text:
            return ""
        text = " ".join(str(text).split())
        return text.strip()

    def _extract_title(self, soup: BeautifulSoup) -> str:
        title = soup.title.get_text(" ", strip=True) if soup.title else ""
        return _clean_text(title)

    def _page_summary(self, url: str, title: str, description: str, page_text: str) -> str:
        title_lower = (title or "").lower()
        if "governance" in title_lower or "ai governance" in page_text.lower():
            return "Governance and compliance messaging is prominent on this page."
        if "security" in page_text.lower() or "secure" in page_text.lower():
            return "Security, validation, and trustworthy AI are part of the product story."
        if "execution" in title_lower or "production" in page_text.lower():
            return "The page emphasizes production AI execution and operational readiness."
        if description:
            return description
        return f"Live company signal sourced from {url}."

    def _extract_keywords(self, text: str, minimum: int = 6) -> list[str]:
        cleaned = re.sub(r"[^a-zA-Z0-9\s-]", " ", text.lower())
        tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9-]{2,}", cleaned)
        stop = {
            "ai",
            "about",
            "across",
            "after",
            "also",
            "and",
            "are",
            "best",
            "been",
            "build",
            "built",
            "can",
            "company",
            "enterprise",
            "from",
            "for",
            "into",
            "most",
            "more",
            "new",
            "not",
            "only",
            "amp",
            "gt",
            "lt",
            "nbsp",
            "platform",
            "public",
            "real",
            "safe",
            "site",
            "systems",
            "quot",
            "their",
            "this",
            "that",
            "the",
            "with",
            "your",
        }
        tokens = [token for token in tokens if token not in stop]
        counts = Counter(tokens)
        order = [
            "ai",
            "governance",
            "agentic ai",
            "llm security",
            "model monitoring",
            "ai compliance",
            "ai risk",
            "rag",
            "enterprise ai",
            "trustworthy ai",
            "shadow ai",
        ]
        phrases = []
        lower_text = text.lower()
        for phrase in order:
            if phrase in lower_text:
                phrases.append(phrase)
        for token, _count in counts.most_common():
            if token not in phrases:
                phrases.append(token)
        return self._unique_ordered(phrases, limit=max(minimum, 12))

    def _prioritize_keywords(self, keywords: list[str], preferred: list[str], limit: int = 10) -> list[str]:
        lower_map = {item.lower(): item for item in keywords}
        ordered: list[str] = []
        for term in preferred:
            if term.lower() in lower_map:
                ordered.append(term)
        for item in keywords:
            if item not in ordered:
                ordered.append(item)
        return self._unique_ordered(ordered, limit=limit)

    def _unique_ordered(self, items: list[str], limit: int = 10) -> list[str]:
        seen: set[str] = set()
        values: list[str] = []
        for item in items:
            value = _clean_text(item)
            if not value:
                continue
            key = value.lower()
            if key in seen:
                continue
            seen.add(key)
            values.append(value)
            if len(values) >= limit:
                break
        return values

    def _sentences_to_phrases(self, items: list[str]) -> list[str]:
        phrases: list[str] = []
        for item in items:
            sentence = _clean_text(item)
            if not sentence:
                continue
            parts = re.split(r"[.;:]", sentence)
            for part in parts:
                phrase = _clean_text(part)
                if phrase and len(phrase) > 10:
                    phrases.append(phrase[:140])
        return phrases

    def _normalize_topic_name(self, value: str) -> str:
        mapping = {
            "governance": "AI Governance",
            "agentic": "Agentic AI",
            "security": "AI Security",
            "llm": "LLM Security",
            "monitoring": "Model Monitoring",
            "compliance": "AI Compliance",
            "risk": "AI Risk",
            "rag": "RAG",
            "enterprise": "Enterprise AI",
            "trustworthy": "Trustworthy AI",
            "shadow": "Shadow AI",
        }
        text = _clean_text(value)
        lowered = text.lower()
        for key, display in mapping.items():
            if key in lowered:
                return display
        return text.title() if text else "AI Governance"

    def _signal_strength(self, momentum: float) -> str:
        if momentum >= 85:
            return "Very High"
        if momentum >= 70:
            return "High"
        if momentum >= 55:
            return "Moderate"
        return "Low"

    def _trend_summary_for(
        self,
        trend_name: str,
        company: dict[str, Any],
        linkedin: dict[str, Any],
        news: list[dict[str, Any]],
        competitors: list[dict[str, Any]],
    ) -> str:
        if trend_name == "AI Governance":
            return "Governance controls are the clearest path to helping enterprise buyers move from AI experimentation to production."
        if trend_name == "Agentic AI":
            return "Agentic systems are moving toward constrained enterprise deployment, making guardrails and approvals more valuable."
        if trend_name == "LLM Security":
            return "Security validation and prompt-injection protection are now central to enterprise AI rollout decisions."
        if trend_name == "Model Monitoring":
            return "Production AI teams want drift detection, observability, and incident handling after deployment."
        if trend_name == "AI Compliance":
            return "Compliance evidence and audit trails are becoming mandatory in regulated AI use cases."
        if trend_name == "AI Risk":
            return "Boards want clearer visibility into model, data, and process risk as AI use scales."
        if trend_name == "RAG":
            return "Retrieval quality, citations, and grounding remain the default enterprise assistant requirements."
        if trend_name == "Enterprise AI":
            return "Enterprise buyers continue to favor vendors that can combine AI capability with integration, governance, and deployment support."
        if trend_name == "Trustworthy AI":
            return "Trustworthy AI is becoming the umbrella expectation for safe, explainable enterprise deployment."
        if trend_name == "Shadow AI":
            return "Shadow AI is a growing board-level concern because it expands faster than policy coverage."
        return f"{trend_name} is gaining attention across Giggso, industry news, and competitor activity."

    def _trend_sources(
        self,
        trend_name: str,
        company: dict[str, Any],
        linkedin: dict[str, Any],
        news: list[dict[str, Any]],
        competitors: list[dict[str, Any]],
    ) -> list[str]:
        source_notes: list[str] = []
        if trend_name in company.get("focus_keywords", []):
            source_notes.append("Giggso site messaging")
        if trend_name == linkedin.get("top_theme") or trend_name == linkedin.get("emerging_theme"):
            source_notes.append("LinkedIn public search signals")
        for item in news[:6]:
            if trend_name.lower() in f"{item.get('headline', '')} {item.get('summary', '')}".lower():
                source_notes.append(f"{item.get('source', 'News')} - {item.get('headline', '')}")
        for item in competitors:
            if trend_name.lower() in f"{item.get('activity_summary', '')} {item.get('positioning', '')}".lower():
                source_notes.append(f"{item.get('name', 'Competitor')} activity")
        return self._unique_ordered(source_notes, limit=6)

    def _topic_overlap(self, left: str, right: str) -> bool:
        return left.replace(" ", "")[:6] in right.replace(" ", "") or right.replace(" ", "")[:6] in left.replace(" ", "")

    def _keyword_source_count(
        self,
        term: str,
        company: dict[str, Any],
        linkedin: dict[str, Any],
        news: list[dict[str, Any]],
        competitors: list[dict[str, Any]],
        live_trends: list[dict[str, Any]],
    ) -> int:
        term_lower = term.lower()
        count = 0
        haystacks = [
            company.get("overview", ""),
            company.get("market_narrative", ""),
            linkedin.get("strategic_narrative", ""),
            " ".join(item.get("headline", "") for item in news[:8]),
            " ".join(item.get("activity_summary", "") for item in competitors),
            " ".join(item.get("trend_name", "") for item in live_trends),
        ]
        for haystack in haystacks:
            if term_lower in str(haystack).lower():
                count += 1
        return count

    def _keyword_sources(
        self,
        term: str,
        company: dict[str, Any],
        linkedin: dict[str, Any],
        news: list[dict[str, Any]],
        competitors: list[dict[str, Any]],
        live_trends: list[dict[str, Any]],
    ) -> list[str]:
        notes = []
        if term.lower() in str(company.get("overview", "")).lower():
            notes.append("Giggso company messaging")
        if term.lower() in str(linkedin.get("strategic_narrative", "")).lower():
            notes.append("LinkedIn intelligence")
        for item in news[:10]:
            if term.lower() in f"{item.get('headline', '')} {item.get('summary', '')}".lower():
                notes.append(f"{item.get('source', 'News')} - {item.get('headline', '')}")
        for item in competitors:
            if term.lower() in f"{item.get('activity_summary', '')} {item.get('positioning', '')}".lower():
                notes.append(f"{item.get('name', 'Competitor')} activity")
        for item in live_trends:
            if term.lower() in item.get("trend_name", "").lower():
                notes.append(f"{item.get('trend_name', '')} trend")
        return self._unique_ordered(notes, limit=6)

    def _build_competitor_activity_summary(self, competitor_name: str, latest: dict[str, Any], snippets: list[str]) -> str:
        if latest.get("snippet"):
            return latest["snippet"]
        if latest.get("title"):
            return latest["title"]
        return f"{competitor_name} is maintaining a visible enterprise AI push across recent public search results."

    def _score_competitor_momentum(self, results: list[dict[str, Any]], competitor_name: str) -> float:
        if not results:
            return 0.0
        signal_strength = 0.0
        for result in results:
            text = f"{result.get('title', '')} {result.get('snippet', '')}".lower()
            if any(term in text for term in ("new", "launch", "introduc", "update", "release", "agent", "security")):
                signal_strength += 4.0
        if competitor_name.lower() in " ".join(result.get("title", "").lower() for result in results):
            signal_strength += 4.0
        result_anchor = self._average([len(results) * 8.0, signal_strength * 4.0]) or 0.0
        return round(min(100.0, result_anchor), 1)

    def _news_relevance(self, query: str, title: str, summary: str, published_at: datetime | None) -> float:
        relevance = 0.0
        lower = f"{query} {title} {summary}".lower()
        enterprise_terms = ("ai", "enterprise ai", "governance", "agentic", "security", "llm", "rag", "risk", "compliance", "trustworthy", "monitoring", "model", "openai", "anthropic", "claude", "chatgpt", "gemini", "mcp")
        matched_terms = sum(1 for term in enterprise_terms if term in lower)
        relevance += min(18.0, matched_terms * 2.2)
        for term in query.lower().split():
            if term and term in lower:
                relevance += 4.0
        if any(term in lower for term in ("governance", "security", "compliance", "risk", "agent", "enterprise", "trustworthy", "monitoring", "rag")):
            relevance += 8.0
        if any(term in lower for term in ("military", "defense", "weapon", "aerospace", "drone", "robotics")) and not any(term in lower for term in ("enterprise", "governance", "security", "compliance", "rag", "agent")):
            relevance -= 18.0
        if any(term in lower for term in ("clickbait", "celebrity", "viral challenge", "game trailer")):
            relevance -= 15.0
        if published_at:
            age_days = max(0, (_NOW() - published_at).days)
            relevance += max(0.0, 14.0 - age_days * 1.8)
        if matched_terms == 0 and "ai" not in lower:
            relevance -= 10.0
        return round(max(0.0, min(100.0, relevance)), 1)

    def _news_domain_alignment(self, query: str, text: str) -> float:
        lower = f"{query} {text}".lower()
        score = 0.0
        positive_terms = {
            "enterprise ai": 8.0,
            "governance": 7.0,
            "security": 7.0,
            "compliance": 7.0,
            "trustworthy ai": 6.0,
            "agentic ai": 9.0,
            "agent": 5.0,
            "ai agents": 8.0,
            "multi-agent": 7.0,
            "mcp": 8.0,
            "rag": 6.0,
            "llm": 6.0,
            "model monitoring": 7.0,
            "observability": 6.0,
            "workflow": 5.0,
            "enterprise automation": 6.0,
            "openai": 3.0,
            "anthropic": 3.0,
            "claude": 3.0,
            "chatgpt": 3.0,
            "gemini": 3.0,
        }
        negative_terms = {
            "military": -12.0,
            "defense": -12.0,
            "weapon": -14.0,
            "aerospace": -10.0,
            "drone": -8.0,
            "robotic": -8.0,
            "robotics": -8.0,
            "consumer": -5.0,
            "gadget": -5.0,
            "celebrity": -4.0,
        }
        for term, value in positive_terms.items():
            if term in lower:
                score += value
        for term, value in negative_terms.items():
            if term in lower:
                score += value
        if "autonomous systems" in lower and any(term in lower for term in ("military", "defense", "weapon", "aerospace")):
            score -= 15.0
        if "autonomous systems" in query.lower() and any(term in lower for term in ("agentic ai", "ai agents", "mcp", "multi-agent", "workflow", "enterprise automation")):
            score += 10.0
        return score

    def _infer_company_scale(self, source_notes: list[str]) -> str:
        joined = " ".join(source_notes).lower()
        if "fortune 500" in joined or "100+ trustworthy ai products" in joined:
            return "Mid-market and enterprise"
        return "51-200 employees"

    def _news_boost(self, news: list[dict[str, Any]]) -> float:
        if not news:
            return 0.0
        top_scores = sorted((item.get("relevance_score", 0.0) for item in news), reverse=True)[:5]
        return min(12.0, sum(top_scores) / max(len(top_scores), 1) / 20.0)

    def _opportunity_buyer(self, trend: str) -> str:
        return {
            "AI Governance": "Chief Risk Officer / AI Governance leader",
            "LLM Security": "CISO / AppSec lead",
            "Model Monitoring": "ML engineering / Platform team",
            "RAG": "Enterprise AI product owner",
        }.get(trend, "Enterprise AI decision maker")

    def _opportunity_value(self, trend: str) -> str:
        return {
            "AI Governance": "Reduces approval friction and creates an audit-ready buying process.",
            "LLM Security": "Helps security teams unblock deployment of customer-facing and internal AI applications.",
            "Model Monitoring": "Prevents silent model quality issues after production launch.",
            "RAG": "Improves answer quality, trust, and adoption for enterprise assistants.",
        }.get(trend, "Creates a cleaner path to production AI adoption.")

    def _recommendation_reason(self, trend: str, item: dict[str, Any], linkedin: dict[str, Any], competitors: list[dict[str, Any]]) -> str:
        if trend == "Agentic AI":
            return "Agentic AI adoption is accelerating, so governance controls should be positioned as a competitive advantage."
        if trend == "LLM Security":
            return "Security demand is increasing as enterprises push LLMs into regulated workflows."
        if trend == "AI Governance":
            return "Governance is the clearest language for translating risk reduction into business value."
        if trend == "Model Monitoring":
            return "Monitoring is the production control buyers expect after deployment."
        if trend == "AI Compliance":
            return "Compliance readiness can shorten buying cycles in regulated industries."
        return f"{trend} should be framed as a production readiness requirement supported by live company and competitor signals."

    def _recommendation_impact(self, trend: str) -> str:
        return {
            "Agentic AI": "Makes governance controls part of the agent rollout conversation.",
            "LLM Security": "Improves trust with security and compliance stakeholders.",
            "AI Governance": "Aligns the product story with procurement and board expectations.",
            "Model Monitoring": "Reduces operational risk after deployment.",
            "AI Compliance": "Strengthens enterprise proof points.",
        }.get(trend, "Creates a stronger enterprise AI value proposition.")

    def _recommendation_action(self, trend: str) -> str:
        return {
            "Agentic AI": "Publish a governance-first agent rollout narrative.",
            "LLM Security": "Lead with validation, guardrails, and red-team testing.",
            "AI Governance": "Translate controls into a board-ready control map.",
            "Model Monitoring": "Show observability, drift detection, and incident response workflows.",
            "AI Compliance": "Map product controls to regulated-industry evidence needs.",
        }.get(trend, "Package the signal into a board-ready executive story.")

    def _group_keywords(self, items: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
        grouped: dict[str, list[dict[str, Any]]] = {
            "Top AI Governance Keywords": [],
            "Fastest Growing Keywords": [],
            "Enterprise Adoption Keywords": [],
        }
        for item in items:
            bucket = item.get("keyword_group") or "Enterprise Adoption Keywords"
            grouped.setdefault(bucket, []).append(item)
        return grouped

    def _document_score(self, query_tokens: set[str], haystack: str, base_score: float) -> float:
        if not query_tokens:
            return max(base_score, 0.1)
        haystack_lower = haystack.lower()
        matches = sum(1 for token in query_tokens if token in haystack_lower)
        if not matches:
            return 0.0
        return base_score + matches * 10.0

    def _normalize_text_list(self, value: Any) -> list[str]:
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str):
            return [line.strip(" -") for line in value.splitlines() if line.strip(" -")]
        return []

    def _parse_json(self, text: str) -> Any:
        if not text:
            return None
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            cleaned = cleaned.replace("json", "", 1).strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return None

    def _xml_text(self, entry: ET.Element, tag: str) -> str:
        node = entry.find(tag)
        return _clean_text(node.text if node is not None else "")

    def _xml_source(self, entry: ET.Element) -> str:
        source = entry.find("source")
        return _clean_text(source.text if source is not None else "")

    def _sanitize_rss_text(self, value: Any) -> str:
        text = unescape(str(value or "")).strip()
        if not text:
            return ""
        soup = BeautifulSoup(text, "html.parser")
        cleaned = soup.get_text(" ", strip=True)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    def _sanitize_url(self, value: Any) -> str:
        text = unescape(str(value or "")).strip()
        if not text:
            return ""
        return text if text.startswith(("http://", "https://")) else ""


industry_intelligence_service = IndustryIntelligenceService()
