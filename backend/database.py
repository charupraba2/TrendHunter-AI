"""SQLite database setup and ORM models."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Iterable

from sqlalchemy import Boolean, JSON, Column, DateTime, Float, Integer, String, create_engine, inspect, text
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from backend.config import settings

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class TrendRecord(Base):
    __tablename__ = "trend_records"

    id = Column(Integer, primary_key=True, index=True)
    trend_name = Column(String, nullable=False, index=True)
    source = Column(String, nullable=False, default="mixed")
    category = Column(String, nullable=False, default="general")
    virality_score = Column(Float, nullable=False, default=0.0)
    sentiment_score = Column(Float, nullable=False, default=0.0)
    payload = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class Trend(Base):
    __tablename__ = "trends"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False, index=True)
    platform = Column(String, nullable=False, default="reddit")
    region = Column(String, nullable=True, index=True)
    source_label = Column(String, nullable=True)
    source_uid = Column(String, nullable=True, index=True)
    subreddit = Column(String, nullable=False, index=True)
    url = Column(String, nullable=False)
    description = Column(String, nullable=True)
    channel_name = Column(String, nullable=True)
    view_count = Column(Integer, nullable=True)
    thumbnail = Column(String, nullable=True)
    upvotes = Column(Integer, nullable=False, default=0)
    comments = Column(Integer, nullable=False, default=0)
    trend_score = Column(Float, nullable=True)
    source_type = Column(String, nullable=True)
    positive_score = Column(Float, nullable=True)
    negative_score = Column(Float, nullable=True)
    neutral_score = Column(Float, nullable=True)
    compound_score = Column(Float, nullable=True)
    sentiment_label = Column(String, nullable=True)
    virality_score = Column(Float, nullable=True)
    virality_label = Column(String, nullable=True)
    virality_probability = Column(Float, nullable=True)
    forecast_confidence = Column(Float, nullable=True)
    prediction_label = Column(String, nullable=True)
    opportunity_score = Column(Float, nullable=True)
    risk_score = Column(Float, nullable=True)
    forecast_updated_at = Column(DateTime, nullable=True)
    analyzed_at = Column(DateTime, nullable=True)
    published_at = Column(DateTime, nullable=True)
    ai_summary = Column(String, nullable=True)
    why_trending = Column(String, nullable=True)
    audience_interest = Column(String, nullable=True)
    future_prediction = Column(String, nullable=True)
    analysis_payload = Column(JSON, nullable=True)
    created_utc = Column(DateTime, nullable=False)
    fetched_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class ContentIdea(Base):
    __tablename__ = "content_ideas"

    id = Column(Integer, primary_key=True, index=True)
    trend_id = Column(Integer, nullable=False, index=True)
    hook = Column(String, nullable=False)
    reel_idea = Column(String, nullable=False)
    youtube_shorts_idea = Column(String, nullable=False)
    caption = Column(String, nullable=False)
    hashtags = Column(JSON, nullable=False, default=list)
    content_angle = Column(String, nullable=False)
    generated_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    trend_id = Column(Integer, nullable=False, index=True)
    title = Column(String, nullable=False)
    platform = Column(String, nullable=False, default="reddit")
    virality_score = Column(Float, nullable=False, default=0.0)
    virality_label = Column(String, nullable=False, default="Low Reach")
    message = Column(String, nullable=False)
    is_read = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class PostPerformanceRecord(Base):
    __tablename__ = "post_performance_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    post_url = Column(String, nullable=False, index=True)
    platform = Column(String, nullable=False, default="instagram")
    region = Column(String, nullable=False, default="India")
    source_label = Column(String, nullable=True)
    content_title = Column(String, nullable=True)
    likes = Column(Integer, nullable=False, default=0)
    comments = Column(Integer, nullable=False, default=0)
    shares = Column(Integer, nullable=False, default=0)
    reach = Column(Integer, nullable=False, default=0)
    impressions = Column(Integer, nullable=False, default=0)
    engagement_growth = Column(Float, nullable=False, default=0.0)
    virality_momentum = Column(Float, nullable=False, default=0.0)
    growth_speed = Column(Float, nullable=False, default=0.0)
    trend_strength = Column(Float, nullable=False, default=0.0)
    engagement_velocity = Column(Float, nullable=False, default=0.0)
    trend_relevance = Column(Float, nullable=False, default=0.0)
    lifecycle_stage = Column(String, nullable=False, default="Stable")
    should_repost = Column(Boolean, nullable=False, default=False)
    should_improve_hook = Column(Boolean, nullable=False, default=False)
    should_shorten_caption = Column(Boolean, nullable=False, default=False)
    should_follow_up = Column(Boolean, nullable=False, default=False)
    is_saturated = Column(Boolean, nullable=False, default=False)
    expected_reach = Column(Integer, nullable=False, default=0)
    expected_impressions = Column(Integer, nullable=False, default=0)
    peak_engagement_time = Column(String, nullable=True)
    engagement_decay = Column(Float, nullable=False, default=0.0)
    live_metrics_available = Column(Boolean, nullable=False, default=False)
    payload = Column(JSON, nullable=False, default=dict)
    recommendations = Column(JSON, nullable=False, default=dict)
    forecast = Column(JSON, nullable=False, default=dict)
    chart_data = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_tracked_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, nullable=False, unique=True, index=True)
    email = Column(String, nullable=False, unique=True, index=True)
    password_hash = Column(String, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class UserSession(Base):
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    jti = Column(String, nullable=False, unique=True, index=True)
    token_hash = Column(String, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    revoked_at = Column(DateTime, nullable=True)


class AnalysisRecord(Base):
    __tablename__ = "analysis_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    trend_title = Column(String, nullable=False, index=True)
    platform = Column(String, nullable=False, default="linkedin")
    trend_match_score = Column(Float, nullable=True)
    virality_score = Column(Float, nullable=True)
    payload = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class LinkedInPostRecord(Base):
    __tablename__ = "linkedin_posts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    analysis_id = Column(Integer, nullable=True, index=True)
    title = Column(String, nullable=False, default="")
    post_text = Column(String, nullable=False)
    payload = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class ReportRecord(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    analysis_id = Column(Integer, nullable=True, index=True)
    filename = Column(String, nullable=False)
    payload = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    _ensure_trends_columns()
    _ensure_content_ideas_columns()
    _ensure_alerts_columns()
    _ensure_post_performance_columns()
    _ensure_users_columns()
    _ensure_user_sessions_columns()
    _ensure_workspace_columns()


def _ensure_trends_columns() -> None:
    inspector = inspect(engine)
    if "trends" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("trends")}
    required_columns = {
        "trend_score": "FLOAT",
        "region": "VARCHAR",
        "source_type": "VARCHAR",
        "source_label": "VARCHAR",
        "source_uid": "VARCHAR",
        "description": "VARCHAR",
        "channel_name": "VARCHAR",
        "view_count": "INTEGER",
        "thumbnail": "VARCHAR",
        "positive_score": "FLOAT",
        "negative_score": "FLOAT",
        "neutral_score": "FLOAT",
        "compound_score": "FLOAT",
        "sentiment_label": "VARCHAR",
        "virality_score": "FLOAT",
        "virality_label": "VARCHAR",
        "virality_probability": "FLOAT",
        "forecast_confidence": "FLOAT",
        "prediction_label": "VARCHAR",
        "opportunity_score": "FLOAT",
        "risk_score": "FLOAT",
        "forecast_updated_at": "DATETIME",
        "analyzed_at": "DATETIME",
        "published_at": "DATETIME",
        "ai_summary": "VARCHAR",
        "why_trending": "VARCHAR",
        "audience_interest": "VARCHAR",
        "future_prediction": "VARCHAR",
        "analysis_payload": "JSON",
    }

    with engine.begin() as connection:
        for column_name, column_type in required_columns.items():
            if column_name not in existing_columns:
                connection.execute(text(f"ALTER TABLE trends ADD COLUMN {column_name} {column_type}"))


def _ensure_content_ideas_columns() -> None:
    inspector = inspect(engine)
    if "content_ideas" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("content_ideas")}
    required_columns = {
        "trend_id": "INTEGER",
        "hook": "VARCHAR",
        "reel_idea": "VARCHAR",
        "youtube_shorts_idea": "VARCHAR",
        "caption": "VARCHAR",
        "hashtags": "JSON",
        "content_angle": "VARCHAR",
        "generated_at": "DATETIME",
    }

    with engine.begin() as connection:
        for column_name, column_type in required_columns.items():
            if column_name not in existing_columns:
                connection.execute(text(f"ALTER TABLE content_ideas ADD COLUMN {column_name} {column_type}"))


def _ensure_alerts_columns() -> None:
    inspector = inspect(engine)
    if "alerts" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("alerts")}
    required_columns = {
        "trend_id": "INTEGER",
        "title": "VARCHAR",
        "platform": "VARCHAR",
        "virality_score": "FLOAT",
        "virality_label": "VARCHAR",
        "message": "VARCHAR",
        "is_read": "INTEGER",
        "created_at": "DATETIME",
    }

    with engine.begin() as connection:
        for column_name, column_type in required_columns.items():
            if column_name not in existing_columns:
                connection.execute(text(f"ALTER TABLE alerts ADD COLUMN {column_name} {column_type}"))


def _ensure_post_performance_columns() -> None:
    inspector = inspect(engine)
    if "post_performance_records" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("post_performance_records")}
    required_columns = {
        "user_id": "INTEGER",
        "post_url": "VARCHAR",
        "platform": "VARCHAR",
        "region": "VARCHAR",
        "source_label": "VARCHAR",
        "content_title": "VARCHAR",
        "likes": "INTEGER",
        "comments": "INTEGER",
        "shares": "INTEGER",
        "reach": "INTEGER",
        "impressions": "INTEGER",
        "engagement_growth": "FLOAT",
        "virality_momentum": "FLOAT",
        "growth_speed": "FLOAT",
        "trend_strength": "FLOAT",
        "engagement_velocity": "FLOAT",
        "trend_relevance": "FLOAT",
        "lifecycle_stage": "VARCHAR",
        "should_repost": "BOOLEAN",
        "should_improve_hook": "BOOLEAN",
        "should_shorten_caption": "BOOLEAN",
        "should_follow_up": "BOOLEAN",
        "is_saturated": "BOOLEAN",
        "expected_reach": "INTEGER",
        "expected_impressions": "INTEGER",
        "peak_engagement_time": "VARCHAR",
        "engagement_decay": "FLOAT",
        "live_metrics_available": "BOOLEAN",
        "payload": "JSON",
        "recommendations": "JSON",
        "forecast": "JSON",
        "chart_data": "JSON",
        "created_at": "DATETIME",
        "updated_at": "DATETIME",
        "last_tracked_at": "DATETIME",
    }

    with engine.begin() as connection:
        for column_name, column_type in required_columns.items():
            if column_name not in existing_columns:
                connection.execute(text(f"ALTER TABLE post_performance_records ADD COLUMN {column_name} {column_type}"))


def _ensure_users_columns() -> None:
    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("users")}
    required_columns = {
        "username": "VARCHAR",
        "email": "VARCHAR",
        "password_hash": "VARCHAR",
        "is_active": "BOOLEAN",
        "created_at": "DATETIME",
        "updated_at": "DATETIME",
    }

    with engine.begin() as connection:
        for column_name, column_type in required_columns.items():
            if column_name not in existing_columns:
                connection.execute(text(f"ALTER TABLE users ADD COLUMN {column_name} {column_type}"))


def _ensure_user_sessions_columns() -> None:
    inspector = inspect(engine)
    if "user_sessions" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("user_sessions")}
    required_columns = {
        "user_id": "INTEGER",
        "jti": "VARCHAR",
        "token_hash": "VARCHAR",
        "expires_at": "DATETIME",
        "created_at": "DATETIME",
        "revoked_at": "DATETIME",
    }

    with engine.begin() as connection:
        for column_name, column_type in required_columns.items():
            if column_name not in existing_columns:
                connection.execute(text(f"ALTER TABLE user_sessions ADD COLUMN {column_name} {column_type}"))


def _ensure_workspace_columns() -> None:
    inspector = inspect(engine)
    workspace_tables = {
        "analysis_records": {
            "user_id": "INTEGER",
            "trend_title": "VARCHAR",
            "platform": "VARCHAR",
            "trend_match_score": "FLOAT",
            "virality_score": "FLOAT",
            "payload": "JSON",
            "created_at": "DATETIME",
        },
        "linkedin_posts": {
            "user_id": "INTEGER",
            "analysis_id": "INTEGER",
            "title": "VARCHAR",
            "post_text": "VARCHAR",
            "payload": "JSON",
            "created_at": "DATETIME",
        },
        "reports": {
            "user_id": "INTEGER",
            "analysis_id": "INTEGER",
            "filename": "VARCHAR",
            "payload": "JSON",
            "created_at": "DATETIME",
        },
    }

    existing_tables = set(inspector.get_table_names())
    with engine.begin() as connection:
        for table_name, columns in workspace_tables.items():
            if table_name not in existing_tables:
                continue
            existing_columns = {column["name"] for column in inspector.get_columns(table_name)}
            for column_name, column_type in columns.items():
                if column_name not in existing_columns:
                    connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"))


def get_db_session() -> Session:
    return SessionLocal()


def save_trends(trends: Iterable[dict]) -> int:
    """Save trend dictionaries into SQLite and return inserted row count."""

    inserted = 0
    session = get_db_session()
    try:
        for trend in trends:
            created_utc = trend.get("created_utc")
            if isinstance(created_utc, (int, float)):
                created_utc = datetime.utcfromtimestamp(created_utc)
            elif not isinstance(created_utc, datetime):
                created_utc = datetime.utcnow()

            region_value = _normalize_region_value(
                trend.get("region")
                or trend.get("selected_region")
                or trend.get("region_label")
                or trend.get("region_code")
                or trend.get("trend_region")
                or "Global"
            )
            source_uid = _build_source_uid(trend)
            if source_uid and session.query(Trend.id).filter(Trend.source_uid == source_uid).first():
                continue

            if not source_uid:
                duplicate_query = session.query(Trend.id).filter(
                    Trend.title == str(trend.get("title", "")).strip(),
                    Trend.platform == str(trend.get("platform", "reddit")).strip() or "reddit",
                    Trend.url == str(trend.get("url", "")).strip(),
                )
                if session.query(duplicate_query.exists()).scalar():
                    continue

            row = Trend(
                title=str(trend.get("title", "")).strip(),
                platform=str(trend.get("platform", "reddit")).strip() or "reddit",
                region=region_value,
                source_label=str(trend.get("source_label", "")).strip() or None,
                source_uid=source_uid,
                subreddit=str(trend.get("subreddit", "unknown")).strip() or "unknown",
                url=str(trend.get("url", "")).strip(),
                description=str(trend.get("description", "")).strip() or None,
                channel_name=str(trend.get("channel_name", "")).strip() or None,
                view_count=_to_int(trend.get("view_count")),
                thumbnail=str(trend.get("thumbnail", "")).strip() or None,
                upvotes=int(trend.get("upvotes", 0) or 0),
                comments=int(trend.get("comments", 0) or 0),
                trend_score=_to_float(trend.get("trend_score")),
                source_type=str(
                    trend.get("source_type")
                    or trend.get("sort")
                    or trend.get("source")
                    or ""
                ).strip()
                or None,
                positive_score=_to_float(trend.get("positive_score")),
                negative_score=_to_float(trend.get("negative_score")),
                neutral_score=_to_float(trend.get("neutral_score")),
                compound_score=_to_float(trend.get("compound_score")),
                sentiment_label=str(trend.get("sentiment_label", "")).strip() or None,
                virality_score=_to_float(trend.get("virality_score")),
                virality_label=_normalize_virality_label(trend.get("virality_score"), trend.get("virality_label")),
                virality_probability=_to_float(trend.get("virality_probability")),
                forecast_confidence=_to_float(trend.get("forecast_confidence")),
                prediction_label=str(trend.get("prediction_label", "")).strip() or None,
                opportunity_score=_to_float(trend.get("opportunity_score")),
                risk_score=_to_float(trend.get("risk_score")),
                forecast_updated_at=_to_datetime(trend.get("forecast_updated_at")),
                analyzed_at=_to_datetime(trend.get("analyzed_at")),
                published_at=_to_datetime(trend.get("published_at")),
                ai_summary=str(trend.get("ai_summary", "")).strip() or None,
                why_trending=str(trend.get("why_trending", "")).strip() or None,
                audience_interest=str(trend.get("audience_interest", "")).strip() or None,
                future_prediction=str(trend.get("future_prediction", "")).strip() or None,
                analysis_payload=trend.get("analysis_payload"),
                created_utc=created_utc,
                fetched_at=datetime.utcnow(),
            )
            session.add(row)
            inserted += 1

        session.commit()
        return inserted
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def save_google_trends(trends: Iterable[dict]) -> int:
    """Save Google Trends rows using the shared trends table."""

    normalized = []
    for trend in trends:
        item = dict(trend)
        item.setdefault("platform", "google_trends")
        item.setdefault("subreddit", "n/a")
        item.setdefault("upvotes", 0)
        item.setdefault("comments", 0)
        item.setdefault("source_type", "google_trending_searches")
        if item.get("trend_score") is None and item.get("search_interest") is not None:
            item["trend_score"] = item.get("search_interest")
        normalized.append(item)
    return save_trends(normalized)


def get_all_trends(limit: int = 100, region: str | None = None) -> list[dict]:
    session = get_db_session()
    try:
        query = session.query(Trend)
        region_value = _normalize_region_value(region)
        if region_value and region_value.lower() != "global":
            query = query.filter((Trend.region == region_value) | (Trend.region.is_(None)))
        rows = query.order_by(Trend.fetched_at.desc(), Trend.id.desc()).limit(limit).all()
        return [_trend_to_dict(row) for row in rows]
    finally:
        session.close()


def get_trend_by_id(trend_id: int) -> dict | None:
    session = get_db_session()
    try:
        row = session.query(Trend).filter(Trend.id == trend_id).first()
        return _trend_to_dict(row) if row else None
    finally:
        session.close()


def _trend_to_dict(row: Trend | None) -> dict | None:
    if row is None:
        return None

    category = row.subreddit if row.platform == "reddit" else (row.source_type or row.platform)
    if row.platform == "reddit":
        summary = f"Reddit trend from r/{row.subreddit} with {row.upvotes} upvotes and {row.comments} comments."
    elif row.platform == "google_trends":
        summary = f"Google Trends keyword '{row.title}' with trend score {row.trend_score or 0}."
    elif row.platform == "news":
        summary = f"News trend '{row.title}' from {row.source_label or 'NEWS'}."
    elif row.platform == "youtube":
        summary = f"YouTube trend '{row.title}' from {row.channel_name or 'YouTube'} with {row.view_count or 0} views."
    else:
        summary = f"Trend '{row.title}' from {row.platform or 'mixed'}."

    return {
        "id": row.id,
        "title": row.title,
        "name": row.title,
        "platform": row.platform,
        "region": row.region or "Global",
        "source": row.platform,
        "source_label": row.source_label or row.platform.upper(),
        "source_uid": row.source_uid,
        "subreddit": row.subreddit,
        "description": row.description,
        "channel_name": row.channel_name,
        "view_count": row.view_count,
        "thumbnail": row.thumbnail,
        "category": category,
        "url": row.url,
        "upvotes": row.upvotes,
        "comments": row.comments,
        "trend_score": row.trend_score,
        "source_type": row.source_type,
        "published_at": row.published_at.isoformat() if row.published_at else None,
        "positive_score": row.positive_score,
        "negative_score": row.negative_score,
        "neutral_score": row.neutral_score,
        "compound_score": row.compound_score,
        "sentiment_label": row.sentiment_label,
        "virality_score": row.virality_score,
        "virality_label": row.virality_label,
        "virality_probability": row.virality_probability,
        "forecast_confidence": row.forecast_confidence,
        "prediction_label": row.prediction_label,
        "opportunity_score": row.opportunity_score,
        "risk_score": row.risk_score,
        "forecast_updated_at": row.forecast_updated_at.isoformat() if row.forecast_updated_at else None,
        "analyzed_at": row.analyzed_at.isoformat() if row.analyzed_at else None,
        "created_utc": row.created_utc.isoformat() if row.created_utc else None,
        "fetched_at": row.fetched_at.isoformat() if row.fetched_at else None,
        "ai_summary": row.ai_summary,
        "why_trending": row.why_trending,
        "audience_interest": row.audience_interest,
        "future_prediction": row.future_prediction,
        "analysis_payload": row.analysis_payload,
        "summary": summary,
    }


def _to_int(value) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _to_float(value) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_datetime(value) -> datetime | None:
    if value is None or value == "":
        return None


def _normalize_region_value(value) -> str:
    if value is None:
        return "Global"
    text = str(value).strip()
    if not text:
        return "Global"
    lowered = text.lower()
    aliases = {
        "in": "India",
        "india": "India",
        "tamil nadu": "Tamil Nadu",
        "tamilnadu": "Tamil Nadu",
        "tn": "Tamil Nadu",
        "chennai": "Chennai",
        "trichy": "Trichy",
        "tiruchirappalli": "Trichy",
        "global": "Global",
        "world": "Global",
        "us": "Global",
        "usa": "Global",
    }
    return aliases.get(lowered, text)
    if isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)):
        return datetime.utcfromtimestamp(value)


def _normalize_virality_label(score, label=None) -> str:
    text = str(label or "").strip()
    if text:
        lowered = text.lower()
        aliases = {
            "high viral": "High Viral",
            "trending": "Trending",
            "average": "Average",
            "low reach": "Low Reach",
            "medium viral": "Average",
            "low viral": "Low Reach",
        }
        if lowered in aliases:
            return aliases[lowered]
        return text

    try:
        value = float(score or 0)
    except (TypeError, ValueError):
        value = 0.0

    if value >= 85:
        return "High Viral"
    if value >= 65:
        return "Trending"
    if value >= 45:
        return "Average"
    return "Low Reach"
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
    return None


def _build_source_uid(trend: dict) -> str | None:
    source_uid = str(trend.get("source_uid", "")).strip()
    if source_uid:
        return source_uid

    platform = str(trend.get("platform", "")).strip().lower()
    url = str(trend.get("url", "")).strip()
    title = str(trend.get("title") or trend.get("name") or "").strip().lower()

    if platform == "reddit":
        subreddit = str(trend.get("subreddit", "")).strip().lower()
        source_type = str(trend.get("source_type") or trend.get("sort") or "").strip().lower()
        upvotes = _to_int(trend.get("upvotes")) or 0
        comments = _to_int(trend.get("comments")) or 0
        if url:
            return f"reddit:{source_type}:{subreddit}:{url}"
        if title:
            return f"reddit:{source_type}:{subreddit}:{title}:{upvotes}:{comments}"

    if platform == "google_trends":
        source_type = str(trend.get("source_type", "google_trending_searches")).strip().lower()
        if title:
            return f"google:{source_type}:{title}"
        if url:
            return f"google:{source_type}:{url}"

    if platform == "news" or platform == "newsapi":
        source_type = str(trend.get("source_type", "newsapi")).strip().lower()
        if url:
            return f"news:{source_type}:{url}"
        if title:
            return f"news:{source_type}:{title}"

    if platform == "youtube":
        source_type = str(trend.get("source_type", "youtube_api")).strip().lower()
        if url:
            return f"youtube:{source_type}:{url}"
        if title:
            return f"youtube:{source_type}:{title}"

    if url:
        return f"{platform or 'mixed'}:{url}"
    if title:
        return f"{platform or 'mixed'}:{title}"
    return None


def get_unanalyzed_trends(limit: int = 100) -> list[dict]:
    session = get_db_session()
    try:
        rows = (
            session.query(Trend)
            .filter(Trend.analyzed_at.is_(None))
            .order_by(Trend.fetched_at.asc(), Trend.id.asc())
            .limit(limit)
            .all()
        )
        return [_trend_to_dict(row) for row in rows]
    finally:
        session.close()


def update_trend_analysis(trend_id: int, analysis: dict) -> dict | None:
    session = get_db_session()
    try:
        row = session.query(Trend).filter(Trend.id == trend_id).first()
        if row is None:
            return None

        row.positive_score = _to_float(analysis.get("positive_score"))
        row.negative_score = _to_float(analysis.get("negative_score"))
        row.neutral_score = _to_float(analysis.get("neutral_score"))
        row.compound_score = _to_float(analysis.get("compound_score"))
        row.sentiment_label = str(analysis.get("sentiment_label", "")).strip() or None
        row.virality_score = _to_float(analysis.get("virality_score"))
        row.virality_label = _normalize_virality_label(analysis.get("virality_score"), analysis.get("virality_label"))
        row.analyzed_at = _to_datetime(analysis.get("analyzed_at")) or datetime.utcnow()
        session.commit()
        session.refresh(row)
        return _trend_to_dict(row)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def update_trend_forecast(trend_id: int, forecast: dict) -> dict | None:
    session = get_db_session()
    try:
        row = session.query(Trend).filter(Trend.id == trend_id).first()
        if row is None:
            return None

        row.virality_probability = _to_float(forecast.get("virality_probability"))
        row.forecast_confidence = _to_float(forecast.get("forecast_confidence"))
        row.prediction_label = str(forecast.get("prediction_label", "")).strip() or None
        row.opportunity_score = _to_float(forecast.get("opportunity_score"))
        row.risk_score = _to_float(forecast.get("risk_score"))
        row.forecast_updated_at = _to_datetime(forecast.get("forecast_updated_at")) or datetime.utcnow()

        if forecast.get("virality_score") is not None:
            row.virality_score = _to_float(forecast.get("virality_score"))
        if forecast.get("virality_label"):
            row.virality_label = _normalize_virality_label(forecast.get("virality_score"), forecast.get("virality_label"))

        row.analysis_payload = forecast.get("analysis_payload", row.analysis_payload)
        session.commit()
        session.refresh(row)
        return _trend_to_dict(row)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def save_content_idea(trend_id: int, content_idea: dict) -> dict:
    session = get_db_session()
    try:
        row = session.query(ContentIdea).filter(ContentIdea.trend_id == trend_id).first()
        if row is None:
            row = ContentIdea(trend_id=trend_id)
            session.add(row)

        row.hook = str(content_idea.get("hook", "")).strip()
        row.reel_idea = str(content_idea.get("reel_idea", "")).strip()
        row.youtube_shorts_idea = str(content_idea.get("youtube_shorts_idea", "")).strip()
        row.caption = str(content_idea.get("caption", "")).strip()
        row.hashtags = content_idea.get("hashtags", [])
        row.content_angle = str(content_idea.get("content_angle", "")).strip()
        row.generated_at = _to_datetime(content_idea.get("generated_at")) or datetime.utcnow()
        session.commit()
        session.refresh(row)
        return _content_idea_to_dict(row)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_content_idea_by_trend_id(trend_id: int) -> dict | None:
    session = get_db_session()
    try:
        row = session.query(ContentIdea).filter(ContentIdea.trend_id == trend_id).first()
        return _content_idea_to_dict(row) if row else None
    finally:
        session.close()


def get_trends_without_content_ideas(limit: int = 100) -> list[dict]:
    session = get_db_session()
    try:
        subquery = session.query(ContentIdea.trend_id)
        rows = (
            session.query(Trend)
            .filter(Trend.analyzed_at.isnot(None))
            .filter(~Trend.id.in_(subquery))
            .order_by(Trend.analyzed_at.asc(), Trend.id.asc())
            .limit(limit)
            .all()
        )
        return [_trend_to_dict(row) for row in rows]
    finally:
        session.close()


def _content_idea_to_dict(row: ContentIdea | None) -> dict | None:
    if row is None:
        return None

    return {
        "id": row.id,
        "trend_id": row.trend_id,
        "hook": row.hook,
        "reel_idea": row.reel_idea,
        "youtube_shorts_idea": row.youtube_shorts_idea,
        "caption": row.caption,
        "hashtags": row.hashtags or [],
        "content_angle": row.content_angle,
        "generated_at": row.generated_at.isoformat() if row.generated_at else None,
    }


def create_alert(trend: dict) -> dict:
    session = get_db_session()
    try:
        trend_id = trend.get("trend_id", trend.get("id"))
        if trend_id is None:
            raise ValueError("Alert trend_id is required.")

        row = Alert(
            trend_id=int(trend_id),
            title=str(trend.get("title") or trend.get("name") or "Untitled trend").strip(),
            platform=str(trend.get("platform", "reddit")).strip() or "reddit",
            virality_score=_to_float(trend.get("virality_score")) or 0.0,
            virality_label=_normalize_virality_label(trend.get("virality_score"), trend.get("virality_label")),
            message=str(trend.get("message", "")).strip(),
            is_read=0,
            created_at=_to_datetime(trend.get("created_at")) or datetime.utcnow(),
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return _alert_to_dict(row)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_alerts(limit: int = 100) -> list[dict]:
    session = get_db_session()
    try:
        rows = (
            session.query(Alert)
            .order_by(Alert.created_at.desc(), Alert.id.desc())
            .limit(limit)
            .all()
        )
        return [_alert_to_dict(row) for row in rows]
    finally:
        session.close()


def mark_alert_as_read(alert_id: int) -> dict | None:
    session = get_db_session()
    try:
        row = session.query(Alert).filter(Alert.id == alert_id).first()
        if row is None:
            return None
        row.is_read = 1
        session.commit()
        session.refresh(row)
        return _alert_to_dict(row)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_high_viral_trends_without_alerts(limit: int = 100) -> list[dict]:
    session = get_db_session()
    try:
        alert_trend_ids = session.query(Alert.trend_id)
        rows = (
            session.query(Trend)
            .filter(Trend.virality_score.isnot(None))
            .filter(Trend.virality_score >= 85)
            .filter(Trend.virality_label == "High Viral")
            .filter(~Trend.id.in_(alert_trend_ids))
            .order_by(Trend.virality_score.desc(), Trend.fetched_at.desc())
            .limit(limit)
            .all()
        )
        return [_trend_to_dict(row) for row in rows]
    finally:
        session.close()


def _alert_to_dict(row: Alert | None) -> dict | None:
    if row is None:
        return None

    return {
        "id": row.id,
        "trend_id": row.trend_id,
        "title": row.title,
        "platform": row.platform,
        "virality_score": row.virality_score,
        "virality_label": row.virality_label,
        "message": row.message,
        "is_read": bool(row.is_read),
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def create_user(username: str, email: str, password_hash: str) -> dict:
    session = get_db_session()
    try:
        row = User(
            username=username.strip(),
            email=email.strip().lower(),
            password_hash=password_hash,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return _user_to_dict(row)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_user_by_id(user_id: int) -> dict | None:
    session = get_db_session()
    try:
        row = session.query(User).filter(User.id == user_id).first()
        return _user_to_dict(row) if row else None
    finally:
        session.close()


def get_user_by_username(username: str) -> dict | None:
    session = get_db_session()
    try:
        row = session.query(User).filter(User.username == username.strip()).first()
        return _user_to_dict(row) if row else None
    finally:
        session.close()


def get_user_by_email(email: str) -> dict | None:
    session = get_db_session()
    try:
        row = session.query(User).filter(User.email == email.strip().lower()).first()
        return _user_to_dict(row) if row else None
    finally:
        session.close()


def create_user_session(user_id: int, jti: str, token_hash: str, expires_at: datetime) -> dict:
    session = get_db_session()
    try:
        row = UserSession(
            user_id=user_id,
            jti=jti,
            token_hash=token_hash,
            expires_at=expires_at,
            created_at=datetime.utcnow(),
            revoked_at=None,
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return _user_session_to_dict(row)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_user_session_by_jti(jti: str) -> dict | None:
    session = get_db_session()
    try:
        row = session.query(UserSession).filter(UserSession.jti == jti).first()
        return _user_session_to_dict(row) if row else None
    finally:
        session.close()


def revoke_user_session(jti: str) -> dict | None:
    session = get_db_session()
    try:
        row = session.query(UserSession).filter(UserSession.jti == jti).first()
        if row is None:
            return None
        row.revoked_at = datetime.utcnow()
        session.commit()
        session.refresh(row)
        return _user_session_to_dict(row)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _user_to_dict(row: User | None) -> dict | None:
    if row is None:
        return None
    return {
        "id": row.id,
        "username": row.username,
        "email": row.email,
        "password_hash": row.password_hash,
        "is_active": bool(row.is_active),
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def _user_session_to_dict(row: UserSession | None) -> dict | None:
    if row is None:
        return None
    return {
        "id": row.id,
        "user_id": row.user_id,
        "jti": row.jti,
        "token_hash": row.token_hash,
        "expires_at": row.expires_at.isoformat() if row.expires_at else None,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "revoked_at": row.revoked_at.isoformat() if row.revoked_at else None,
    }


def save_analysis_record(user_id: int, payload: dict, trend_title: str, platform: str, trend_match_score: float | None = None, virality_score: float | None = None) -> dict:
    session = get_db_session()
    try:
        row = AnalysisRecord(
            user_id=user_id,
            trend_title=(trend_title or "Untitled analysis").strip(),
            platform=(platform or "linkedin").strip(),
            trend_match_score=_to_float(trend_match_score),
            virality_score=_to_float(virality_score),
            payload=payload,
            created_at=datetime.utcnow(),
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return _analysis_record_to_dict(row)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def save_linkedin_post_record(user_id: int, post_text: str, payload: dict, analysis_id: int | None = None, title: str = "") -> dict:
    session = get_db_session()
    try:
        row = LinkedInPostRecord(
            user_id=user_id,
            analysis_id=analysis_id,
            title=(title or payload.get("title") or "LinkedIn draft").strip(),
            post_text=post_text,
            payload=payload,
            created_at=datetime.utcnow(),
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return _linkedin_post_to_dict(row)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def save_report_record(user_id: int, filename: str, payload: dict, analysis_id: int | None = None) -> dict:
    session = get_db_session()
    try:
        row = ReportRecord(
            user_id=user_id,
            analysis_id=analysis_id,
            filename=filename,
            payload=payload,
            created_at=datetime.utcnow(),
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return _report_record_to_dict(row)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_user_workspace(user_id: int, limit: int = 10) -> dict:
    session = get_db_session()
    try:
        analyses = (
            session.query(AnalysisRecord)
            .filter(AnalysisRecord.user_id == user_id)
            .order_by(AnalysisRecord.created_at.desc(), AnalysisRecord.id.desc())
            .limit(limit)
            .all()
        )
        linkedin_posts = (
            session.query(LinkedInPostRecord)
            .filter(LinkedInPostRecord.user_id == user_id)
            .order_by(LinkedInPostRecord.created_at.desc(), LinkedInPostRecord.id.desc())
            .limit(limit)
            .all()
        )
        reports = (
            session.query(ReportRecord)
            .filter(ReportRecord.user_id == user_id)
            .order_by(ReportRecord.created_at.desc(), ReportRecord.id.desc())
            .limit(limit)
            .all()
        )
        return {
            "success": True,
            "analyses": [_analysis_record_to_dict(row) for row in analyses],
            "linkedin_posts": [_linkedin_post_to_dict(row) for row in linkedin_posts],
            "reports": [_report_record_to_dict(row) for row in reports],
        }
    finally:
        session.close()


def _analysis_record_to_dict(row: AnalysisRecord | None) -> dict | None:
    if row is None:
        return None
    return {
        "id": row.id,
        "user_id": row.user_id,
        "trend_title": row.trend_title,
        "platform": row.platform,
        "trend_match_score": row.trend_match_score,
        "virality_score": row.virality_score,
        "payload": row.payload,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def _linkedin_post_to_dict(row: LinkedInPostRecord | None) -> dict | None:
    if row is None:
        return None
    return {
        "id": row.id,
        "user_id": row.user_id,
        "analysis_id": row.analysis_id,
        "title": row.title,
        "post_text": row.post_text,
        "payload": row.payload,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def _report_record_to_dict(row: ReportRecord | None) -> dict | None:
    if row is None:
        return None
    return {
        "id": row.id,
        "user_id": row.user_id,
        "analysis_id": row.analysis_id,
        "filename": row.filename,
        "payload": row.payload,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def save_post_performance_record(
    user_id: int,
    post_url: str,
    payload: dict,
    platform: str,
    region: str,
    content_title: str,
    likes: int,
    comments: int,
    shares: int,
    reach: int,
    impressions: int,
    engagement_growth: float,
    virality_momentum: float,
    growth_speed: float,
    trend_strength: float,
    engagement_velocity: float,
    trend_relevance: float,
    lifecycle_stage: str,
    should_repost: bool,
    should_improve_hook: bool,
    should_shorten_caption: bool,
    should_follow_up: bool,
    is_saturated: bool,
    expected_reach: int,
    expected_impressions: int,
    peak_engagement_time: str,
    engagement_decay: float,
    live_metrics_available: bool,
    recommendations: dict,
    forecast: dict,
    chart_data: dict,
) -> dict:
    session = get_db_session()
    try:
        row = (
            session.query(PostPerformanceRecord)
            .filter(
                PostPerformanceRecord.user_id == user_id,
                PostPerformanceRecord.post_url == post_url,
            )
            .first()
        )
        now = datetime.utcnow()
        if row is None:
            row = PostPerformanceRecord(
                user_id=user_id,
                post_url=post_url,
                platform=platform,
                region=region,
                created_at=now,
            )
            session.add(row)

        row.platform = platform
        row.region = region
        row.source_label = str(payload.get("source_label") or payload.get("platform_label") or platform.title())
        row.content_title = content_title
        row.likes = int(likes)
        row.comments = int(comments)
        row.shares = int(shares)
        row.reach = int(reach)
        row.impressions = int(impressions)
        row.engagement_growth = float(engagement_growth)
        row.virality_momentum = float(virality_momentum)
        row.growth_speed = float(growth_speed)
        row.trend_strength = float(trend_strength)
        row.engagement_velocity = float(engagement_velocity)
        row.trend_relevance = float(trend_relevance)
        row.lifecycle_stage = lifecycle_stage
        row.should_repost = bool(should_repost)
        row.should_improve_hook = bool(should_improve_hook)
        row.should_shorten_caption = bool(should_shorten_caption)
        row.should_follow_up = bool(should_follow_up)
        row.is_saturated = bool(is_saturated)
        row.expected_reach = int(expected_reach)
        row.expected_impressions = int(expected_impressions)
        row.peak_engagement_time = peak_engagement_time
        row.engagement_decay = float(engagement_decay)
        row.live_metrics_available = bool(live_metrics_available)
        row.payload = payload
        row.recommendations = recommendations
        row.forecast = forecast
        row.chart_data = chart_data
        row.updated_at = now
        row.last_tracked_at = now
        session.commit()
        session.refresh(row)
        return _post_performance_record_to_dict(row)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_post_performance_records(user_id: int | None = None, limit: int = 10) -> list[dict]:
    session = get_db_session()
    try:
        query = session.query(PostPerformanceRecord)
        if user_id is not None:
            query = query.filter(PostPerformanceRecord.user_id == user_id)
        rows = query.order_by(PostPerformanceRecord.last_tracked_at.desc(), PostPerformanceRecord.id.desc()).limit(limit).all()
        return [_post_performance_record_to_dict(row) for row in rows]
    finally:
        session.close()


def get_post_performance_by_url(post_url: str, user_id: int | None = None) -> dict | None:
    session = get_db_session()
    try:
        query = session.query(PostPerformanceRecord).filter(PostPerformanceRecord.post_url == post_url)
        if user_id is not None:
            query = query.filter(PostPerformanceRecord.user_id == user_id)
        row = query.order_by(PostPerformanceRecord.last_tracked_at.desc(), PostPerformanceRecord.id.desc()).first()
        return _post_performance_record_to_dict(row) if row else None
    finally:
        session.close()


def get_latest_post_performance(user_id: int | None = None) -> dict | None:
    records = get_post_performance_records(user_id=user_id, limit=1)
    return records[0] if records else None


def _post_performance_record_to_dict(row: PostPerformanceRecord | None) -> dict | None:
    if row is None:
        return None
    return {
        "id": row.id,
        "user_id": row.user_id,
        "post_url": row.post_url,
        "platform": row.platform,
        "region": row.region,
        "source_label": row.source_label,
        "content_title": row.content_title,
        "likes": row.likes,
        "comments": row.comments,
        "shares": row.shares,
        "reach": row.reach,
        "impressions": row.impressions,
        "engagement_growth": row.engagement_growth,
        "virality_momentum": row.virality_momentum,
        "growth_speed": row.growth_speed,
        "trend_strength": row.trend_strength,
        "engagement_velocity": row.engagement_velocity,
        "trend_relevance": row.trend_relevance,
        "lifecycle_stage": row.lifecycle_stage,
        "should_repost": bool(row.should_repost),
        "should_improve_hook": bool(row.should_improve_hook),
        "should_shorten_caption": bool(row.should_shorten_caption),
        "should_follow_up": bool(row.should_follow_up),
        "is_saturated": bool(row.is_saturated),
        "expected_reach": row.expected_reach,
        "expected_impressions": row.expected_impressions,
        "peak_engagement_time": row.peak_engagement_time,
        "engagement_decay": row.engagement_decay,
        "live_metrics_available": bool(row.live_metrics_available),
        "payload": row.payload,
        "recommendations": row.recommendations,
        "forecast": row.forecast,
        "chart_data": row.chart_data,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        "last_tracked_at": row.last_tracked_at.isoformat() if row.last_tracked_at else None,
    }
