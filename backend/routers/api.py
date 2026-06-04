"""API routes for trend data."""

from __future__ import annotations

from datetime import datetime, timezone
import logging

from fastapi import APIRouter, HTTPException
from sqlalchemy.exc import SQLAlchemyError

from backend.content_agent import ContentAgent
from backend.alert_agent import AlertAgent
from backend.database import (
    create_alert,
    get_alerts,
    get_content_idea_by_trend_id,
    get_all_trends,
    get_high_viral_trends_without_alerts,
    get_trend_by_id,
    get_unanalyzed_trends,
    get_trends_without_content_ideas,
    init_db,
    save_google_trends,
    save_content_idea,
    save_trends,
    update_trend_forecast,
    update_trend_analysis,
    mark_alert_as_read,
)
from backend.services.gemini_service import GeminiService
from backend.services.forecast_service import ForecastService
from backend.services.rag_service import RAGService
from backend.services.news_service import NewsService
from backend.services.youtube_service import YouTubeService
from backend.reddit_agent import RedditAgent
from backend.sentiment_agent import SentimentAgent
from backend.trend_fetcher import TrendFetcher
from backend.virality_agent import ViralityAgent
from backend.websocket_manager import websocket_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["api"])
trend_fetcher = TrendFetcher()
sentiment_agent = SentimentAgent()
virality_agent = ViralityAgent()
content_agent = ContentAgent()
reddit_agent = RedditAgent()
alert_agent = AlertAgent()
news_service = NewsService()
youtube_service = YouTubeService()
gemini_service = GeminiService()
rag_service = RAGService()
forecast_service = ForecastService()


@router.get("/trends")
def get_trends():
    trends = get_all_trends()
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
    return {"items": trends_with_flags, "count": len(trends_with_flags)}


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
async def fetch_live_trends(keyword: str | None = None, region_code: str = "US"):
    """Fetch news and YouTube live trends in one request."""

    try:
        init_db()
        news_trends = news_service.search_news(keyword) if keyword else news_service.fetch_latest_trending_news()
        youtube_trends = youtube_service.fetch_trending_videos(region_code=region_code)
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
        }
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail=f"Database error: {exc}") from exc
    except Exception as exc:
        logger.exception("Failed to fetch live trends")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {exc}") from exc


@router.get("/forecast-trend")
async def forecast_trend(title: str, description: str = ""):
    """Forecast a single trend using historical context and Gemini."""

    try:
        init_db()
        if not title or not title.strip():
            raise HTTPException(status_code=400, detail="title is required")

        result = forecast_service.forecast_trend_growth(title=title, description=description)
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
        return {"success": True, **result, "saved": updated is not None}
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
async def forecast_live_trends():
    """Forecast all stored trends and persist the prediction fields."""

    try:
        init_db()
        trends = get_all_trends()
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
            result = forecast_service.forecast_trend_growth(title=title, description=description, trend=trend)
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
async def fetch_reddit_trends():
    """Fetch Reddit trends and persist them to SQLite."""

    try:
        init_db()
        trends = reddit_agent.fetch_trends()
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
        }
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail=f"Database error: {exc}") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {exc}") from exc


@router.get("/fetch-google-trends")
async def fetch_google_trends():
    """Fetch Google Trends data and persist it to SQLite."""

    try:
        init_db()
        trends = trend_fetcher.fetch_google_trends()
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
        }
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail=f"Database error: {exc}") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {exc}") from exc


@router.get("/fetch-news-trends")
async def fetch_news_trends(keyword: str | None = None):
    """Fetch latest news trends or search by keyword and persist them."""

    try:
        init_db()
        trends = news_service.search_news(keyword) if keyword else news_service.fetch_latest_trending_news()
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
        }
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail=f"Database error: {exc}") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Failed to fetch news trends")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {exc}") from exc


@router.get("/fetch-youtube-trends")
async def fetch_youtube_trends(region_code: str = "US"):
    """Fetch trending YouTube videos and persist them."""

    try:
        init_db()
        trends = youtube_service.fetch_trending_videos(region_code=region_code)
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
        }
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail=f"Database error: {exc}") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Failed to fetch YouTube trends")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {exc}") from exc


@router.get("/analyze-trend")
async def analyze_trend(title: str, description: str = ""):
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
        return {"success": True, "item": payload}
    except Exception as exc:
        logger.exception("Failed to analyze trend with Gemini")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {exc}") from exc


@router.get("/rag-analyze-trend")
async def rag_analyze_trend(title: str, description: str = ""):
    """Analyze a live trend with historical context retrieved from SQLite."""

    try:
        init_db()
        if not title or not title.strip():
            raise HTTPException(status_code=400, detail="title is required")

        result = rag_service.rag_analyze_trend(title=title, description=description)
        logger.info("RAG analysis completed for title=%s with %s similar trends", title, len(result.get("similar_trends", [])))
        await websocket_manager.broadcast_event("rag_update", result)
        return {
            "success": True,
            **result,
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


@router.get("/analyze-trends")
async def analyze_trends():
    """Analyze stored trends and persist sentiment/virality fields."""

    try:
        init_db()
        unanalyzed_trends = get_unanalyzed_trends()
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
async def generate_alerts():
    """Generate alerts for high viral trends that have not been alerted yet."""

    try:
        init_db()
        trends = get_high_viral_trends_without_alerts()
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
