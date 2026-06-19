"""API routes for trend data."""

from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError

from backend.content_agent import ContentAgent
from backend.alert_agent import AlertAgent
from backend.auth import require_current_user
from backend.config import settings
from backend.database import (
    create_alert,
    get_industry_company,
    get_industry_competitors,
    get_industry_competitor_activity,
    get_industry_insights,
    get_industry_opportunities,
    get_industry_keywords,
    get_industry_live_trends,
    get_industry_recommendations,
    get_industry_report,
    get_industry_trends,
    get_trend_history,
    get_trend_history_leaderboard,
    refresh_industry_live_data,
    get_user_workspace,
    get_alerts,
    get_content_idea_by_trend_id,
    get_all_trends,
    get_high_viral_trends_without_alerts,
    get_post_performance_records,
    get_trend_by_id,
    get_unanalyzed_trends,
    get_trends_without_content_ideas,
    init_db,
    save_google_trends,
    save_content_idea,
    save_analysis_record,
    save_linkedin_post_record,
    save_post_performance_record,
    save_report_record,
    save_trends,
    update_trend_forecast,
    update_trend_analysis,
    mark_alert_as_read,
    _normalize_region_value,
)
from backend.services.gemini_service import GeminiService
from backend.services.industry_intelligence_service import industry_intelligence_service
from backend.services.forecast_service import ForecastService
from backend.services.creator_strategy_service import CreatorStrategyService
from backend.services.ai_chat_service import AIChatService
from backend.services.rag_service import RAGService
from backend.services.news_service import NewsService
from backend.services.insight_tools import InsightTools
from backend.services.report_service import report_service
from backend.services.youtube_service import YouTubeService
from backend.reddit_agent import RedditAgent
from backend.sentiment_agent import SentimentAgent
from backend.trend_fetcher import TrendFetcher
from backend.virality_agent import ViralityAgent
from backend.services.post_intelligence_service import analyze_creator_post, PostIntelligenceService
from backend.services.post_performance_service import track_post_performance
from backend.websocket_manager import websocket_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["AI"], dependencies=[Depends(require_current_user)])
dev_router = APIRouter(prefix="/api/dev", tags=["AI Dev"])
trend_fetcher = TrendFetcher()
sentiment_agent = SentimentAgent()
virality_agent = ViralityAgent()
reddit_agent = RedditAgent()
alert_agent = AlertAgent()
news_service = NewsService()
youtube_service = YouTubeService()
gemini_service = GeminiService()
rag_service = RAGService()
forecast_service = ForecastService()
content_agent = ContentAgent()
post_intelligence_service = PostIntelligenceService()
insight_tools = InsightTools()
creator_strategy_service = CreatorStrategyService()
ai_chat_service = AIChatService()


def _ensure_dev_validation_enabled() -> None:
    if settings.app_env.lower() not in {"development", "dev", "local"}:
        raise HTTPException(
            status_code=404,
            detail="Development validation endpoints are disabled outside development mode.",
        )


class CreatorIntelligenceRequest(BaseModel):
    platform: str
    title: str
    caption: str = ""
    hashtags: str | list[str] | None = None
    content_type: str = ""
    target_audience: str = ""
    audience: str = ""
    trend_region: str = "India"
    region: str = "India"
    thumbnail_result: dict[str, Any] | None = None


class PostPerformanceRequest(BaseModel):
    publishedPostUrl: str
    platform: str = ""
    region: str = "India"
    likes: int | None = None
    comments: int | None = None
    shares: int | None = None
    impressions: int | None = None
    post_age: str = "2 hours"


class LinkedInPostRequest(BaseModel):
    platform: Optional[str] = ""
    content_type: Optional[str] = ""
    audience: Optional[str] = ""
    title: Optional[str] = ""
    caption: Optional[str] = ""
    hashtags: Optional[str] = ""
    linkedin_profile: Optional[str] = "https://www.linkedin.com/in/charuka-p-91578b311"
    github_url: Optional[str] = "https://github.com/charupraba2"
    portfolio_url: Optional[str] = ""
    analysis_result: Optional[Dict[str, Any]] = None
    thumbnail_result: Optional[Dict[str, Any]] = None
    trends: Optional[List[Any]] = None
    latest_analysis_result: Optional[Dict[str, Any]] = None
    analysis: Optional[Dict[str, Any]] = None
    competitor_analysis: Optional[Dict[str, Any]] = None
    thumbnail_analysis: Optional[Dict[str, Any]] = None


class CompetitorAnalysisRequest(BaseModel):
    competitor: str
    topic: str | None = None
    platform: str | None = None
    region: str | None = "Global"


class TrendFetchRequest(BaseModel):
    region: str = "India"
    topic: str | None = None
    niche: str | None = None
    platform: str | None = None
    mode: str | None = None
    limit: int = 12


class ProductImpactRequest(BaseModel):
    feature_name: str = Field(..., min_length=1)
    feature_description: str = Field(default="")


def _region_to_country_code(region: str) -> str:
    region_key = str(region or "").strip().lower()
    if region_key in {"india", "tamil nadu", "chennai", "trichy"}:
        return "in"
    return "us"


def _region_to_youtube_code(region: str) -> str:
    region_key = str(region or "").strip().lower()
    if region_key == "india":
        return "IN"
    if region_key in {"tamil nadu", "chennai", "trichy"}:
        return "IN"
    return "US"


def _coerce_linkedin_context(payload: LinkedInPostRequest) -> dict:
    analysis = payload.analysis_result or payload.latest_analysis_result or payload.analysis or {}
    thumbnail_result = payload.thumbnail_result or payload.thumbnail_analysis or {}
    competitor_analysis = payload.competitor_analysis or analysis.get("competitor_analysis") or {}
    hashtags = payload.hashtags
    if hashtags is None:
        hashtags = analysis.get("hashtags") or analysis.get("normalized_hashtags") or []

    if isinstance(hashtags, list):
        hashtag_text = " ".join(str(item) for item in hashtags if item)
    else:
        hashtag_text = str(hashtags or "")

    current_request = analysis.get("current_request", {}) if isinstance(analysis, dict) else {}
    title = payload.title or current_request.get("title") or analysis.get("title") or ""
    caption = payload.caption or current_request.get("caption") or analysis.get("caption") or ""
    audience = payload.audience or current_request.get("audience") or analysis.get("audience") or ""
    platform = payload.platform or current_request.get("platform") or analysis.get("platform") or "linkedin"
    content_type = payload.content_type or current_request.get("content_type") or analysis.get("content_type") or ""

    merged = {
        **analysis,
        "platform": platform,
        "content_type": content_type,
        "audience": audience,
        "title": title,
        "caption": caption,
        "hashtags": hashtag_text,
        "analysis_result": analysis,
        "latest_analysis_result": analysis,
        "competitor_analysis": competitor_analysis,
        "thumbnail_result": thumbnail_result,
        "thumbnail_analysis": thumbnail_result,
        "linkedin_profile": payload.linkedin_profile or "https://www.linkedin.com/in/charuka-p-91578b311",
        "github_url": payload.github_url or "https://github.com/charupraba2",
        "portfolio_url": payload.portfolio_url or "",
        "trends": payload.trends or [],
    }
    if "current_request" not in merged:
        merged["current_request"] = {}
    merged["current_request"].update(
        {
            "platform": platform,
            "content_type": content_type,
            "audience": audience,
            "title": title,
            "caption": caption,
            "hashtags": hashtag_text,
        }
    )
    return merged


def build_linkedin_post(payload: LinkedInPostRequest) -> str:
    context = _coerce_linkedin_context(payload)
    logger.info(
        "LinkedIn request validation: platform=%s content_type=%s audience=%s title=%s analysis_result=%s thumbnail_result=%s trends=%s",
        context.get("platform"),
        context.get("content_type"),
        context.get("audience"),
        context.get("title"),
        bool(context.get("analysis_result")),
        bool(context.get("thumbnail_result")),
        len(context.get("trends") or []),
    )
    return insight_tools.generate_linkedin_post(context)


def _current_user_id(request: Request) -> int | None:
    user = getattr(request.state, "current_user", None)
    if isinstance(user, dict):
        try:
            return int(user.get("id") or 0) or None
        except (TypeError, ValueError):
            return None
    return None


def _creator_content_text(payload: CreatorIntelligenceRequest) -> str:
    hashtag_text = ""
    if isinstance(payload.hashtags, list):
        hashtag_text = " ".join(str(item) for item in payload.hashtags if item)
    elif payload.hashtags:
        hashtag_text = str(payload.hashtags)
    return " ".join(part for part in [payload.title, payload.caption, hashtag_text] if part).strip()


def _creator_analysis_response(payload: CreatorIntelligenceRequest) -> dict:
    region = payload.trend_region or payload.region or "India"
    try:
        result = analyze_creator_post(
            platform=payload.platform,
            title=payload.title,
            caption=payload.caption,
            hashtags=payload.hashtags,
            content_type=payload.content_type,
            target_audience=payload.target_audience,
            audience=payload.audience,
            region=region,
            thumbnail_result=payload.thumbnail_result,
        )
        analysis = result.get("analysis", {}) if isinstance(result, dict) else {}
        recommendations = result.get("recommendations", analysis) if isinstance(result, dict) else analysis
        current_trends = insight_tools.fetch_current_trends(region=region).get("items", [])
        trend_match = insight_tools.compare_keywords(content_text=_creator_content_text(payload), trends=current_trends, region=region)
        return {
            "success": True,
            **result,
            "analysis": analysis,
            "recommendations": recommendations,
            "region": region,
            **trend_match,
        }
    except ValueError as exc:
        logger.warning("Invalid creator analysis request: %s", exc)
        return {
            "success": False,
            "error": str(exc),
        }
    except Exception as exc:
        logger.exception("Creator analysis failed")
        fallback = post_intelligence_service._fallback_response(
            platform=payload.platform,
            title=payload.title,
            caption=payload.caption,
            hashtags=payload.hashtags,
            content_type=payload.content_type,
            audience=payload.target_audience or payload.audience,
            region=region,
            thumbnail_result=payload.thumbnail_result,
        )
        current_trends = insight_tools.fetch_current_trends(region=region).get("items", [])
        trend_match = insight_tools.compare_keywords(content_text=_creator_content_text(payload), trends=current_trends, region=region)
        return {
            "success": True,
            **fallback,
            "fallback_used": True,
            "error": str(exc),
            "region": region,
            **trend_match,
        }


@router.get("/trends")
def get_trends(region: str = "Global", platform: str = "all", category: str = "ai", topic: str | None = None, limit: int = 100):
    try:
        region_value = _normalize_region_value(region).lower()
        platform_value = str(platform or "all").strip().lower()
        category_value = _normalize_trend_category(category)
        topic_value = str(topic or "").strip().lower()
        print("Region:", region_value)
        print("Platform:", platform_value)
        print("Category:", category_value)
        trends = get_all_trends(limit=max(1, min(int(limit or 100), 250)), region=region_value)
        if region_value and region_value != "global":
            trends = [trend for trend in trends if str(trend.get("region") or "").strip().lower() == region_value]
        if platform_value and platform_value != "all":
            trends = [trend for trend in trends if str(trend.get("platform") or trend.get("source_type") or trend.get("source") or "").strip().lower() == platform_value]
        if category_value:
            trends = [trend for trend in trends if _trend_matches_category(trend, category_value, topic_value)]
        trends = _dedupe_trends(trends)
        alerts = get_alerts(200)
        alerted_trend_ids = {alert["trend_id"] for alert in alerts}
        trends_with_flags = [
            {
                **trend,
                "has_content_idea": get_content_idea_by_trend_id(trend["id"]) is not None,
                "has_alert": trend["id"] in alerted_trend_ids,
                "has_forecast": trend.get("prediction_label") is not None,
            }
            for trend in trends
        ]
        logger.info("Trend fetch filters region=%s platform=%s category=%s resultCount=%s", region_value, platform_value, category_value, len(trends_with_flags))
        if not trends_with_flags:
            return {
                "success": True,
                "trends": [],
                "items": [],
                "count": 0,
                "region": region_value,
                "platform": platform_value,
                "category": category_value,
                "message": f"No AI trends found for {region_value.title()}",
            }
        return {"success": True, "items": trends_with_flags, "trends": trends_with_flags, "count": len(trends_with_flags), "region": region_value, "platform": platform_value, "category": category_value}
    except Exception as exc:
        logger.exception("Failed /api/trends")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(exc),
            },
        )


def _normalize_trend_category(value: str | None) -> str:
    text = str(value or "ai").strip().lower().replace("_", " ").replace("-", " ")
    text = " ".join(text.split())
    aliases = {
        "ai": "ai",
        "artificial intelligence": "ai",
        "technology": "technology",
        "machine learning": "machine learning",
        "ml": "machine learning",
        "data science": "data science",
        "software development": "software development",
        "software dev": "software development",
        "startups": "startups",
        "startup": "startups",
        "business": "business",
        "finance": "finance",
        "education": "education",
        "healthcare": "healthcare",
        "sports": "sports",
        "entertainment": "entertainment",
        "marketing": "marketing",
        "cyber security": "cyber security",
        "cybersecurity": "cyber security",
        "security": "cyber security",
    }
    return aliases.get(text, text)


def _dedupe_trends(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str]] = set()
    deduped: list[dict[str, Any]] = []
    for item in items:
        title = str(item.get("title") or item.get("name") or "").strip().lower()
        source = str(item.get("source_label") or item.get("platform") or item.get("source") or "").strip().lower()
        key = (title, source)
        if not title or key in seen:
            continue
        seen.add(key)
        if "ai agents" in title and "linkedin" not in source and "news" not in source and "youtube" not in source and "reddit" not in source:
            continue
        if "prompt tools" in title and "linkedin" not in source and "news" not in source and "youtube" not in source and "reddit" not in source:
            continue
        if "ai video editing" in title and "linkedin" not in source and "news" not in source and "youtube" not in source and "reddit" not in source:
            continue
        deduped.append(item)
    return deduped


def _trend_matches_category(trend: dict[str, Any], category: str, topic: str = "") -> bool:
    haystack = " ".join(
        [
            str(trend.get("title") or ""),
            str(trend.get("name") or ""),
            str(trend.get("description") or trend.get("summary") or ""),
            str(trend.get("category") or ""),
            str(trend.get("platform") or ""),
            str(trend.get("source_label") or ""),
            topic,
        ]
    ).lower()
    mapping = {
        "ai": ["ai", "llm", "openai", "gemini", "chatgpt", "agents", "automation"],
        "technology": ["software", "cloud", "devops", "programming", "engineering", "technology"],
        "machine learning": ["machine learning", "ml", "model training", "prediction", "nlp"],
        "data science": ["data science", "analytics", "data", "visualization", "statistics"],
        "software development": ["software", "coding", "programming", "engineering", "developer"],
        "startups": ["startup", "founder", "funding", "seed", "series", "venture"],
        "business": ["business", "strategy", "revenue", "market", "enterprise"],
        "finance": ["finance", "bank", "fintech", "investment", "trading", "markets"],
        "education": ["college", "university", "exam", "course", "learning", "student"],
        "healthcare": ["health", "hospital", "medical", "clinical", "patient"],
        "sports": ["cricket", "ipl", "football", "olympics", "sports"],
        "entertainment": ["movie", "film", "tv", "music", "entertainment"],
        "marketing": ["marketing", "content", "campaign", "brand", "seo", "social"],
        "cyber security": ["security", "cyber", "threat", "vulnerability", "breach", "llm security"],
    }
    normalized = _normalize_trend_category(category)
    terms = mapping.get(normalized, [normalized])
    return any(term in haystack for term in terms)


@router.get("/industry/company")
def get_industry_company_endpoint():
    init_db()
    return {"success": True, "item": get_industry_company()}


@router.get("/industry/trends")
def get_industry_trends_endpoint():
    init_db()
    items = get_industry_trends()
    return {"success": True, "items": items, "count": len(items)}


@router.get("/industry/live-trends")
def get_industry_live_trends_endpoint():
    init_db()
    items = get_industry_live_trends()
    return {"success": True, "items": items, "count": len(items)}


@router.get("/industry/company-intelligence")
def get_industry_company_intelligence_endpoint():
    init_db()
    return {"success": True, "item": get_industry_company()}


@router.get("/industry/company-signals")
def get_industry_company_signals_endpoint():
    init_db()
    return industry_intelligence_service.get_company_signals()


@router.get("/industry/linkedin-intelligence")
def get_industry_linkedin_intelligence_endpoint():
    init_db()
    return industry_intelligence_service.get_linkedin_intelligence()


@router.get("/industry/linkedin-posts")
def get_industry_linkedin_posts_endpoint():
    init_db()
    return industry_intelligence_service.get_linkedin_posts()


@router.get("/industry/linkedin-themes")
def get_industry_linkedin_themes_endpoint():
    init_db()
    return industry_intelligence_service.get_linkedin_themes()


@router.get("/industry/news-intelligence")
def get_industry_news_intelligence_endpoint():
    init_db()
    return industry_intelligence_service.get_news_intelligence()


@router.get("/industry/competitor-signals")
def get_industry_competitor_signals_endpoint():
    init_db()
    return industry_intelligence_service.get_competitor_signals()


@router.get("/industry/executive-insights")
def get_industry_executive_insights_endpoint():
    init_db()
    return industry_intelligence_service.get_executive_insights()


@router.get("/industry/rag-analysis")
def get_industry_rag_analysis_endpoint(topic: str | None = None):
    init_db()
    return industry_intelligence_service.get_rag_analysis(topic=topic)


@router.get("/industry/board-report")
def get_industry_board_report_endpoint():
    init_db()
    return industry_intelligence_service.get_board_report()


def _build_industry_pdf_response(request: Request, payload: dict[str, Any] | None = None) -> Response:
    try:
        init_db()
        report_payload = payload if payload else industry_intelligence_service.build_industry_board_report_payload()
        report_payload = report_payload or {}
        pdf_bytes = report_service.build_industry_pdf(report_payload)
        filename = "industry_board_report.pdf"
        headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
        return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to build industry PDF report")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {exc}") from exc


@router.get("/industry/report/pdf")
def get_industry_report_pdf_endpoint(request: Request):
    return _build_industry_pdf_response(request)


@router.post("/industry/report/pdf")
def post_industry_report_pdf_endpoint(request: Request, payload: dict[str, Any] = Body(default_factory=dict)):
    return _build_industry_pdf_response(request, payload)


@router.post("/industry/refresh")
def refresh_industry_endpoint():
    try:
        init_db()
        snapshot = refresh_industry_live_data(force=True)
        linkedin = snapshot.get("linkedin", {}) or {}
        source_coverage = {
            "company": "Giggso Website" if snapshot.get("company") else "Unavailable",
            "linkedin": linkedin.get("source_label") or "Unavailable",
            "news": "Google News RSS" if snapshot.get("news") else "Unavailable",
            "competitors": "Web/Search Signals" if snapshot.get("competitor_signals") else "Unavailable",
            "insights": "Gemini / Fallback" if snapshot.get("insights") else "Fallback",
            "last_refreshed": snapshot.get("report", {}).get("generated_at").isoformat() if snapshot.get("report", {}).get("generated_at") else None,
        }
        return {
            "success": True,
            "message": "Industry intelligence refreshed.",
            "last_updated": snapshot["report"]["generated_at"].isoformat() if snapshot.get("report", {}).get("generated_at") else None,
            "source_coverage": source_coverage,
            "source_coverage_list": linkedin.get("source_coverage") or [],
        }
    except Exception as exc:
        logger.exception("Industry refresh failed")
        return {
            "success": False,
            "message": "Industry intelligence refresh completed with fallback data.",
            "error": str(exc),
            "source_coverage": {
                "company": "Giggso Website",
                "linkedin": "Fallback",
                "news": "Google News RSS",
                "competitors": "Web/Search Signals",
                "insights": "Fallback",
                "last_refreshed": None,
            },
            "source_coverage_list": [],
        }


@router.get("/industry/recommendations")
def get_industry_recommendations_endpoint():
    init_db()
    items = get_industry_recommendations()
    return {"success": True, "items": items, "count": len(items)}


@router.get("/industry/competitor-activity")
def get_industry_competitor_activity_endpoint():
    init_db()
    items = get_industry_competitor_activity()
    return {"success": True, "items": items, "count": len(items)}


@router.get("/industry/keywords")
def get_industry_keywords_endpoint():
    init_db()
    items = get_industry_keywords()
    grouped: dict[str, list[dict]] = {}
    for item in items:
        grouped.setdefault(item.get("keyword_group") or "Other", []).append(item)
    return {"success": True, "items": items, "groups": grouped, "count": len(items)}


@router.get("/industry/report")
def get_industry_report_endpoint():
    init_db()
    report = get_industry_report()
    return {"success": True, "item": report}


@router.get("/industry/competitors")
def get_industry_competitors_endpoint():
    init_db()
    items = get_industry_competitors()
    return {"success": True, "items": items, "count": len(items)}


@router.get("/industry/insights")
def get_industry_insights_endpoint():
    init_db()
    items = get_industry_insights()
    return {"success": True, "items": items, "count": len(items)}


@router.get("/industry/opportunities")
def get_industry_opportunities_endpoint():
    init_db()
    items = get_industry_opportunities()
    return {"success": True, "items": items, "count": len(items)}


@router.post("/industry/product-impact")
def analyze_product_impact_endpoint(payload: ProductImpactRequest):
    init_db()
    return industry_intelligence_service.analyze_product_impact(payload.feature_name, payload.feature_description)


@router.get("/industry/search")
def search_industry_endpoint(q: str = ""):
    init_db()
    query = (q or "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="q is required")
    return industry_intelligence_service.search_intelligence(query)


@router.get("/industry/compare")
def compare_industry_endpoint(q1: str = "", q2: str = ""):
    init_db()
    left = (q1 or "").strip()
    right = (q2 or "").strip()
    if not left or not right:
        raise HTTPException(status_code=400, detail="q1 and q2 are required")
    return industry_intelligence_service.compare_intelligence(left, right)


@router.get("/industry/validation-report")
def get_industry_validation_report_endpoint():
    init_db()
    return industry_intelligence_service.get_validation_report()


@router.get("/industry/history")
def get_industry_history_endpoint(keyword: str = "", range: str = "7d"):
    init_db()
    query = (keyword or "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="keyword is required")
    history = get_trend_history(query, range_label=range)
    if not history:
        return {
            "success": False,
            "keyword": query,
            "current_score": 0,
            "previous_score": 0,
            "delta": 0,
            "direction": "stable",
            "movement_label": "Stable",
            "history": [],
            "range": str(range or "7d").lower(),
        }
    return {"success": True, **history}


@router.get("/industry/history/leaderboard")
def get_industry_history_leaderboard_endpoint(range: str = "7d"):
    init_db()
    return {"success": True, **get_trend_history_leaderboard(range_label=range)}


@dev_router.get("/industry/search")
def dev_search_industry_endpoint(q: str = ""):
    _ensure_dev_validation_enabled()
    query = (q or "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="q is required")
    return industry_intelligence_service.search_intelligence(query)


@dev_router.get("/industry/compare")
def dev_compare_industry_endpoint(q1: str = "", q2: str = ""):
    _ensure_dev_validation_enabled()
    left = (q1 or "").strip()
    right = (q2 or "").strip()
    if not left or not right:
        raise HTTPException(status_code=400, detail="q1 and q2 are required")
    return industry_intelligence_service.compare_intelligence(left, right)


@dev_router.post("/industry/product-impact")
def dev_analyze_product_impact_endpoint(payload: ProductImpactRequest):
    _ensure_dev_validation_enabled()
    return industry_intelligence_service.analyze_product_impact(payload.feature_name, payload.feature_description)


@dev_router.get("/industry/validation-report")
def dev_validation_report_endpoint():
    _ensure_dev_validation_enabled()
    return industry_intelligence_service.get_validation_report()


@dev_router.get("/industry/history")
def dev_get_industry_history_endpoint(keyword: str = "", range: str = "7d"):
    _ensure_dev_validation_enabled()
    query = (keyword or "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="keyword is required")
    history = get_trend_history(query, range_label=range)
    if not history:
        return {
            "success": False,
            "keyword": query,
            "current_score": 0,
            "previous_score": 0,
            "delta": 0,
            "direction": "stable",
            "movement_label": "Stable",
            "history": [],
            "range": str(range or "7d").lower(),
        }
    return {"success": True, **history}


@dev_router.get("/industry/history/leaderboard")
def dev_get_industry_history_leaderboard_endpoint(range: str = "7d"):
    _ensure_dev_validation_enabled()
    return {"success": True, **get_trend_history_leaderboard(range_label=range)}


@dev_router.get("/industry/report/pdf")
def dev_get_industry_report_pdf_endpoint(request: Request):
    _ensure_dev_validation_enabled()
    return _build_industry_pdf_response(request)


@dev_router.post("/industry/report/pdf")
def dev_post_industry_report_pdf_endpoint(request: Request, payload: dict[str, Any] = Body(default_factory=dict)):
    _ensure_dev_validation_enabled()
    return _build_industry_pdf_response(request, payload)


@router.post("/analyze")
async def analyze(request: Request, payload: CreatorIntelligenceRequest):
    return await analyze_post(request, payload)


@router.get("/current-trends")
def get_current_trends(region: str = "US", limit: int = 12):
    try:
        payload = insight_tools.fetch_current_trends(region=region, limit=limit)
        return payload
    except Exception as exc:
        logger.exception("Failed to fetch current trends")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {exc}") from exc


def _resolve_trend_fetch_query(payload: TrendFetchRequest) -> dict[str, Any]:
    topic = (payload.topic or payload.niche or payload.mode or "").strip()
    platform = (payload.platform or "all").strip()
    region = (payload.region or "India").strip()
    return {
        "topic": topic,
        "platform": platform,
        "region": region,
        "limit": max(1, min(int(payload.limit or 12), 24)),
    }


async def _fetch_trends_impl(payload: TrendFetchRequest):
    try:
        fetch_args = _resolve_trend_fetch_query(payload)
        logger.info(
            "Fetching trend radar data for region=%s topic=%s platform=%s limit=%s",
            fetch_args["region"],
            fetch_args["topic"],
            fetch_args["platform"],
            fetch_args["limit"],
        )
        result = insight_tools.fetch_current_trends(
            region=fetch_args["region"],
            limit=fetch_args["limit"],
            topic=fetch_args["topic"] or None,
            niche=payload.niche,
            platform=fetch_args["platform"],
            mode=payload.mode,
        )
        init_db()
        for item in result.get("items", []):
            item["region"] = fetch_args["region"]
            if fetch_args["topic"]:
                item["topic"] = fetch_args["topic"]
        save_trends(result.get("items", []))
        return {
            **result,
            "success": True,
            "selected_region": fetch_args["region"],
            "selected_topic": fetch_args["topic"],
            "selected_niche": payload.niche or "",
            "selected_platform": fetch_args["platform"],
        }
    except Exception as exc:
        logger.exception("Failed to fetch trend radar data")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {exc}") from exc


@router.get("/trends/fetch")
async def fetch_trends_get(
    region: str = "India",
    topic: str | None = None,
    niche: str | None = None,
    platform: str | None = None,
    mode: str | None = None,
    limit: int = 12,
):
    payload = TrendFetchRequest(region=region, topic=topic, niche=niche, platform=platform, mode=mode, limit=limit)
    return await _fetch_trends_impl(payload)


@router.post("/trends/fetch")
async def fetch_trends_post(payload: TrendFetchRequest):
    return await _fetch_trends_impl(payload)


@router.get("/fetch-trends")
async def fetch_trends_legacy_get(
    region: str = "India",
    topic: str | None = None,
    niche: str | None = None,
    platform: str | None = None,
    mode: str | None = None,
    limit: int = 12,
):
    payload = TrendFetchRequest(region=region, topic=topic, niche=niche, platform=platform, mode=mode, limit=limit)
    return await _fetch_trends_impl(payload)


@router.post("/fetch-trends")
async def fetch_trends_legacy_post(payload: TrendFetchRequest):
    return await _fetch_trends_impl(payload)


@router.get("/trends/{trend_id}")
def get_trend(trend_id: int):
    trend = get_trend_by_id(trend_id)
    if trend is None:
        raise HTTPException(status_code=404, detail="Trend not found")
    trend["content_brief"] = content_agent.build_content_brief(trend)
    trend["content_idea"] = get_content_idea_by_trend_id(trend_id)
    sentiment = sentiment_agent.analyze_text(trend.get("summary") or trend.get("title", ""))
    virality = virality_agent.analyze_trend({**trend, **sentiment})
    trend.update(sentiment)
    trend.update(virality)
    return trend


@router.get("/fetch-live-trends")
async def fetch_live_trends(keyword: str | None = None, region_code: str = "US", region: str = "Global"):
    """Fetch news and YouTube live trends in one request."""

    try:
        init_db()
        if keyword:
            news_keyword = f"{keyword} {region}".strip()
            news_trends = news_service.search_news(news_keyword)
        else:
            news_trends = news_service.fetch_latest_trending_news(country=_region_to_country_code(region))
        youtube_region_code = region_code or _region_to_youtube_code(region)
        youtube_trends = youtube_service.fetch_trending_videos(region_code=youtube_region_code)
        for trend in [*news_trends, *youtube_trends]:
            trend["region"] = region
        news_saved = save_trends(news_trends)
        youtube_saved = save_trends(youtube_trends)
        for trend in [*news_trends, *youtube_trends]:
            await websocket_manager.broadcast_event(
                "trend_update",
                {
                    "action": "created",
                    "trend": websocket_manager._trend_snapshot(trend),
                },
            )
        await websocket_manager.broadcast_event(
            "activity",
            {
                "message": f"Fetched {len(news_trends) + len(youtube_trends)} live trends from NEWS and YOUTUBE.",
                "level": "success",
                "kind": "trend_fetch",
                "source": "live",
                "count": len(news_trends) + len(youtube_trends),
            },
        )
        logger.info(
            "Fetched live trends successfully: NEWS=%s YOUTUBE=%s saved=%s",
            len(news_trends),
            len(youtube_trends),
            news_saved + youtube_saved,
        )
        return {
            "success": True,
            "sources": ["NEWS", "YOUTUBE"],
            "count": len(news_trends) + len(youtube_trends),
            "saved": news_saved + youtube_saved,
            "items": [*news_trends, *youtube_trends],
            "demo_mode": any(item.get("source_type") in {"news_demo", "youtube_demo"} for item in [*news_trends, *youtube_trends]),
            "region": region,
        }
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail=f"Database error: {exc}") from exc
    except Exception as exc:
        logger.exception("Failed to fetch live trends")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {exc}") from exc


@router.get("/forecast-trend")
async def forecast_trend(title: str, description: str = "", region: str = "Global"):
    """Forecast a single trend using historical context and Gemini."""

    try:
        init_db()
        if not title or not title.strip():
            raise HTTPException(status_code=400, detail="title is required")

        result = forecast_service.forecast_trend_growth(title=title, description=description, region=region)
        matched_trend = result.get("trend") or {}
        forecast = result.get("forecast", {})
        updated = None

        if matched_trend.get("id") is not None:
            updated = update_trend_forecast(matched_trend["id"], forecast)
            if updated is not None:
                result["trend"] = updated
                websocket_manager.broadcast_forecast_update(
                    {
                        "action": "updated",
                        "trend": websocket_manager._trend_snapshot(updated),
                        "forecast": forecast,
                        "similar_trends": result.get("similar_trends", []),
                    }
                )

        await websocket_manager.broadcast_event(
            "activity",
            {
                "message": f"Forecast generated for {title}.",
                "level": "success",
                "kind": "forecast",
                "title": title,
            },
        )
        return {"success": True, **result, "saved": updated is not None, "region": region}
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail=f"Database error: {exc}") from exc
    except HTTPException:
        raise
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Failed to forecast trend")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {exc}") from exc


@router.get("/forecast-live-trends")
async def forecast_live_trends(region: str = "Global"):
    """Forecast all stored trends and persist the prediction fields."""

    try:
        init_db()
        trends = get_all_trends(region=region)
        if not trends:
            return {
                "success": True,
                "count": 0,
                "items": [],
                "message": "No stored trends found to forecast.",
            }

        forecasted: list[dict] = []
        for trend in trends:
            title = trend.get("title") or trend.get("name") or "Untitled trend"
            description = trend.get("description") or trend.get("summary") or ""
            result = forecast_service.forecast_trend_growth(title=title, description=description, trend=trend, region=region)
            forecast = result.get("forecast", {})
            updated = update_trend_forecast(trend["id"], forecast)
            merged = updated or {**trend, **forecast}
            merged["similar_trends"] = result.get("similar_trends", [])
            merged["current_trend"] = result.get("current_trend")
            forecasted.append(merged)
            websocket_manager.broadcast_forecast_update(
                {
                    "action": "updated",
                    "trend": websocket_manager._trend_snapshot(merged),
                    "forecast": forecast,
                    "similar_trends": result.get("similar_trends", []),
                }
            )

        await websocket_manager.broadcast_event(
            "activity",
            {
                "message": f"Forecasted {len(forecasted)} active trends.",
                "level": "success",
                "kind": "forecast",
                "count": len(forecasted),
            },
        )
        return {
            "success": True,
            "count": len(forecasted),
            "items": forecasted,
        }
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail=f"Database error: {exc}") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Failed to forecast live trends")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {exc}") from exc


@router.get("/fetch-reddit-trends")
async def fetch_reddit_trends(region: str = "Global"):
    """Fetch Reddit trends and persist them to SQLite."""

    try:
        init_db()
        trends = reddit_agent.fetch_trends()
        for trend in trends:
            trend["region"] = region
        inserted = save_trends(trends)
        for trend in trends:
            await websocket_manager.broadcast_event(
                "trend_update",
                {
                    "action": "created",
                    "trend": websocket_manager._trend_snapshot(trend),
                },
            )
        await websocket_manager.broadcast_event(
            "activity",
            {
                "message": f"Fetched {len(trends)} Reddit trends.",
                "level": "success",
                "kind": "trend_fetch",
                "source": "reddit",
                "count": len(trends),
            },
        )
        return {
            "success": True,
            "source": "reddit",
            "count": len(trends),
            "saved": inserted,
            "demo_mode": not reddit_agent.has_credentials(),
            "items": trends,
            "region": region,
        }
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail=f"Database error: {exc}") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {exc}") from exc


@router.get("/fetch-google-trends")
async def fetch_google_trends(region: str = "Global"):
    """Fetch Google Trends data and persist it to SQLite."""

    try:
        init_db()
        trends = trend_fetcher.fetch_google_trends()
        for trend in trends:
            trend["region"] = region
        inserted = save_google_trends(trends)
        demo_mode = any(item.get("source_type") == "google_demo" for item in trends)
        for trend in trends:
            await websocket_manager.broadcast_event(
                "trend_update",
                {
                    "action": "created",
                    "trend": websocket_manager._trend_snapshot(trend),
                },
            )
        await websocket_manager.broadcast_event(
            "activity",
            {
                "message": f"Fetched {len(trends)} Google Trends items.",
                "level": "success",
                "kind": "trend_fetch",
                "source": "google_trends",
                "count": len(trends),
            },
        )
        return {
            "success": True,
            "source": "google_trends",
            "count": len(trends),
            "saved": inserted,
            "demo_mode": demo_mode,
            "items": trends,
            "region": region,
        }
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail=f"Database error: {exc}") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {exc}") from exc


@router.get("/fetch-news-trends")
async def fetch_news_trends(keyword: str | None = None, region: str = "Global"):
    """Fetch latest news trends or search by keyword and persist them."""

    try:
        init_db()
        if keyword:
            search_keyword = f"{keyword} {region}".strip()
            trends = news_service.search_news(search_keyword)
        else:
            trends = news_service.fetch_latest_trending_news(country=_region_to_country_code(region))
        for trend in trends:
            trend["region"] = region
        inserted = save_trends(trends)
        demo_mode = any(item.get("source_type") == "news_demo" for item in trends)
        for trend in trends:
            await websocket_manager.broadcast_event(
                "trend_update",
                {
                    "action": "created",
                    "trend": websocket_manager._trend_snapshot(trend),
                },
            )
        await websocket_manager.broadcast_event(
            "activity",
            {
                "message": f"Fetched {len(trends)} NEWS trends.",
                "level": "success",
                "kind": "trend_fetch",
                "source": "NEWS",
                "count": len(trends),
            },
        )
        logger.info(
            "News trends fetched: source_type=NEWS fetched=%s saved=%s demo_mode=%s",
            len(trends),
            inserted,
            demo_mode,
        )
        return {
            "success": True,
            "source": "NEWS",
            "count": len(trends),
            "saved": inserted,
            "demo_mode": demo_mode,
            "items": trends,
            "keyword": keyword,
            "region": region,
        }
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail=f"Database error: {exc}") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Failed to fetch news trends")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {exc}") from exc


@router.get("/fetch-youtube-trends")
async def fetch_youtube_trends(region_code: str = "US", region: str = "Global"):
    """Fetch trending YouTube videos and persist them."""

    try:
        init_db()
        region_code = region_code or _region_to_youtube_code(region)
        trends = youtube_service.fetch_trending_videos(region_code=region_code)
        for trend in trends:
            trend["region"] = region
        inserted = save_trends(trends)
        demo_mode = any(item.get("source_type") == "youtube_demo" for item in trends)
        for trend in trends:
            await websocket_manager.broadcast_event(
                "trend_update",
                {
                    "action": "created",
                    "trend": websocket_manager._trend_snapshot(trend),
                },
            )
        await websocket_manager.broadcast_event(
            "activity",
            {
                "message": f"Fetched {len(trends)} YOUTUBE trends.",
                "level": "success",
                "kind": "trend_fetch",
                "source": "YOUTUBE",
                "count": len(trends),
            },
        )
        logger.info(
            "YouTube trends fetched: source_type=YOUTUBE fetched=%s saved=%s demo_mode=%s",
            len(trends),
            inserted,
            demo_mode,
        )
        return {
            "success": True,
            "source": "YOUTUBE",
            "count": len(trends),
            "saved": inserted,
            "demo_mode": demo_mode,
            "items": trends,
            "region_code": region_code,
            "region": region,
        }
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail=f"Database error: {exc}") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Failed to fetch YouTube trends")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {exc}") from exc


@router.get("/analyze-trend")
async def analyze_trend(title: str, description: str = "", region: str = "Global"):
    """Analyze a single live trend with Gemini and return AI insights."""

    try:
        payload = gemini_service.analyze_trend(title=title, description=description)
        logger.info("AI analysis completed for trend title=%s", title)
        await websocket_manager.broadcast_event(
            "activity",
            {
                "message": f"AI generated a new recommendation for {title}.",
                "level": "success",
            },
        )
        return {"success": True, "item": payload, "region": region}
    except Exception as exc:
        logger.exception("Failed to analyze trend with Gemini")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {exc}") from exc


async def _broadcast_creator_analysis(payload: CreatorIntelligenceRequest, result: dict) -> None:
    analysis = result.get("analysis", {}) if isinstance(result, dict) else {}
    await websocket_manager.broadcast_event(
        "creator_analysis",
        {
            "current_request": result.get("current_request", {}) if isinstance(result, dict) else {},
            "analysis": analysis,
            "similar_trends": result.get("similar_trends", []) if isinstance(result, dict) else [],
            "forecast": result.get("forecast", {}) if isinstance(result, dict) else {},
            "rag_analysis": result.get("rag_analysis", {}) if isinstance(result, dict) else {},
            "warnings": result.get("warnings", []) if isinstance(result, dict) else [],
        },
    )
    if float(analysis.get("virality_score") or 0) >= 75 or str(analysis.get("prediction_label") or "").upper() == "EXPLODING":
        await websocket_manager.broadcast_event(
            "activity",
            {
                "message": f"High-potential post detected: {payload.title}.",
                "level": "success",
                "kind": "creator_analysis",
                "platform": payload.platform,
            },
        )
    else:
        await websocket_manager.broadcast_event(
            "activity",
            {
                "message": f"Creator analysis completed for {payload.title}.",
                "level": "info",
                "kind": "creator_analysis",
                "platform": payload.platform,
            },
        )


@router.post("/track-post-performance")
async def track_post_performance_route(request: Request, payload: PostPerformanceRequest):
    """Track a published post and generate performance intelligence."""
    return await _track_post_performance_core(
        request=request,
        post_url=payload.publishedPostUrl,
        region=payload.region,
        platform=payload.platform,
        manual_metrics={
            "likes": payload.likes,
            "comments": payload.comments,
            "shares": payload.shares,
            "impressions": payload.impressions,
            "post_age": payload.post_age,
        },
    )


@router.post("/track-post")
async def track_post_route(request: Request, payload: dict = Body(...)):
    """Compatibility route for older frontend builds."""

    return await _track_post_performance_core(
        request=request,
        post_url=str(payload.get("post_url") or payload.get("publishedPostUrl") or "").strip(),
        region=str(payload.get("region") or "India"),
        platform=str(payload.get("platform") or ""),
        manual_metrics={
            "likes": payload.get("likes"),
            "comments": payload.get("comments"),
            "shares": payload.get("shares"),
            "impressions": payload.get("impressions"),
            "post_age": payload.get("post_age") or payload.get("postAge") or "2 hours",
        },
    )


async def _track_post_performance_core(request: Request, post_url: str, region: str, platform: str, manual_metrics: dict[str, Any] | None = None):
    init_db()
    user_id = _current_user_id(request)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Authentication required")

    logger.info(
        "Received post performance tracking request: url=%s region=%s platform=%s",
        post_url,
        region,
        platform,
    )

    try:
        result = track_post_performance(
            post_url=post_url,
            region=region,
            platform=platform,
            user_id=user_id,
            manual_metrics=manual_metrics or {},
        )
        performance = result.get("performance", {})
        recommendations = result.get("recommendations", {})
        forecast = result.get("forecast", {})
        chart_data = result.get("chart_data", {})
        current_post = result.get("current_post", {})

        saved = save_post_performance_record(
            user_id=user_id,
            post_url=post_url,
            payload=current_post,
            platform=str(performance.get("platform") or platform or "instagram"),
            region=str(performance.get("region") or region or "India"),
            content_title=str(performance.get("content_title") or current_post.get("content_title") or "Published post"),
            likes=int(performance.get("likes") or 0),
            comments=int(performance.get("comments") or 0),
            shares=int(performance.get("shares") or 0),
            reach=int(performance.get("reach") or 0),
            impressions=int(performance.get("impressions") or 0),
            engagement_growth=float(performance.get("engagement_growth") or 0),
            virality_momentum=float(performance.get("virality_momentum") or 0),
            growth_speed=float(performance.get("growth_speed") or 0),
            trend_strength=float(performance.get("trend_strength") or 0),
            engagement_velocity=float(performance.get("engagement_velocity") or 0),
            trend_relevance=float(performance.get("trend_relevance") or 0),
            lifecycle_stage=str(performance.get("lifecycle_stage") or "Stable"),
            should_repost=bool(recommendations.get("should_repost")),
            should_improve_hook=bool(recommendations.get("should_improve_hook")),
            should_shorten_caption=bool(recommendations.get("should_shorten_caption")),
            should_follow_up=bool(recommendations.get("should_follow_up")),
            is_saturated=bool(performance.get("is_saturated")),
            expected_reach=int(forecast.get("expected_reach") or 0),
            expected_impressions=int(forecast.get("expected_impressions") or 0),
            peak_engagement_time=str(forecast.get("peak_engagement_time") or ""),
            engagement_decay=float(performance.get("engagement_decay") or forecast.get("engagement_decay") or 0),
            live_metrics_available=bool(performance.get("live_metrics_available")),
            recommendations=recommendations,
            forecast=forecast,
            chart_data=chart_data,
        )

        await websocket_manager.broadcast_event(
            "performance_update",
            {
                "action": "tracked",
                "performance": saved,
                "recommendations": recommendations,
                "forecast": forecast,
                "chart_data": chart_data,
            },
        )
        await websocket_manager.broadcast_event(
            "activity",
            {
                "message": f"Tracked published post performance for {saved.get('content_title') or post_url}.",
                "level": "success",
                "kind": "performance_tracking",
                "platform": saved.get("platform"),
                "region": saved.get("region"),
            },
        )
        return {
            "success": True,
            **result,
            "performance": saved,
            "saved": True,
        }
    except ValueError as exc:
        return {"success": False, "error": str(exc)}
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail=f"Database error: {exc}") from exc
    except Exception as exc:
        logger.exception("Post performance tracking failed")
        fallback = track_post_performance(
            post_url=post_url,
            region=region,
            platform=platform,
            user_id=user_id,
            manual_metrics=manual_metrics or {},
        )
        return {
            "success": True,
            **fallback,
            "fallback_used": True,
            "error": str(exc),
        }


@router.get("/post-performance")
def get_post_performance(limit: int = 10):
    """Return recent tracked post performance records."""

    try:
        records = get_post_performance_records(limit=max(1, min(limit, 20)))
        latest = records[0] if records else None
        return {
            "success": True,
            "count": len(records),
            "latest": latest,
            "items": records,
        }
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail=f"Database error: {exc}") from exc
    except Exception as exc:
        logger.exception("Failed to load post performance records")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {exc}") from exc


def _analyze_post_core(request: Request, payload: CreatorIntelligenceRequest) -> dict:
    """Shared creator analysis handler used by all legacy route aliases."""

    init_db()
    logger.info(
        "Received creator analysis request: platform=%s title=%s target_audience=%s content_type=%s",
        payload.platform,
        payload.title,
        payload.target_audience or payload.audience,
        payload.content_type,
    )
    if not payload.title or not payload.title.strip():
        return {
            "success": False,
            "error": "title is required",
        }

    result = _creator_analysis_response(payload)
    if result.get("success"):
        user_id = _current_user_id(request)
        if user_id is not None:
            try:
                analysis = result.get("analysis", {}) if isinstance(result, dict) else {}
                save_analysis_record(
                    user_id=user_id,
                    payload=result,
                    trend_title=str(result.get("current_request", {}).get("title") or payload.title),
                    platform=str(result.get("current_request", {}).get("platform") or payload.platform),
                    trend_match_score=analysis.get("trend_match_score"),
                    virality_score=analysis.get("virality_score"),
                )
            except Exception:
                logger.exception("Failed to save creator analysis record")
        logger.info(
            "Creator analysis completed for platform=%s title=%s virality_score=%s",
            result.get("current_request", {}).get("platform"),
            result.get("current_request", {}).get("title"),
            result.get("analysis", {}).get("virality_score"),
        )
    return result


@router.post("/analyze-post")
async def analyze_post(request: Request, payload: CreatorIntelligenceRequest):
    """Analyze a creator-submitted post and return optimization recommendations."""

    result = _analyze_post_core(request, payload)
    if result.get("success"):
        await _broadcast_creator_analysis(payload, result)
    return result


@router.post("/analyze-post/")
async def analyze_post_with_trailing_slash(request: Request, payload: CreatorIntelligenceRequest):
    """Compatibility alias for clients that send a trailing slash."""

    result = _analyze_post_core(request, payload)
    if result.get("success"):
        await _broadcast_creator_analysis(payload, result)
    return result


@router.post("/analyze-content")
async def analyze_content_alias(request: Request, payload: CreatorIntelligenceRequest):
    """Backward-compatible alias for older frontend builds."""

    result = _analyze_post_core(request, payload)
    if result.get("success"):
        await _broadcast_creator_analysis(payload, result)
    return result


@router.post("/generate-linkedin-post")
async def generate_linkedin_post(payload: dict = Body(...)):
    try:
        logger.info(
            "LinkedIn generation payload received with keys=%s",
            sorted(payload.keys()) if isinstance(payload, dict) else [],
        )

        analysis = payload.get("analysis_result") or payload.get("latest_analysis_result") or payload.get("analysis") or {}
        thumbnail_result = (
            payload.get("thumbnail_result")
            or payload.get("thumbnail_analysis")
            or (analysis.get("thumbnail_result") if isinstance(analysis, dict) else None)
            or (analysis.get("thumbnail_analysis") if isinstance(analysis, dict) else None)
            or {}
        )
        current_request = analysis.get("current_request", {}) if isinstance(analysis, dict) else {}

        title = str(payload.get("title") or current_request.get("title") or analysis.get("title") or "").strip()
        caption = str(payload.get("caption") or current_request.get("caption") or analysis.get("caption") or "").strip()
        hashtags_value = payload.get("hashtags") or current_request.get("hashtags") or analysis.get("hashtags") or analysis.get("normalized_hashtags") or []
        platform = str(payload.get("platform") or current_request.get("platform") or analysis.get("platform") or "LinkedIn").strip()
        audience = str(payload.get("audience") or current_request.get("audience") or analysis.get("audience") or "").strip()
        linkedin_profile = str(payload.get("linkedin_profile") or "https://www.linkedin.com/in/charuka-p-91578b311").strip()
        github_url = str(payload.get("github_url") or "https://github.com/charupraba2").strip()

        if isinstance(hashtags_value, list):
            hashtags = " ".join(str(item).strip() for item in hashtags_value if str(item).strip())
        else:
            hashtags = str(hashtags_value or "").strip()

        thumbnail_summary = []
        if isinstance(thumbnail_result, dict) and thumbnail_result:
            thumbnail_summary.append(f"Thumbnail score: {thumbnail_result.get('thumbnail_score', 'n/a')}%")
            if thumbnail_result.get("file_name"):
                thumbnail_summary.append(f"File: {thumbnail_result.get('file_name')}")
            if thumbnail_result.get("width") and thumbnail_result.get("height"):
                thumbnail_summary.append(f"Resolution: {thumbnail_result.get('width')} x {thumbnail_result.get('height')}")
            if thumbnail_result.get("brightness") is not None:
                thumbnail_summary.append(f"Brightness: {thumbnail_result.get('brightness')}")
            if thumbnail_result.get("contrast") is not None:
                thumbnail_summary.append(f"Contrast: {thumbnail_result.get('contrast')}")

        image_context_parts: list[str] = []
        if isinstance(thumbnail_result, dict):
            image_context_parts.extend([
                str(thumbnail_result.get("topic") or "").strip(),
                str(thumbnail_result.get("visible_text") or "").strip(),
                str(thumbnail_result.get("visual_theme") or "").strip(),
                str(thumbnail_result.get("learning_context") or "").strip(),
                str(thumbnail_result.get("project_context") or "").strip(),
                str(thumbnail_result.get("context_summary") or "").strip(),
            ])
            image_context_parts.extend(str(item).strip() for item in (thumbnail_result.get("suggestions") or []) if str(item).strip())
            image_context_parts.extend(str(item).strip() for item in (thumbnail_result.get("issues") or []) if str(item).strip())
        image_context = " ".join(part for part in image_context_parts if part)

        title_caption_context = " ".join(part for part in [title, caption] if part).strip()
        if not title_caption_context and not image_context:
            raise HTTPException(status_code=400, detail="Please enter content or upload an image first.")

        inferred_topic = title or str(thumbnail_result.get("topic") or "").strip() or "the project"
        visible_text = str(thumbnail_result.get("visible_text") or thumbnail_result.get("text") or "").strip()
        visual_theme = str(thumbnail_result.get("visual_theme") or thumbnail_result.get("theme") or "").strip()
        learning_context = str(thumbnail_result.get("learning_context") or thumbnail_result.get("context_summary") or "").strip()
        project_context = str(thumbnail_result.get("project_context") or thumbnail_result.get("project_type") or "").strip()
        thumbnail_score = thumbnail_result.get("thumbnail_score")
        thumbnail_suggestions = thumbnail_result.get("suggestions") or []

        opening_line = caption or title_caption_context or (
            f"I shared a quick learning note on {inferred_topic} and how it connects with real-world projects."
            if any(token in f"{image_context} {title_caption_context}".lower() for token in ["ai", "ml", "machine", "model", "python", "fastapi", "technical", "learning"])
            else f"Sharing a small progress update from my {project_context or 'AI project'} dashboard."
        )

        image_insights = []
        if inferred_topic:
            image_insights.append(f"Topic: {inferred_topic}")
        if visible_text:
            image_insights.append(f"Visible text: {visible_text}")
        if visual_theme:
            image_insights.append(f"Visual theme: {visual_theme}")
        if learning_context:
            image_insights.append(f"Learning context: {learning_context}")
        if project_context:
            image_insights.append(f"Project context: {project_context}")
        if thumbnail_score is not None:
            image_insights.append(f"Thumbnail score: {thumbnail_score}%")

        hook = f"Here’s a quick update from {inferred_topic}."
        if visible_text:
            hook = f"Turning the visual note on '{visible_text}' into a quick LinkedIn update."
        elif learning_context:
            hook = f"Sharing a quick learning note on {learning_context}."
        elif project_context:
            hook = f"Sharing a small progress update from my {project_context} project."

        story = opening_line
        if not story.endswith((".", "!", "?")):
            story += "."
        detail_line = ""
        if image_insights:
            detail_line = "Image context: " + " | ".join(image_insights)

        if thumbnail_suggestions:
            suggestion_line = "Takeaway: " + " ".join(str(item).strip() for item in thumbnail_suggestions if str(item).strip())
        else:
            suggestion_line = ""

        if not hashtags:
            hashtags = "#AI #FastAPI #Python #MachineLearning"

        linkedin_post_parts = [
            hook,
            "",
            story,
        ]
        if detail_line:
            linkedin_post_parts.extend(["", detail_line])
        if suggestion_line:
            linkedin_post_parts.extend(["", suggestion_line])
        linkedin_post_parts.extend(
            [
                "",
                "Tech stack: FastAPI | Python | JavaScript | NLP | AI Analytics",
                "",
                hashtags,
                "",
                f"LinkedIn: {linkedin_profile}",
                f"GitHub: {github_url}",
            ]
        )

        logger.info(
            "LinkedIn request validation requirements satisfied: platform=%s audience=%s title=%s caption_present=%s image_context_present=%s thumbnail_result=%s trends=%s",
            platform,
            audience,
            title or "(none)",
            bool(caption),
            bool(image_context),
            bool(thumbnail_result),
            len(payload.get("trends") or []),
        )

        return {
            "success": True,
            "linkedin_post": "\n".join(linkedin_post_parts).strip(),
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to generate LinkedIn post")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {exc}") from exc


@router.post("/creator-strategy")
async def creator_strategy(payload: dict = Body(...)):
    try:
        logger.info(
            "Creator strategy payload received with keys=%s",
            sorted(payload.keys()) if isinstance(payload, dict) else [],
        )
        result = creator_strategy_service.generate_strategy(payload or {})
        return result
    except Exception as exc:
        logger.exception("Failed to generate creator strategy")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {exc}") from exc


@router.post("/strategy")
async def strategy(payload: dict = Body(...)):
    return await creator_strategy(payload)


@router.post("/ai-chat")
async def ai_chat(payload: dict = Body(...)):
    try:
        logger.info("AI chat payload received with keys=%s", sorted(payload.keys()) if isinstance(payload, dict) else [])
        result = ai_chat_service.chat(payload or {})
        return result
    except Exception as exc:
        logger.exception("AI chat failed")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {exc}") from exc


def _build_pdf_response(request: Request, payload: LinkedInPostRequest) -> Response:
    try:
        context = _coerce_linkedin_context(payload)
        if not context.get("latest_analysis_result") and not context.get("analysis"):
            raise HTTPException(status_code=400, detail="Please analyze content first.")
        pdf_bytes = report_service.build_pdf(context)
        filename = "trendhunter_report.pdf"
        headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
        user_id = _current_user_id(request)
        if user_id is not None:
            try:
                save_report_record(
                    user_id=user_id,
                    filename=filename,
                    payload=context,
                )
            except Exception:
                logger.exception("Failed to save report record")
        return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to export PDF report")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {exc}") from exc


@router.post("/export-pdf-report")
def export_pdf_report(request: Request, payload: LinkedInPostRequest):
    return _build_pdf_response(request, payload)


@router.post("/export-pdf")
def export_pdf(request: Request, payload: LinkedInPostRequest):
    return _build_pdf_response(request, payload)


@router.post("/analyze-thumbnail")
async def analyze_thumbnail(file: UploadFile = File(...)):
    try:
        from io import BytesIO

        from PIL import Image, ImageFilter, ImageStat

        contents = await file.read()
        if not contents:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        with Image.open(BytesIO(contents)) as image:
            width, height = image.size
            grayscale = image.convert("L")
            stats = ImageStat.Stat(grayscale)
            brightness = round(float(stats.mean[0]), 2)
            contrast = round(float(stats.stddev[0]), 2)
            edge_map = grayscale.filter(ImageFilter.FIND_EDGES)
            edge_stats = ImageStat.Stat(edge_map)
            edge_strength = round(float(edge_stats.mean[0]), 2)

        file_size_kb = round(len(contents) / 1024, 2)
        issues: list[str] = []
        suggestions: list[str] = []
        score = 100.0
        text_visibility = 100.0

        if width < 800 or height < 800:
            issues.append("Resolution is below 800 x 800, which may look soft on feed previews.")
            suggestions.append("Upload a higher-resolution thumbnail, ideally 1080 x 1080 or larger.")
            score -= 20
        if brightness < 70:
            issues.append("The image is quite dark and may be hard to read.")
            suggestions.append("Increase exposure or use a brighter background.")
            score -= 12
        elif brightness > 190:
            issues.append("The image is very bright and may lose contrast in the feed.")
            suggestions.append("Reduce highlights or add darker text overlays.")
            score -= 12
        if contrast < 25:
            issues.append("Contrast is low, so the thumbnail may blend into the feed.")
            suggestions.append("Increase contrast or add a stronger focal point.")
            score -= 15
            text_visibility -= 20
        if edge_strength < 18:
            issues.append("The image has weak edge definition, so text may not stand out clearly.")
            suggestions.append("Use bolder typography or a higher-contrast text overlay.")
            score -= 10
            text_visibility -= 15
        if file_size_kb > 5000:
            issues.append("The file is quite large and may slow down upload/preview performance.")
            suggestions.append("Compress the image before uploading if possible.")
            score -= 8

        if not issues:
            suggestions.append("The thumbnail has solid basic image quality signals.")

        thumbnail_score = max(0.0, min(100.0, round(score, 2)))
        text_visibility_score = max(0.0, min(100.0, round(text_visibility, 2)))
        clickability_score = round((thumbnail_score * 0.4) + (text_visibility_score * 0.4) + (max(0.0, min(100.0, 100.0 - abs(brightness - 140.0) / 1.4)) * 0.2), 2)
        result = {
            "success": True,
            "file_name": file.filename,
            "file_size_kb": file_size_kb,
            "width": width,
            "height": height,
            "brightness": brightness,
            "contrast": contrast,
            "text_visibility": text_visibility_score,
            "edge_strength": edge_strength,
            "clickability_score": clickability_score,
            "thumbnail_score": thumbnail_score,
            "issues": issues,
            "suggestions": suggestions,
        }
        logger.info(
            "Thumbnail analyzed: filename=%s score=%s width=%s height=%s",
            file.filename,
            thumbnail_score,
            width,
            height,
        )
        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to analyze thumbnail")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {exc}") from exc


@router.post("/analyze-competitor")
def analyze_competitor(payload: CompetitorAnalysisRequest):
    try:
        result = insight_tools.analyze_competitor(payload.competitor, payload.topic, payload.platform, payload.region)
        return result
    except Exception as exc:
        logger.exception("Failed to analyze competitor")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {exc}") from exc


@router.post("/competitor-analysis")
def competitor_analysis(payload: CompetitorAnalysisRequest):
    return analyze_competitor(payload)


@router.post("/forecast")
async def forecast(payload: dict = Body(...)):
    title = str(payload.get("title") or payload.get("post_title") or payload.get("idea") or "").strip()
    description = str(payload.get("description") or payload.get("caption") or "").strip()
    region = str(payload.get("region") or payload.get("trend_region") or "Global").strip() or "Global"
    if not title:
        raise HTTPException(status_code=400, detail="title is required")
    result = forecast_service.forecast_trend_growth(title=title, description=description, region=region)
    return {"success": True, **result, "region": region}


@router.post("/analyze-creator-content")
async def analyze_creator_content(request: Request, payload: CreatorIntelligenceRequest):
    """Backwards-compatible creator analysis endpoint."""

    return await analyze_post(request, payload)


@router.get("/rag-analyze-trend")
async def rag_analyze_trend(title: str, description: str = "", region: str = "Global"):
    """Analyze a live trend with historical context retrieved from SQLite."""

    try:
        init_db()
        if not title or not title.strip():
            raise HTTPException(status_code=400, detail="title is required")

        result = rag_service.rag_analyze_trend(title=title, description=description, region=region)
        logger.info("RAG analysis completed for title=%s with %s similar trends", title, len(result.get("similar_trends", [])))
        await websocket_manager.broadcast_event("rag_update", result)
        return {
            "success": True,
            **result,
            "region": region,
        }
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail=f"Database error: {exc}") from exc
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Failed to run RAG trend analysis")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {exc}") from exc


@router.get("/workspace")
def get_workspace(request: Request, limit: int = 10):
    user_id = _current_user_id(request)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    try:
        return get_user_workspace(user_id=user_id, limit=max(1, min(limit, 25)))
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail=f"Database error: {exc}") from exc


@router.get("/analyze-trends")
async def analyze_trends(region: str = "Global"):
    """Analyze stored trends and persist sentiment/virality fields."""

    try:
        init_db()
        stored_trends = get_all_trends(region=region)
        unanalyzed_trends = [trend for trend in stored_trends if not trend.get("analysis")]
        analyzed: list[dict] = []

        if not unanalyzed_trends:
            return {
                "success": True,
                "count": 0,
                "items": [],
                "message": "No unanalyzed trends found.",
            }

        for trend in unanalyzed_trends:
            text = trend.get("title") or trend.get("name") or ""
            sentiment = sentiment_agent.analyze_text(text)
            virality_input = {**trend, **sentiment}
            virality = virality_agent.analyze_trend(virality_input)
            analysis = {
                **sentiment,
                **virality,
                "analyzed_at": datetime.now(timezone.utc),
            }
            updated = update_trend_analysis(trend["id"], analysis)
            if updated is not None:
                analyzed.append(updated)
                await websocket_manager.broadcast_event(
                    "virality_update",
                    {
                        "action": "analyzed",
                        "trend": updated,
                    },
                )

        return {
            "success": True,
            "count": len(analyzed),
            "items": analyzed,
            "region": region,
        }
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail=f"Database error: {exc}") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {exc}") from exc


@router.get("/generate-content-ideas")
async def generate_content_ideas():
    """Generate content ideas for analyzed trends missing a content idea."""

    try:
        init_db()
        trends = get_trends_without_content_ideas()
        generated: list[dict] = []

        if not trends:
            return {
                "success": True,
                "count": 0,
                "items": [],
                "message": "No analyzed trends need content ideas.",
            }

        for trend in trends:
            idea = content_agent.generate_content_idea(trend)
            saved = save_content_idea(trend["id"], {
                **idea,
                "generated_at": datetime.now(timezone.utc),
            })
            if saved is not None:
                saved["trend_title"] = trend.get("title")
                generated.append(saved)
                await websocket_manager.broadcast_event(
                    "activity",
                    {
                        "message": f"AI generated content ideas for {trend.get('title')}.",
                        "level": "success",
                    },
                )

        return {
            "success": True,
            "count": len(generated),
            "items": generated,
        }
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail=f"Database error: {exc}") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {exc}") from exc


@router.get("/trend/{trend_id}/content-idea")
def get_trend_content_idea(trend_id: int):
    idea = get_content_idea_by_trend_id(trend_id)
    if idea is None:
        raise HTTPException(status_code=404, detail="Content idea not found")
    return idea


@router.get("/generate-alerts")
async def generate_alerts(region: str = "Global"):
    """Generate alerts for high viral trends that have not been alerted yet."""

    try:
        init_db()
        trends = get_high_viral_trends_without_alerts()
        if region != "Global":
            trends = [trend for trend in trends if str(trend.get("region") or "Global") == region or not trend.get("region")]
        generated: list[dict] = []

        if not trends:
            return {
                "success": True,
                "count": 0,
                "items": [],
                "message": "No high viral trends need alerts.",
            }

        for trend in trends:
            payload = alert_agent.prepare_alert(trend)
            if payload is None:
                continue
            saved = create_alert(payload)
            if saved is not None:
                saved["trend"] = trend
                generated.append(saved)
                await websocket_manager.broadcast_event(
                    "alert_update",
                    {
                        "action": "created",
                        "alert": saved,
                    },
                )

        return {
            "success": True,
            "count": len(generated),
            "items": generated,
            "region": region,
        }
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail=f"Database error: {exc}") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {exc}") from exc


@router.get("/alerts")
def fetch_alerts():
    try:
        init_db()
        alerts = get_alerts()
        return {"success": True, "count": len(alerts), "items": alerts}
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail=f"Database error: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {exc}") from exc


@router.post("/alerts/{alert_id}/read")
def read_alert(alert_id: int):
    try:
        init_db()
        alert = mark_alert_as_read(alert_id)
        if alert is None:
            raise HTTPException(status_code=404, detail="Alert not found")
        return {"success": True, "item": alert}
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail=f"Database error: {exc}") from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {exc}") from exc
