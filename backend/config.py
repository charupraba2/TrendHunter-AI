"""Application configuration helpers."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "TrendHunter AI")
    app_env: str = os.getenv("APP_ENV", "development")
    app_host: str = os.getenv("APP_HOST", "0.0.0.0")
    app_port: int = int(os.getenv("APP_PORT", "8000"))
    secret_key: str = os.getenv("SECRET_KEY", "change-me")
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./database/trendhunter.db")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    allowed_origins_raw: str = os.getenv("ALLOWED_ORIGINS", "http://127.0.0.1:8000,http://localhost:8000")
    trusted_hosts_raw: str = os.getenv("TRUSTED_HOSTS", "127.0.0.1,localhost,0.0.0.0")
    reddit_client_id: str = os.getenv("REDDIT_CLIENT_ID", "")
    reddit_client_secret: str = os.getenv("REDDIT_CLIENT_SECRET", "")
    reddit_user_agent: str = os.getenv("REDDIT_USER_AGENT", "TrendHunterAI/1.0")
    google_trends_hl: str = os.getenv("GOOGLE_TRENDS_HL", "en-US")
    google_trends_tz: int = int(os.getenv("GOOGLE_TRENDS_TZ", "330"))
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    news_api_key: str = os.getenv("NEWS_API_KEY", "")
    youtube_api_key: str = os.getenv("YOUTUBE_API_KEY", "")

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins_raw.split(",") if origin.strip()]

    @property
    def trusted_hosts(self) -> list[str]:
        return [host.strip() for host in self.trusted_hosts_raw.split(",") if host.strip()]


settings = Settings()
