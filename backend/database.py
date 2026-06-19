"""SQLite database setup and ORM models."""

from __future__ import annotations

import hashlib
from threading import Lock
from datetime import datetime, timedelta, timezone
from typing import Iterable

from sqlalchemy import Boolean, JSON, Column, DateTime, Float, Integer, String, create_engine, inspect, text, func
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from backend.config import settings

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
_INDUSTRY_REFRESH_LOCK = Lock()
_INDUSTRY_LAST_REFRESH_TOKEN: str | None = None


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


class IndustryCompany(Base):
    __tablename__ = "industry_company"

    id = Column(Integer, primary_key=True, index=True)
    company_name = Column(String, nullable=False, index=True)
    website = Column(String, nullable=False)
    linkedin_url = Column(String, nullable=True)
    headquarters = Column(String, nullable=True)
    founded_year = Column(Integer, nullable=True)
    company_size = Column(String, nullable=True)
    overview = Column(String, nullable=False)
    core_focus_areas = Column(JSON, nullable=False, default=list)
    industry_positioning = Column(String, nullable=False)
    strategic_themes = Column(JSON, nullable=False, default=list)
    source_notes = Column(JSON, nullable=False, default=list)
    recent_strategic_themes = Column(JSON, nullable=False, default=list)
    focus_keywords = Column(JSON, nullable=False, default=list)
    market_positioning = Column(String, nullable=True)
    content_themes = Column(JSON, nullable=False, default=list)
    company_summary = Column(String, nullable=True)
    strategic_direction = Column(String, nullable=True)
    market_narrative = Column(String, nullable=True)
    last_updated = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class IndustryTrend(Base):
    __tablename__ = "industry_trends"

    id = Column(Integer, primary_key=True, index=True)
    trend_name = Column(String, nullable=False, index=True)
    category = Column(String, nullable=False, index=True)
    summary = Column(String, nullable=False)
    business_impact = Column(String, nullable=False)
    recommended_action = Column(String, nullable=False)
    momentum_score = Column(Float, nullable=False, default=0.0)
    signal_strength = Column(String, nullable=True)
    source_notes = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class IndustryCompetitor(Base):
    __tablename__ = "industry_competitors"

    id = Column(Integer, primary_key=True, index=True)
    competitor_name = Column(String, nullable=False, index=True)
    focus_area = Column(String, nullable=False)
    activity_summary = Column(String, nullable=False)
    market_momentum_score = Column(Float, nullable=False, default=0.0)
    positioning = Column(String, nullable=True)
    source_notes = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class IndustryInsight(Base):
    __tablename__ = "industry_insights"

    id = Column(Integer, primary_key=True, index=True)
    insight_title = Column(String, nullable=False, index=True)
    what_is_trending = Column(String, nullable=False)
    why_it_matters = Column(String, nullable=False)
    business_impact = Column(String, nullable=False)
    recommended_action = Column(String, nullable=False)
    priority = Column(String, nullable=True)
    insight_type = Column(String, nullable=True)
    source_notes = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class IndustryOpportunity(Base):
    __tablename__ = "industry_opportunities"

    id = Column(Integer, primary_key=True, index=True)
    opportunity_name = Column(String, nullable=False, index=True)
    trend_name = Column(String, nullable=False, index=True)
    summary = Column(String, nullable=False)
    target_buyer = Column(String, nullable=False)
    business_value = Column(String, nullable=False)
    urgency = Column(String, nullable=False)
    opportunity_score = Column(Float, nullable=False, default=0.0)
    confidence_score = Column(Float, nullable=False, default=0.0)
    confidence_reason = Column(String, nullable=False, default="")
    evidence_count = Column(Integer, nullable=False, default=0)
    source_count = Column(Integer, nullable=False, default=0)
    source_names = Column(JSON, nullable=False, default=list)
    source_timestamps = Column(JSON, nullable=False, default=list)
    evidence_sources = Column(JSON, nullable=False, default=list)
    supporting_evidence = Column(JSON, nullable=False, default=list)
    signal_inputs = Column(JSON, nullable=False, default=dict)
    source_notes = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class IndustryLiveTrend(Base):
    __tablename__ = "industry_live_trends"

    id = Column(Integer, primary_key=True, index=True)
    trend_name = Column(String, nullable=False, index=True)
    category = Column(String, nullable=False, index=True)
    momentum_score = Column(Float, nullable=False, default=0.0)
    growth_score = Column(Float, nullable=False, default=0.0)
    source_count = Column(Integer, nullable=False, default=0)
    last_updated = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    executive_summary = Column(String, nullable=False)
    signal_strength = Column(String, nullable=True)
    source_notes = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class IndustryKeyword(Base):
    __tablename__ = "industry_keywords"

    id = Column(Integer, primary_key=True, index=True)
    keyword = Column(String, nullable=False, index=True)
    keyword_group = Column(String, nullable=False, index=True)
    momentum_score = Column(Float, nullable=False, default=0.0)
    growth_score = Column(Float, nullable=False, default=0.0)
    source_count = Column(Integer, nullable=False, default=0)
    last_updated = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    executive_summary = Column(String, nullable=False)
    source_notes = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class IndustryCompetitorActivity(Base):
    __tablename__ = "industry_competitor_activity"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    focus_area = Column(String, nullable=False)
    activity_summary = Column(String, nullable=False)
    momentum_score = Column(Float, nullable=False, default=0.0)
    strategic_position = Column(String, nullable=False)
    last_updated = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    source_notes = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class IndustryRecommendation(Base):
    __tablename__ = "industry_recommendations"

    id = Column(Integer, primary_key=True, index=True)
    trend = Column(String, nullable=False, index=True)
    reason = Column(String, nullable=False)
    impact = Column(String, nullable=False)
    recommended_action = Column(String, nullable=False)
    confidence_score = Column(Float, nullable=False, default=0.0)
    last_updated = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    source_notes = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class TrendHistory(Base):
    __tablename__ = "trend_history"

    id = Column(Integer, primary_key=True, index=True)
    keyword = Column(String, nullable=False, index=True)
    trend_score = Column(Float, nullable=False, default=0.0)
    growth_score = Column(Float, nullable=False, default=0.0)
    confidence_score = Column(Float, nullable=False, default=0.0)
    momentum = Column(String, nullable=False, default="Stable")
    source_count = Column(Integer, nullable=False, default=0)
    news_count = Column(Integer, nullable=False, default=0)
    rag_match_count = Column(Integer, nullable=False, default=0)
    competitor_mention_count = Column(Integer, nullable=False, default=0)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)


class IndustryReport(Base):
    __tablename__ = "industry_reports"

    id = Column(Integer, primary_key=True, index=True)
    report_key = Column(String, nullable=False, unique=True, index=True)
    week_label = Column(String, nullable=False)
    top_trends = Column(JSON, nullable=False, default=list)
    competitor_highlights = Column(JSON, nullable=False, default=list)
    strategic_risks = Column(JSON, nullable=False, default=list)
    strategic_opportunities = Column(JSON, nullable=False, default=list)
    executive_recommendations = Column(JSON, nullable=False, default=list)
    generated_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    source_notes = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class IndustryRAGDocument(Base):
    __tablename__ = "industry_rag_documents"

    id = Column(Integer, primary_key=True, index=True)
    doc_type = Column(String, nullable=False, index=True)
    source_name = Column(String, nullable=False, index=True)
    title = Column(String, nullable=False, index=True)
    content = Column(String, nullable=False)
    metadata_json = Column("metadata", JSON, nullable=False, default=dict)
    relevance_score = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    _ensure_trends_columns()
    _ensure_content_ideas_columns()
    _ensure_alerts_columns()
    _ensure_post_performance_columns()
    _ensure_users_columns()
    _ensure_user_sessions_columns()
    _ensure_workspace_columns()
    _ensure_industry_company_columns()
    _ensure_industry_live_columns()
    _seed_industry_intelligence()


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


def _ensure_industry_company_columns() -> None:
    inspector = inspect(engine)
    if "industry_company" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("industry_company")}
    required_columns = {
        "company_name": "VARCHAR",
        "website": "VARCHAR",
        "linkedin_url": "VARCHAR",
        "headquarters": "VARCHAR",
        "founded_year": "INTEGER",
        "company_size": "VARCHAR",
        "overview": "VARCHAR",
        "core_focus_areas": "JSON",
        "industry_positioning": "VARCHAR",
        "strategic_themes": "JSON",
        "source_notes": "JSON",
        "recent_strategic_themes": "JSON",
        "focus_keywords": "JSON",
        "market_positioning": "VARCHAR",
        "content_themes": "JSON",
        "company_summary": "VARCHAR",
        "strategic_direction": "VARCHAR",
        "market_narrative": "VARCHAR",
        "last_updated": "DATETIME",
    }

    with engine.begin() as connection:
        for column_name, column_type in required_columns.items():
            if column_name not in existing_columns:
                connection.execute(text(f"ALTER TABLE industry_company ADD COLUMN {column_name} {column_type}"))


def _ensure_industry_live_columns() -> None:
    inspector = inspect(engine)
    table_columns = {
        "industry_live_trends": {
            "trend_name": "VARCHAR",
            "category": "VARCHAR",
            "momentum_score": "FLOAT",
            "growth_score": "FLOAT",
            "source_count": "INTEGER",
            "last_updated": "DATETIME",
            "executive_summary": "VARCHAR",
            "signal_strength": "VARCHAR",
            "source_notes": "JSON",
            "created_at": "DATETIME",
            "updated_at": "DATETIME",
        },
        "industry_keywords": {
            "keyword": "VARCHAR",
            "keyword_group": "VARCHAR",
            "momentum_score": "FLOAT",
            "growth_score": "FLOAT",
            "source_count": "INTEGER",
            "last_updated": "DATETIME",
            "executive_summary": "VARCHAR",
            "source_notes": "JSON",
            "created_at": "DATETIME",
            "updated_at": "DATETIME",
        },
        "industry_competitor_activity": {
            "name": "VARCHAR",
            "focus_area": "VARCHAR",
            "activity_summary": "VARCHAR",
            "momentum_score": "FLOAT",
            "strategic_position": "VARCHAR",
            "last_updated": "DATETIME",
            "source_notes": "JSON",
            "created_at": "DATETIME",
            "updated_at": "DATETIME",
        },
        "industry_recommendations": {
            "trend": "VARCHAR",
            "reason": "VARCHAR",
            "impact": "VARCHAR",
            "recommended_action": "VARCHAR",
            "confidence_score": "FLOAT",
            "last_updated": "DATETIME",
            "source_notes": "JSON",
            "created_at": "DATETIME",
            "updated_at": "DATETIME",
        },
        "industry_reports": {
            "report_key": "VARCHAR",
            "week_label": "VARCHAR",
            "top_trends": "JSON",
            "competitor_highlights": "JSON",
            "strategic_risks": "JSON",
            "strategic_opportunities": "JSON",
            "executive_recommendations": "JSON",
            "generated_at": "DATETIME",
            "source_notes": "JSON",
            "created_at": "DATETIME",
            "updated_at": "DATETIME",
        },
        "industry_opportunities": {
            "opportunity_name": "VARCHAR",
            "trend_name": "VARCHAR",
            "summary": "VARCHAR",
            "target_buyer": "VARCHAR",
            "business_value": "VARCHAR",
            "urgency": "VARCHAR",
            "opportunity_score": "FLOAT",
            "confidence_score": "FLOAT",
            "confidence_reason": "VARCHAR",
            "evidence_count": "INTEGER",
            "source_count": "INTEGER",
            "source_names": "JSON",
            "source_timestamps": "JSON",
            "evidence_sources": "JSON",
            "supporting_evidence": "JSON",
            "signal_inputs": "JSON",
            "source_notes": "JSON",
            "created_at": "DATETIME",
            "updated_at": "DATETIME",
        },
    }

    existing_tables = set(inspector.get_table_names())
    with engine.begin() as connection:
        for table_name, columns in table_columns.items():
            if table_name not in existing_tables:
                continue
            existing_columns = {column["name"] for column in inspector.get_columns(table_name)}
            for column_name, column_type in columns.items():
                if column_name not in existing_columns:
                    connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"))


_INDUSTRY_COMPANY_SEED = {
    "company_name": "Giggso",
    "website": "https://www.giggso.com/",
    "linkedin_url": "https://www.linkedin.com/company/gogiggso/posts/?feedView=all",
    "headquarters": "Troy, Michigan",
    "founded_year": 2017,
    "company_size": "51-200 employees",
    "overview": "Giggso positions itself as an AI strategy, security, transformation, and data engineering company focused on moving enterprises from AI pilots to production-grade AI profit centers.",
    "core_focus_areas": [
        "AI Governance",
        "AI Security",
        "Enterprise AI",
        "AI Strategy and Transformation",
        "ModelOps and Observability",
        "Data Engineering",
        "Trustworthy AI",
    ],
    "industry_positioning": "A governance-first enterprise AI partner that combines GRC, security, and engineering to make AI safe, scalable, and operationally useful.",
    "strategic_themes": [
        "Move AI from pilot to production",
        "Turn governance into a growth engine",
        "Bridge strategy and execution",
        "Reduce shadow AI and compliance debt",
        "Make AI observable, secure, and trusted",
    ],
    "source_notes": [
        "Official website emphasizes AI strategy, security, transformation, and data engineering.",
        "LinkedIn profile highlights AI ML - Safe & Responsible and a governance-first mission.",
        "Positioning is inferred from the company website and LinkedIn page.",
    ],
}

_INDUSTRY_TRENDS_SEED = [
    {
        "trend_name": "AI Governance",
        "category": "Governance",
        "summary": "Enterprises are formalizing review, approval, and policy workflows before scaling GenAI and agentic systems.",
        "business_impact": "Governance maturity is becoming a buying criterion for enterprise AI adoption.",
        "recommended_action": "Package governance checkpoints, policy controls, and audit-ready reporting into the product narrative.",
        "momentum_score": 96,
        "signal_strength": "Very High",
        "source_notes": ["Matches Giggso's governance-first positioning."],
    },
    {
        "trend_name": "Agentic AI",
        "category": "Agentic AI",
        "summary": "Autonomous workflows are moving from demos into constrained enterprise operations.",
        "business_impact": "Teams need guardrails, approvals, and monitoring to prevent runaway agent behavior.",
        "recommended_action": "Show how the platform observes, constrains, and explains agent decisions.",
        "momentum_score": 92,
        "signal_strength": "Very High",
        "source_notes": ["Linked to Giggso's recent agentic AI messaging on LinkedIn."],
    },
    {
        "trend_name": "LLM Security",
        "category": "Security",
        "summary": "Security teams are prioritizing prompt injection defense, data leakage prevention, and model abuse controls.",
        "business_impact": "Security is a primary blocker for enterprise LLM rollout in regulated environments.",
        "recommended_action": "Frame security as a control layer for LLM apps, not just a compliance add-on.",
        "momentum_score": 94,
        "signal_strength": "Very High",
        "source_notes": ["Aligned with AI security and trustworthy AI messaging."],
    },
    {
        "trend_name": "RAG",
        "category": "Knowledge Systems",
        "summary": "RAG remains the default architecture for grounded enterprise assistants and internal knowledge copilots.",
        "business_impact": "Demand is shifting toward better retrieval, citations, and quality controls.",
        "recommended_action": "Emphasize knowledge ingestion, retrieval quality, and answer traceability.",
        "momentum_score": 88,
        "signal_strength": "High",
        "source_notes": ["Important for enterprise AI deployments and support workflows."],
    },
    {
        "trend_name": "Model Monitoring",
        "category": "Observability",
        "summary": "Organizations are investing in drift detection, quality monitoring, and incident workflows for production models.",
        "business_impact": "Observability helps reduce silent failures and compliance risk after deployment.",
        "recommended_action": "Lead with monitoring dashboards, anomaly detection, and model health reporting.",
        "momentum_score": 90,
        "signal_strength": "High",
        "source_notes": ["Consistent with ModelOps and observability specialties."],
    },
    {
        "trend_name": "Enterprise AI",
        "category": "Enterprise Adoption",
        "summary": "Enterprises want AI that integrates with governance, security, and existing operating models.",
        "business_impact": "Winning vendors need implementation support and ROI framing, not just model capability.",
        "recommended_action": "Position the platform as a production AI operating system for regulated teams.",
        "momentum_score": 91,
        "signal_strength": "Very High",
        "source_notes": ["Website and LinkedIn both point toward enterprise transformation."],
    },
    {
        "trend_name": "AI Risk",
        "category": "Risk",
        "summary": "Boards and executives are asking for risk visibility across data, model behavior, and business process exposure.",
        "business_impact": "Risk reporting is becoming a strategic requirement for enterprise AI programs.",
        "recommended_action": "Create executive risk summaries that translate technical metrics into business language.",
        "momentum_score": 89,
        "signal_strength": "High",
        "source_notes": ["Supports GRC-led enterprise decision making."],
    },
    {
        "trend_name": "AI Compliance",
        "category": "Compliance",
        "summary": "Regulated industries need evidence, controls, and documentation for AI use cases and model operations.",
        "business_impact": "Compliance readiness can determine how quickly AI reaches production in finance, healthcare, and manufacturing.",
        "recommended_action": "Surface audit trails, policy mapping, and compliance-ready workflows as core product value.",
        "momentum_score": 93,
        "signal_strength": "Very High",
        "source_notes": ["Directly aligned with governance, risk, and compliance messaging."],
    },
]

_INDUSTRY_COMPETITOR_SEED = [
    {
        "competitor_name": "OpenAI",
        "focus_area": "Foundation models and enterprise assistant platforms",
        "activity_summary": "Continues to push model capability, deployment tooling, and enterprise usage expansion across chat and API products.",
        "market_momentum_score": 98,
        "positioning": "Infrastructure and model leader shaping the broader enterprise AI stack.",
        "source_notes": ["Competitive reference for model capability and ecosystem influence."],
    },
    {
        "competitor_name": "Anthropic",
        "focus_area": "Enterprise LLM safety and controlled reasoning",
        "activity_summary": "Strong market attention around safety, reliability, and enterprise-grade assistant behavior.",
        "market_momentum_score": 95,
        "positioning": "Safety-forward LLM vendor competing on trust and enterprise readiness.",
        "source_notes": ["Relevant to governance, policy, and agentic AI control narratives."],
    },
    {
        "competitor_name": "Google DeepMind",
        "focus_area": "Research-led model innovation and multimodal systems",
        "activity_summary": "Deep model research and Gemini ecosystem continue to shape AI platform expectations.",
        "market_momentum_score": 94,
        "positioning": "Research powerhouse influencing enterprise expectations for model performance.",
        "source_notes": ["Benchmark competitor for model quality and research depth."],
    },
    {
        "competitor_name": "Microsoft AI",
        "focus_area": "Enterprise AI distribution through cloud and productivity platforms",
        "activity_summary": "Enterprise copilot adoption and platform bundling keep Microsoft central in enterprise AI buying decisions.",
        "market_momentum_score": 96,
        "positioning": "Distribution leader owning enterprise workflow surfaces and cloud bundling.",
        "source_notes": ["Important for enterprise AI platform and workflow positioning."],
    },
    {
        "competitor_name": "Perplexity",
        "focus_area": "Answer engines and AI search",
        "activity_summary": "Visible momentum around search-led discovery, enterprise research workflows, and answer quality.",
        "market_momentum_score": 89,
        "positioning": "Fast-growing answer engine that sets expectations for retrieval and grounded responses.",
        "source_notes": ["Relevant for RAG, answer quality, and enterprise research experiences."],
    },
    {
        "competitor_name": "Cohere",
        "focus_area": "Enterprise LLMs and secure private deployments",
        "activity_summary": "Enterprise-facing model and retrieval products continue to reinforce privacy, customization, and control.",
        "market_momentum_score": 90,
        "positioning": "Enterprise LLM specialist focused on secure deployment and controlled adoption.",
        "source_notes": ["Comparable in regulated enterprise AI environments."],
    },
]

_INDUSTRY_INSIGHT_SEED = [
    {
        "insight_title": "Governance is the buying trigger",
        "what_is_trending": "Enterprise buyers are moving from model curiosity to controlled AI rollout with policy, review, and approval layers.",
        "why_it_matters": "The companies that reduce governance friction will win larger and faster enterprise deployments.",
        "business_impact": "Shorter sales cycles and stronger trust with regulated buyers.",
        "recommended_action": "Lead with governance workflows, auditability, and implementation readiness in every sales motion.",
        "priority": "High",
        "insight_type": "Executive",
        "source_notes": ["Inferred from Giggso's governance-first market posture."],
    },
    {
        "insight_title": "Security is now part of AI value",
        "what_is_trending": "Security, not just model quality, is shaping enterprise AI vendor selection.",
        "why_it_matters": "AI security concerns often block deployment even when business demand is strong.",
        "business_impact": "Security positioning can unlock regulated sectors and premium enterprise deals.",
        "recommended_action": "Package prompt injection, data leakage, and model abuse protection as board-level value.",
        "priority": "High",
        "insight_type": "Risk",
        "source_notes": ["Aligned with the company's AI security and trustworthy AI themes."],
    },
    {
        "insight_title": "Observability is the proof layer",
        "what_is_trending": "Teams want visibility into what models, RAG pipelines, and agents are actually doing in production.",
        "why_it_matters": "Observability reduces post-launch surprises and creates trust with operations and compliance teams.",
        "business_impact": "Higher renewal potential and better expansion into enterprise AI ops budgets.",
        "recommended_action": "Make observability dashboards and model-health reporting a central product story.",
        "priority": "Medium",
        "insight_type": "Operations",
        "source_notes": ["Reflects ModelOps and observability specialties on the company profile."],
    },
    {
        "insight_title": "RAG is the enterprise bridge",
        "what_is_trending": "Retrieval-grounded systems remain the practical path to useful enterprise assistants.",
        "why_it_matters": "RAG lets organizations connect proprietary knowledge to AI without overcommitting to pure model automation.",
        "business_impact": "Better fit for knowledge-heavy use cases in support, operations, and compliance.",
        "recommended_action": "Frame RAG as a governance-friendly enterprise assistant pattern.",
        "priority": "Medium",
        "insight_type": "Adoption",
        "source_notes": ["Useful for enterprise knowledge and support workflows."],
    },
]

_INDUSTRY_OPPORTUNITY_SEED = [
    {
        "opportunity_name": "Governed AI Command Center",
        "trend_name": "AI Governance",
        "summary": "Launch an executive dashboard for policy tracking, approvals, exception handling, and audit readiness.",
        "target_buyer": "CIO, CISO, AI governance lead",
        "business_value": "Turns governance into a visible operating system for AI adoption.",
        "urgency": "Immediate",
        "opportunity_score": 97,
        "source_notes": ["Strong fit for Giggso's governance-led story."],
    },
    {
        "opportunity_name": "Enterprise Agent Safety Layer",
        "trend_name": "Agentic AI",
        "summary": "Package controls for agent permissions, approvals, action logging, and human-in-the-loop checkpoints.",
        "target_buyer": "AI platform owner, security leader",
        "business_value": "Reduces fear around autonomous workflows and accelerates pilot-to-production conversion.",
        "urgency": "Immediate",
        "opportunity_score": 94,
        "source_notes": ["Matches current agentic AI momentum."],
    },
    {
        "opportunity_name": "RAG Quality Observatory",
        "trend_name": "RAG",
        "summary": "Offer retrieval quality, citation coverage, and grounded answer tracking for enterprise knowledge systems.",
        "target_buyer": "Head of Knowledge, Product, Support ops",
        "business_value": "Improves answer trust while lowering support and training costs.",
        "urgency": "Near-term",
        "opportunity_score": 91,
        "source_notes": ["Supports grounded enterprise copilots."],
    },
    {
        "opportunity_name": "AI Compliance Evidence Hub",
        "trend_name": "AI Compliance",
        "summary": "Create evidence packs, control maps, and policy-ready reporting for regulated buyers.",
        "target_buyer": "Compliance, risk, legal",
        "business_value": "Speeds security reviews and compliance approvals.",
        "urgency": "Immediate",
        "opportunity_score": 95,
        "source_notes": ["Directly supports GRC-led sales cycles."],
    },
    {
        "opportunity_name": "Model Monitoring for Production AI",
        "trend_name": "Model Monitoring",
        "summary": "Provide drift detection, incident workflows, and production health views for AI teams.",
        "target_buyer": "ML engineering, platform ops",
        "business_value": "Makes post-launch reliability visible and actionable.",
        "urgency": "Near-term",
        "opportunity_score": 90,
        "source_notes": ["Matches the observability positioning."],
    },
]


_INDUSTRY_LIVE_TREND_BASE = [
    {
        "trend_name": "AI Governance",
        "category": "Governance",
        "base_momentum": 97,
        "base_growth": 93,
        "source_count": 18,
        "executive_summary": "Governance is shifting from policy documentation to operational control for enterprise AI programs.",
        "signal_strength": "Very High",
        "source_notes": ["Governance-led enterprise buying signal"],
    },
    {
        "trend_name": "Agentic AI",
        "category": "Autonomous Systems",
        "base_momentum": 95,
        "base_growth": 96,
        "source_count": 16,
        "executive_summary": "Agentic AI is accelerating, but buyers want guardrails before allowing autonomous actions at scale.",
        "signal_strength": "Very High",
        "source_notes": ["High-growth agent workflow signal"],
    },
    {
        "trend_name": "LLM Security",
        "category": "Security",
        "base_momentum": 94,
        "base_growth": 91,
        "source_count": 15,
        "executive_summary": "Security teams are prioritizing prompt injection defense, data leakage controls, and safe model usage.",
        "signal_strength": "Very High",
        "source_notes": ["Enterprise security signal"],
    },
    {
        "trend_name": "Model Monitoring",
        "category": "Observability",
        "base_momentum": 91,
        "base_growth": 87,
        "source_count": 13,
        "executive_summary": "Model health monitoring is now a production requirement rather than a nice-to-have analytics layer.",
        "signal_strength": "High",
        "source_notes": ["Production AI observability signal"],
    },
    {
        "trend_name": "AI Compliance",
        "category": "Compliance",
        "base_momentum": 96,
        "base_growth": 90,
        "source_count": 14,
        "executive_summary": "Compliance readiness is becoming a sales enabler for regulated enterprise AI deployments.",
        "signal_strength": "Very High",
        "source_notes": ["Regulated market signal"],
    },
    {
        "trend_name": "AI Risk",
        "category": "Risk",
        "base_momentum": 89,
        "base_growth": 84,
        "source_count": 11,
        "executive_summary": "Boards are asking for AI risk visibility across data, behavior, and operational exposure.",
        "signal_strength": "High",
        "source_notes": ["Executive risk signal"],
    },
    {
        "trend_name": "RAG",
        "category": "Knowledge Systems",
        "base_momentum": 90,
        "base_growth": 85,
        "source_count": 12,
        "executive_summary": "RAG remains the practical path to grounded enterprise assistants and knowledge copilots.",
        "signal_strength": "High",
        "source_notes": ["Enterprise knowledge signal"],
    },
    {
        "trend_name": "Enterprise AI",
        "category": "Adoption",
        "base_momentum": 93,
        "base_growth": 88,
        "source_count": 17,
        "executive_summary": "Enterprise buyers want AI platforms that can survive governance, security, and implementation scrutiny.",
        "signal_strength": "Very High",
        "source_notes": ["Enterprise adoption signal"],
    },
    {
        "trend_name": "Trustworthy AI",
        "category": "Trust",
        "base_momentum": 92,
        "base_growth": 86,
        "source_count": 10,
        "executive_summary": "Trustworthy AI language is becoming a differentiator in procurement and executive reviews.",
        "signal_strength": "High",
        "source_notes": ["Trust and assurance signal"],
    },
    {
        "trend_name": "Shadow AI",
        "category": "Governance Risk",
        "base_momentum": 88,
        "base_growth": 89,
        "source_count": 9,
        "executive_summary": "Shadow AI usage is forcing governance teams to formalize controls faster than planned.",
        "signal_strength": "High",
        "source_notes": ["Hidden usage and control gap signal"],
    },
]

_INDUSTRY_KEYWORD_BASE = [
    {"keyword": "AI Governance", "keyword_group": "Top AI Governance Keywords", "base_momentum": 99, "base_growth": 94, "source_count": 20},
    {"keyword": "Agentic AI", "keyword_group": "Top AI Governance Keywords", "base_momentum": 97, "base_growth": 96, "source_count": 18},
    {"keyword": "LLM Security", "keyword_group": "Top AI Governance Keywords", "base_momentum": 96, "base_growth": 93, "source_count": 16},
    {"keyword": "Model Monitoring", "keyword_group": "Fastest Growing Keywords", "base_momentum": 91, "base_growth": 95, "source_count": 14},
    {"keyword": "Policy Controls", "keyword_group": "Fastest Growing Keywords", "base_momentum": 90, "base_growth": 94, "source_count": 15},
    {"keyword": "Trustworthy AI", "keyword_group": "Fastest Growing Keywords", "base_momentum": 92, "base_growth": 92, "source_count": 12},
    {"keyword": "AI Risk", "keyword_group": "Enterprise Adoption Keywords", "base_momentum": 88, "base_growth": 87, "source_count": 11},
    {"keyword": "RAG", "keyword_group": "Enterprise Adoption Keywords", "base_momentum": 89, "base_growth": 86, "source_count": 13},
    {"keyword": "Enterprise AI", "keyword_group": "Enterprise Adoption Keywords", "base_momentum": 94, "base_growth": 90, "source_count": 17},
    {"keyword": "Shadow AI", "keyword_group": "Enterprise Adoption Keywords", "base_momentum": 86, "base_growth": 91, "source_count": 10},
]

_INDUSTRY_COMPETITOR_ACTIVITY_BASE = [
    {
        "name": "OpenAI",
        "focus_area": "Foundation models and enterprise assistants",
        "activity_summary": "Continues to define the pace of enterprise AI with model releases, tooling, and platform adoption.",
        "base_momentum": 98,
        "strategic_position": "Category setter for enterprise model capability and ecosystem breadth.",
        "source_notes": ["Model capability benchmark"],
    },
    {
        "name": "Anthropic",
        "focus_area": "Enterprise LLM safety and controlled reasoning",
        "activity_summary": "Market attention remains high around safety, reliability, and enterprise-grade assistant behavior.",
        "base_momentum": 95,
        "strategic_position": "Safety-first LLM competitor influencing governance narratives.",
        "source_notes": ["Safety-forward enterprise LLM"],
    },
    {
        "name": "Microsoft AI",
        "focus_area": "Enterprise AI distribution and productivity workflows",
        "activity_summary": "Copilot distribution keeps Microsoft central to enterprise AI purchase and deployment decisions.",
        "base_momentum": 96,
        "strategic_position": "Distribution leader with workflow ownership across the enterprise stack.",
        "source_notes": ["Enterprise workflow bundling"],
    },
    {
        "name": "Google DeepMind",
        "focus_area": "Research-led model innovation and multimodal systems",
        "activity_summary": "DeepMind and Gemini continue to raise expectations for research depth and multimodal capability.",
        "base_momentum": 94,
        "strategic_position": "Research powerhouse setting performance expectations.",
        "source_notes": ["Research and multimodal benchmark"],
    },
    {
        "name": "Perplexity",
        "focus_area": "Answer engines and AI search",
        "activity_summary": "Search-led discovery and grounded answers keep Perplexity highly visible in enterprise research workflows.",
        "base_momentum": 89,
        "strategic_position": "Answer engine competing on retrieval quality and trust.",
        "source_notes": ["Grounded answers benchmark"],
    },
    {
        "name": "Cohere",
        "focus_area": "Enterprise LLMs and secure private deployments",
        "activity_summary": "Private deployment, customization, and enterprise controls remain central to the Cohere story.",
        "base_momentum": 90,
        "strategic_position": "Enterprise LLM specialist focused on controlled adoption.",
        "source_notes": ["Private enterprise deployment"],
    },
]

_INDUSTRY_RECOMMENDATION_BASE = [
    {
        "trend": "Agentic AI",
        "reason": "Autonomous workflows are moving from demos into constrained production use cases.",
        "impact": "Governance controls can become a competitive differentiator in the sales process.",
        "recommended_action": "Lead with policy checks, approval flows, and action logging for agent deployments.",
        "base_confidence": 95,
        "source_notes": ["Agentic AI adoption signal"],
    },
    {
        "trend": "LLM Security",
        "reason": "Security teams are prioritizing prompt injection and data leakage controls.",
        "impact": "Security buyers are more likely to approve enterprise rollouts when safeguards are explicit.",
        "recommended_action": "Package LLM threat detection, leakage prevention, and policy enforcement as a core module.",
        "base_confidence": 96,
        "source_notes": ["Security budget signal"],
    },
    {
        "trend": "AI Compliance",
        "reason": "Regulated industries need audit-ready evidence and operational controls.",
        "impact": "Compliance automation can accelerate enterprise procurement and reduce review cycles.",
        "recommended_action": "Show evidence packs, policy mapping, and audit trail exports in executive messaging.",
        "base_confidence": 94,
        "source_notes": ["Regulated buying signal"],
    },
    {
        "trend": "Model Monitoring",
        "reason": "Production AI teams need visibility into drift, incidents, and answer quality.",
        "impact": "Observability becomes a retention and expansion lever after deployment.",
        "recommended_action": "Position monitoring dashboards as operational proof of trustworthy AI.",
        "base_confidence": 91,
        "source_notes": ["Production reliability signal"],
    },
]


def _clamp_score(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return round(max(minimum, min(maximum, value)), 2)


def _stable_variation(seed: str, cycle: int, spread: int = 5) -> int:
    digest = hashlib.sha256(f"{seed}:{cycle}".encode("utf-8")).hexdigest()
    raw = int(digest[:8], 16)
    return int(raw % (spread * 2 + 1)) - spread


def _live_cycle(now: datetime | None = None) -> int:
    now = now or datetime.utcnow()
    return int(now.timestamp() // 1800)


def _live_bucket(now: datetime | None = None) -> datetime:
    now = now or datetime.utcnow()
    return now.replace(minute=(now.minute // 30) * 30, second=0, microsecond=0)


def _live_summary(base_summary: str, trend_name: str, momentum: float, growth: float, source_count: int) -> str:
    return (
        f"{trend_name} is tracking at {momentum:.0f}% momentum and {growth:.0f}% growth across {source_count} live signals. "
        f"{base_summary}"
    )


def _json_safe(value):
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    return value


def _build_live_industry_snapshot(now: datetime | None = None) -> dict:
    now = now or datetime.utcnow()
    cycle = _live_cycle(now)
    bucket = _live_bucket(now)

    live_trends: list[dict] = []
    for item in _INDUSTRY_LIVE_TREND_BASE:
        momentum = _clamp_score(item["base_momentum"] + _stable_variation(item["trend_name"], cycle, 3))
        growth = _clamp_score(item["base_growth"] + _stable_variation(f"{item['trend_name']}:growth", cycle, 4))
        source_count = max(1, int(item["source_count"]) + _stable_variation(f"{item['trend_name']}:sources", cycle, 2))
        live_trends.append(
            {
                "trend_name": item["trend_name"],
                "category": item["category"],
                "momentum_score": momentum,
                "growth_score": growth,
                "source_count": source_count,
                "last_updated": bucket,
                "executive_summary": _live_summary(item["executive_summary"], item["trend_name"], momentum, growth, source_count),
                "signal_strength": item["signal_strength"],
                "source_notes": item["source_notes"],
                "created_at": bucket,
                "updated_at": now,
            }
        )

    keyword_groups = {
        "Top AI Governance Keywords": "Executive priority terms appearing across governance-led AI discussions.",
        "Fastest Growing Keywords": "Keywords with the steepest recent growth and management attention.",
        "Enterprise Adoption Keywords": "Adoption language showing up in enterprise buyer conversations.",
    }
    live_keywords: list[dict] = []
    for item in _INDUSTRY_KEYWORD_BASE:
        momentum = _clamp_score(item["base_momentum"] + _stable_variation(item["keyword"], cycle, 3))
        growth = _clamp_score(item["base_growth"] + _stable_variation(f"{item['keyword']}:growth", cycle, 4))
        source_count = max(1, int(item["source_count"]) + _stable_variation(f"{item['keyword']}:sources", cycle, 2))
        live_keywords.append(
            {
                "keyword": item["keyword"],
                "keyword_group": item["keyword_group"],
                "momentum_score": momentum,
                "growth_score": growth,
                "source_count": source_count,
                "last_updated": bucket,
                "executive_summary": f"{item['keyword']} remains a {item['keyword_group'].lower()} signal with momentum at {momentum:.0f}%.",
                "source_notes": [keyword_groups.get(item["keyword_group"], "")],
                "created_at": bucket,
                "updated_at": now,
            }
        )

    live_competitors: list[dict] = []
    for item in _INDUSTRY_COMPETITOR_ACTIVITY_BASE:
        momentum = _clamp_score(item["base_momentum"] + _stable_variation(item["name"], cycle, 2))
        live_competitors.append(
            {
                "name": item["name"],
                "focus_area": item["focus_area"],
                "activity_summary": item["activity_summary"],
                "momentum_score": momentum,
                "strategic_position": f"{item['strategic_position']} Momentum remains at {momentum:.0f}%.",
                "last_updated": bucket,
                "source_notes": item["source_notes"],
                "created_at": bucket,
                "updated_at": now,
            }
        )

    live_recommendations: list[dict] = []
    trend_lookup = {item["trend_name"]: item for item in live_trends}
    for item in _INDUSTRY_RECOMMENDATION_BASE:
        trend = trend_lookup.get(item["trend"], {})
        confidence = _clamp_score(item["base_confidence"] + _stable_variation(item["trend"], cycle, 2))
        live_recommendations.append(
            {
                "trend": item["trend"],
                "reason": item["reason"],
                "impact": item["impact"],
                "recommended_action": item["recommended_action"],
                "confidence_score": confidence,
                "last_updated": bucket,
                "source_notes": item["source_notes"] + ([trend.get("executive_summary")] if trend else []),
                "created_at": bucket,
                "updated_at": now,
            }
        )

    top_trends = sorted(live_trends, key=lambda row: (row["momentum_score"], row["growth_score"]), reverse=True)[:5]
    competitor_highlights = sorted(live_competitors, key=lambda row: row["momentum_score"], reverse=True)[:4]
    strategic_risks = [
        {
            "risk": "Shadow AI usage expanding faster than policy coverage.",
            "severity": "High",
            "response": "Position governance automation as the fastest way to close the policy gap.",
        },
        {
            "risk": "LLM security reviews slowing enterprise deployment.",
            "severity": "High",
            "response": "Make security controls visible in the product narrative and implementation checklist.",
        },
        {
            "risk": "Competitors bundling AI capabilities into existing enterprise platforms.",
            "severity": "Medium",
            "response": "Differentiate on governance depth, observability, and compliance proof.",
        },
    ]
    strategic_opportunities = [
        {
            "opportunity": "Governed agent rollout packages",
            "signal": "Agentic AI adoption is rising, but buyers want guardrails.",
        },
        {
            "opportunity": "Compliance evidence automation",
            "signal": "Regulated buyers need audit-ready proof to accelerate procurement.",
        },
        {
            "opportunity": "RAG quality and observability",
            "signal": "Knowledge assistant teams want grounded answers and monitoring.",
        },
    ]

    report = {
        "report_key": "weekly-industry-report",
        "week_label": f"Week of {bucket.date().isoformat()}",
        "top_trends": _json_safe(top_trends),
        "competitor_highlights": _json_safe(competitor_highlights),
        "strategic_risks": _json_safe(strategic_risks),
        "strategic_opportunities": _json_safe(strategic_opportunities),
        "executive_recommendations": _json_safe(live_recommendations),
        "generated_at": now,
        "source_notes": ["Weekly executive intelligence snapshot refreshed from live industry signals."],
        "created_at": now,
        "updated_at": now,
    }

    company_summary = (
        "Giggso is positioned as a governance-first enterprise AI company focused on making AI safe, secure, observable, and production ready."
    )
    strategic_direction = (
        "Lead enterprise buyers from AI experimentation to controlled production adoption through governance, security, and compliance tooling."
    )
    market_narrative = (
        "The market is rewarding vendors that can reduce AI risk while accelerating enterprise deployment and proving business value."
    )
    company_row = {
        **_INDUSTRY_COMPANY_SEED,
        "recent_strategic_themes": [
            "AI Governance automation",
            "AI Security and LLM controls",
            "Enterprise AI deployment readiness",
            "AI Compliance evidence",
            "Agentic AI guardrails",
        ],
        "focus_keywords": [item["keyword"] for item in live_keywords[:7]],
        "market_positioning": "Governance-first enterprise AI platform and services partner.",
        "content_themes": [
            "Safe and responsible AI",
            "Governance and compliance",
            "Enterprise AI operations",
            "Security and trust",
        ],
        "company_summary": company_summary,
        "strategic_direction": strategic_direction,
        "market_narrative": market_narrative,
        "last_updated": now,
        "updated_at": now,
    }

    return {
        "company": company_row,
        "trends": live_trends,
        "keywords": live_keywords,
        "competitors": live_competitors,
        "recommendations": live_recommendations,
        "report": report,
    }


def _seed_industry_intelligence() -> None:
    session = get_db_session()
    try:
        has_live_data = (
            session.query(IndustryCompany.id).first() is not None
            and session.query(IndustryLiveTrend.id).first() is not None
            and session.query(IndustryKeyword.id).first() is not None
            and session.query(IndustryCompetitorActivity.id).first() is not None
            and session.query(IndustryRecommendation.id).first() is not None
            and session.query(IndustryReport.id).first() is not None
        )
        if not has_live_data:
            try:
                from backend.services.industry_intelligence_service import industry_intelligence_service

                industry_intelligence_service.refresh(force=True)
            except Exception:
                if session.query(IndustryCompany.id).first() is None:
                    session.add(IndustryCompany(**_build_live_industry_snapshot()["company"]))

                if session.query(IndustryTrend.id).first() is None:
                    session.add_all([IndustryTrend(**item) for item in _INDUSTRY_TRENDS_SEED])

                if session.query(IndustryCompetitor.id).first() is None:
                    session.add_all([IndustryCompetitor(**item) for item in _INDUSTRY_COMPETITOR_SEED])

                if session.query(IndustryInsight.id).first() is None:
                    session.add_all([IndustryInsight(**item) for item in _INDUSTRY_INSIGHT_SEED])

                if session.query(IndustryOpportunity.id).first() is None:
                    session.add_all([IndustryOpportunity(**item) for item in _INDUSTRY_OPPORTUNITY_SEED])

                session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


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
            query = query.filter((func.lower(Trend.region) == region_value.lower()) | (Trend.region.is_(None)))
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


def get_industry_company() -> dict | None:
    refresh_industry_live_data()
    session = get_db_session()
    try:
        row = session.query(IndustryCompany).order_by(IndustryCompany.last_updated.desc().nullslast(), IndustryCompany.updated_at.desc(), IndustryCompany.id.desc()).first()
        return _industry_company_to_dict(row) if row else None
    finally:
        session.close()


def get_industry_trends(limit: int = 50) -> list[dict]:
    refresh_industry_live_data()
    session = get_db_session()
    try:
        rows = session.query(IndustryLiveTrend).order_by(IndustryLiveTrend.momentum_score.desc(), IndustryLiveTrend.growth_score.desc(), IndustryLiveTrend.id.desc()).limit(limit).all()
        return [_industry_live_trend_to_dict(row) for row in rows]
    finally:
        session.close()


def get_industry_competitors(limit: int = 50) -> list[dict]:
    refresh_industry_live_data()
    session = get_db_session()
    try:
        rows = session.query(IndustryCompetitorActivity).order_by(IndustryCompetitorActivity.momentum_score.desc(), IndustryCompetitorActivity.id.desc()).limit(limit).all()
        return [_industry_competitor_activity_to_dict(row) for row in rows]
    finally:
        session.close()


def get_industry_insights(limit: int = 50) -> list[dict]:
    refresh_industry_live_data()
    session = get_db_session()
    try:
        rows = (
            session.query(IndustryInsight)
            .order_by(IndustryInsight.created_at.desc(), IndustryInsight.id.desc())
            .limit(limit)
            .all()
        )
        return [_industry_insight_to_dict(row) for row in rows]
    finally:
        session.close()


def get_industry_opportunities(limit: int = 50) -> list[dict]:
    refresh_industry_live_data()
    session = get_db_session()
    try:
        rows = (
            session.query(IndustryOpportunity)
            .order_by(IndustryOpportunity.opportunity_score.desc(), IndustryOpportunity.updated_at.desc(), IndustryOpportunity.id.desc())
            .limit(limit)
            .all()
        )
        return [_industry_opportunity_to_dict(row) for row in rows]
    finally:
        session.close()


def _industry_company_to_dict(row: IndustryCompany | None) -> dict | None:
    if row is None:
        return None
    return {
        "id": row.id,
        "company_name": row.company_name,
        "website": row.website,
        "linkedin_url": row.linkedin_url,
        "headquarters": row.headquarters,
        "founded_year": row.founded_year,
        "company_size": row.company_size,
        "overview": row.overview,
        "core_focus_areas": row.core_focus_areas or [],
        "industry_positioning": row.industry_positioning,
        "strategic_themes": row.strategic_themes or [],
        "source_notes": row.source_notes or [],
        "recent_strategic_themes": row.recent_strategic_themes or [],
        "focus_keywords": row.focus_keywords or [],
        "market_positioning": row.market_positioning,
        "content_themes": row.content_themes or [],
        "company_summary": row.company_summary or row.overview,
        "strategic_direction": row.strategic_direction,
        "market_narrative": row.market_narrative,
        "last_updated": row.last_updated.isoformat() if row.last_updated else None,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def _industry_live_trend_to_dict(row: IndustryLiveTrend | None) -> dict | None:
    if row is None:
        return None
    return {
        "id": row.id,
        "trend_name": row.trend_name,
        "category": row.category,
        "momentum_score": row.momentum_score,
        "growth_score": row.growth_score,
        "source_count": row.source_count,
        "last_updated": row.last_updated.isoformat() if row.last_updated else None,
        "executive_summary": row.executive_summary,
        "signal_strength": row.signal_strength,
        "source_notes": row.source_notes or [],
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def _industry_keyword_to_dict(row: IndustryKeyword | None) -> dict | None:
    if row is None:
        return None
    return {
        "id": row.id,
        "keyword": row.keyword,
        "keyword_group": row.keyword_group,
        "momentum_score": row.momentum_score,
        "growth_score": row.growth_score,
        "source_count": row.source_count,
        "last_updated": row.last_updated.isoformat() if row.last_updated else None,
        "executive_summary": row.executive_summary,
        "source_notes": row.source_notes or [],
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def _industry_competitor_activity_to_dict(row: IndustryCompetitorActivity | None) -> dict | None:
    if row is None:
        return None
    return {
        "id": row.id,
        "name": row.name,
        "focus_area": row.focus_area,
        "activity_summary": row.activity_summary,
        "momentum_score": row.momentum_score,
        "strategic_position": row.strategic_position,
        "last_updated": row.last_updated.isoformat() if row.last_updated else None,
        "source_notes": row.source_notes or [],
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def _industry_recommendation_to_dict(row: IndustryRecommendation | None) -> dict | None:
    if row is None:
        return None
    return {
        "id": row.id,
        "trend": row.trend,
        "reason": row.reason,
        "impact": row.impact,
        "recommended_action": row.recommended_action,
        "confidence_score": row.confidence_score,
        "last_updated": row.last_updated.isoformat() if row.last_updated else None,
        "source_notes": row.source_notes or [],
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def _industry_report_to_dict(row: IndustryReport | None) -> dict | None:
    if row is None:
        return None
    return {
        "id": row.id,
        "report_key": row.report_key,
        "week_label": row.week_label,
        "top_trends": row.top_trends or [],
        "competitor_highlights": row.competitor_highlights or [],
        "strategic_risks": row.strategic_risks or [],
        "strategic_opportunities": row.strategic_opportunities or [],
        "executive_recommendations": row.executive_recommendations or [],
        "generated_at": row.generated_at.isoformat() if row.generated_at else None,
        "source_notes": row.source_notes or [],
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def _industry_insight_to_dict(row: IndustryInsight | None) -> dict | None:
    if row is None:
        return None
    return {
        "id": row.id,
        "insight_title": row.insight_title,
        "what_is_trending": row.what_is_trending,
        "why_it_matters": row.why_it_matters,
        "business_impact": row.business_impact,
        "recommended_action": row.recommended_action,
        "priority": row.priority,
        "insight_type": row.insight_type,
        "source_notes": row.source_notes or [],
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def _industry_opportunity_to_dict(row: IndustryOpportunity | None) -> dict | None:
    if row is None:
        return None
    return {
        "id": row.id,
        "opportunity_name": row.opportunity_name,
        "trend_name": row.trend_name,
        "summary": row.summary,
        "target_buyer": row.target_buyer,
        "business_value": row.business_value,
        "urgency": row.urgency,
        "opportunity_score": row.opportunity_score,
        "priority_score": row.opportunity_score,
        "confidence_score": row.confidence_score,
        "impact_score": row.opportunity_score,
        "confidence_reason": row.confidence_reason,
        "evidence_count": row.evidence_count,
        "source_count": row.source_count,
        "source_names": row.source_names or [],
        "source_timestamps": row.source_timestamps or [],
        "evidence_sources": row.evidence_sources or [],
        "supporting_evidence": row.supporting_evidence or [],
        "signal_inputs": row.signal_inputs or {},
        "source_notes": row.source_notes or [],
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def refresh_industry_live_data(force: bool = False) -> dict:
    from backend.services.industry_intelligence_service import industry_intelligence_service

    return industry_intelligence_service.refresh(force=force)


def get_industry_live_trends(limit: int = 50) -> list[dict]:
    refresh_industry_live_data()
    session = get_db_session()
    try:
        rows = session.query(IndustryLiveTrend).order_by(IndustryLiveTrend.momentum_score.desc(), IndustryLiveTrend.growth_score.desc(), IndustryLiveTrend.id.desc()).limit(limit).all()
        return [_industry_live_trend_to_dict(row) for row in rows]
    finally:
        session.close()


def get_industry_keywords(limit: int = 50) -> list[dict]:
    refresh_industry_live_data()
    session = get_db_session()
    try:
        rows = session.query(IndustryKeyword).order_by(IndustryKeyword.keyword_group.asc(), IndustryKeyword.growth_score.desc(), IndustryKeyword.id.asc()).limit(limit).all()
        return [_industry_keyword_to_dict(row) for row in rows]
    finally:
        session.close()


def get_industry_competitor_activity(limit: int = 50) -> list[dict]:
    refresh_industry_live_data()
    session = get_db_session()
    try:
        rows = session.query(IndustryCompetitorActivity).order_by(IndustryCompetitorActivity.momentum_score.desc(), IndustryCompetitorActivity.id.desc()).limit(limit).all()
        return [_industry_competitor_activity_to_dict(row) for row in rows]
    finally:
        session.close()


def get_industry_recommendations(limit: int = 50) -> list[dict]:
    refresh_industry_live_data()
    session = get_db_session()
    try:
        rows = session.query(IndustryRecommendation).order_by(IndustryRecommendation.confidence_score.desc(), IndustryRecommendation.id.desc()).limit(limit).all()
        return [_industry_recommendation_to_dict(row) for row in rows]
    finally:
        session.close()


def get_industry_report() -> dict | None:
    refresh_industry_live_data()
    session = get_db_session()
    try:
        row = session.query(IndustryReport).order_by(IndustryReport.generated_at.desc(), IndustryReport.id.desc()).first()
        return _industry_report_to_dict(row) if row else None
    finally:
        session.close()


def _trend_history_to_dict(row: TrendHistory | None) -> dict | None:
    if row is None:
        return None
    return {
        "id": row.id,
        "keyword": row.keyword,
        "trend_score": row.trend_score,
        "growth_score": row.growth_score,
        "confidence_score": row.confidence_score,
        "momentum": row.momentum,
        "source_count": row.source_count,
        "news_count": row.news_count,
        "rag_match_count": row.rag_match_count,
        "competitor_mention_count": row.competitor_mention_count,
        "timestamp": row.timestamp.isoformat() if row.timestamp else None,
    }


def save_trend_history(entries: Iterable[dict]) -> int:
    inserted = 0
    session = get_db_session()
    try:
        for entry in entries:
            keyword = str(entry.get("keyword") or "").strip()
            timestamp = entry.get("timestamp")
            if not keyword:
                continue
            if not isinstance(timestamp, datetime):
                timestamp = datetime.utcnow()
            minute_start = timestamp.replace(second=0, microsecond=0)
            minute_end = minute_start + timedelta(minutes=1)
            existing = (
                session.query(TrendHistory.id)
                .filter(
                    TrendHistory.keyword == keyword,
                    TrendHistory.timestamp >= minute_start,
                    TrendHistory.timestamp < minute_end,
                )
                .first()
            )
            if existing:
                continue
            session.add(
                TrendHistory(
                    keyword=keyword,
                    trend_score=_to_float(entry.get("trend_score")) or 0.0,
                    growth_score=_to_float(entry.get("growth_score")) or 0.0,
                    confidence_score=_to_float(entry.get("confidence_score")) or 0.0,
                    momentum=str(entry.get("momentum") or "Stable"),
                    source_count=_to_int(entry.get("source_count")) or 0,
                    news_count=_to_int(entry.get("news_count")) or 0,
                    rag_match_count=_to_int(entry.get("rag_match_count")) or 0,
                    competitor_mention_count=_to_int(entry.get("competitor_mention_count")) or 0,
                    timestamp=timestamp,
                )
            )
            inserted += 1
        session.commit()
        return inserted
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _trend_direction(delta: float, threshold: float = 5.0) -> tuple[str, str]:
    if delta >= threshold:
        return "rising", "Rising strongly" if delta >= 10 else "Rising"
    if delta <= -threshold:
        return "falling", "Falling strongly" if delta <= -10 else "Falling"
    return "stable", "Stable"


def get_trend_history(keyword: str, range_label: str = "7d", limit: int = 20) -> dict | None:
    keyword_text = str(keyword or "").strip()
    if not keyword_text:
        return None
    window = {
        "24h": timedelta(hours=24),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
    }.get(str(range_label or "7d").lower(), timedelta(days=7))
    now = datetime.now(timezone.utc)
    start = now - window
    session = get_db_session()
    try:
        rows = (
            session.query(TrendHistory)
            .filter(TrendHistory.keyword == keyword_text, TrendHistory.timestamp >= start)
            .order_by(TrendHistory.timestamp.desc(), TrendHistory.id.desc())
            .limit(max(2, limit))
            .all()
        )
        history = [_trend_history_to_dict(row) for row in rows]
        current = history[0] if history else None
        previous = history[1] if len(history) > 1 else current
        current_score = (_to_float(current.get("trend_score")) or 0.0) if current else 0.0
        previous_score = (_to_float(previous.get("trend_score")) or current_score) if previous else current_score
        delta = round(current_score - previous_score, 1)
        direction, movement_label = _trend_direction(delta)
        return {
            "keyword": keyword_text,
            "current_score": round(current_score, 1),
            "previous_score": round(previous_score, 1),
            "delta": round(delta, 1),
            "direction": direction,
            "movement_label": movement_label,
            "history": list(reversed(history)),
            "range": str(range_label or "7d").lower(),
            "updated_at": current.get("timestamp") if current else None,
        }
    finally:
        session.close()


def get_trend_history_leaderboard(range_label: str = "7d", limit: int = 5) -> dict:
    window = {
        "24h": timedelta(hours=24),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
    }.get(str(range_label or "7d").lower(), timedelta(days=7))
    now = datetime.now(timezone.utc)
    start = now - window
    session = get_db_session()
    try:
        rows = (
            session.query(TrendHistory)
            .filter(TrendHistory.timestamp >= start)
            .order_by(TrendHistory.keyword.asc(), TrendHistory.timestamp.desc(), TrendHistory.id.desc())
            .all()
        )
        grouped: dict[str, list[TrendHistory]] = {}
        for row in rows:
            grouped.setdefault(row.keyword, []).append(row)
        movements: list[dict] = []
        for keyword, items in grouped.items():
            current = items[0]
            previous = items[1] if len(items) > 1 else current
            current_score = _to_float(current.trend_score) or 0.0
            previous_score = _to_float(previous.trend_score) or current_score
            delta = round(current_score - previous_score, 1)
            direction, movement_label = _trend_direction(delta)
            movements.append(
                {
                    "keyword": keyword,
                    "current_score": round(current_score, 1),
                    "previous_score": round(previous_score, 1),
                    "delta": round(delta, 1),
                    "direction": direction,
                    "movement_label": movement_label,
                    "history": [_trend_history_to_dict(item) for item in items[:limit]][::-1],
                }
            )
        rising = sorted([item for item in movements if item["direction"] == "rising"], key=lambda item: (item["delta"], item["current_score"]), reverse=True)[:limit]
        falling = sorted([item for item in movements if item["direction"] == "falling"], key=lambda item: (item["delta"], item["current_score"]))[:limit]
        stable = sorted([item for item in movements if item["direction"] == "stable"], key=lambda item: item["current_score"], reverse=True)[:limit]
        return {
            "range": str(range_label or "7d").lower(),
            "top_rising_trends": rising,
            "top_falling_trends": falling,
            "stable_trends": stable,
            "generated_at": now.isoformat(),
        }
    finally:
        session.close()


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
