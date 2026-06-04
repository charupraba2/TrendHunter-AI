"""NewsAPI service for live trend collection."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from backend.config import settings

logger = logging.getLogger(__name__)


class NewsService:
    def __init__(self) -> None:
        self.api_key = settings.news_api_key.strip()
        self._client = self._load_client() if self.api_key else None

    def _load_client(self):
        try:
            from newsapi import NewsApiClient
        except Exception:
            logger.warning("newsapi-python is not available.")
            return None

        try:
            return NewsApiClient(api_key=self.api_key)
        except Exception as exc:
            logger.warning("NewsAPI client could not be initialized: %s", exc)
            return None

    def fetch_latest_trending_news(self, country: str = "us", page_size: int = 10) -> list[dict[str, Any]]:
        if self._client is None:
            logger.info("NewsAPI key missing or client unavailable. Using demo news trends.")
            return self._demo_news("latest")

        try:
            response = self._client.get_top_headlines(country=country, page_size=page_size)

            if not isinstance(response, dict):
                raise ValueError("NewsAPI returned an invalid response payload.")
            if response.get("status") != "ok":
                raise ValueError(f"NewsAPI returned status {response.get('status')!r}.")

            articles = response.get("articles") or []
            if not articles:
                raise ValueError("NewsAPI returned an empty articles list.")

            items = [self._normalize_article(article, index) for index, article in enumerate(articles)]
            if items:
                logger.info("Fetched %s news trends from NewsAPI with source type %s", len(items), "newsapi")
                return items
            logger.info("NewsAPI returned no articles. Using demo news trends.")
        except Exception as exc:
            logger.warning("NewsAPI fetch failed: %s", exc)
        return self._demo_news("latest")

    def search_news(self, keyword: str, page_size: int = 10) -> list[dict[str, Any]]:
        keyword = (keyword or "").strip()
        if not keyword:
            return self.fetch_latest_trending_news(page_size=page_size)

        if self._client is None:
            logger.info("NewsAPI key missing or client unavailable. Using demo news search results for %s", keyword)
            return self._demo_news(keyword)

        try:
            response = self._client.get_everything(q=keyword, language="en", sort_by="publishedAt", page_size=page_size)

            if not isinstance(response, dict):
                raise ValueError("NewsAPI returned an invalid response payload.")
            if response.get("status") != "ok":
                raise ValueError(f"NewsAPI returned status {response.get('status')!r}.")

            articles = response.get("articles") or []
            if not articles:
                raise ValueError("NewsAPI returned an empty articles list.")

            items = [self._normalize_article(article, index, keyword=keyword) for index, article in enumerate(articles)]
            if items:
                logger.info("Fetched %s NewsAPI search results for %s with source type %s", len(items), keyword, "newsapi")
                return items
            logger.info("NewsAPI search returned no articles for %s. Using demo news trends.", keyword)
        except Exception as exc:
            logger.warning("NewsAPI search failed for %s: %s", keyword, exc)
        return self._demo_news(keyword)

    def _normalize_article(self, article: dict[str, Any], index: int, keyword: str | None = None) -> dict[str, Any]:
        source = article.get("source") or {}
        title = str(article.get("title") or "Untitled news trend").strip()
        url = str(article.get("url") or "").strip()
        published_at = self._parse_datetime(article.get("publishedAt"))
        source_name = str(source.get("name") or "NewsAPI").strip()
        trend_score = max(10.0, 100.0 - (index * 8.0))

        return {
            "title": title,
            "name": title,
            "description": str(article.get("description") or article.get("content") or "").strip() or None,
            "source": source_name,
            "source_label": "NEWS",
            "source_uid": f"news:{url or title}",
            "platform": "news",
            "source_type": "newsapi",
            "subreddit": "n/a",
            "url": url,
            "upvotes": 0,
            "comments": 0,
            "trend_score": trend_score,
            "published_at": published_at,
            "created_utc": published_at or datetime.now(timezone.utc),
            "fetched_at": datetime.now(timezone.utc),
            "search_keyword": keyword,
        }

    def _demo_news(self, keyword: str) -> list[dict[str, Any]]:
        now = datetime.now(timezone.utc)
        topics = [
            "AI tools reshape content creation workflows",
            "Creators adopt faster short-form editing stacks",
            "Marketing teams use automation for trend response",
            "Audience behavior shifts toward interactive media",
            "New product launches dominate the social feed",
        ]
        items = []
        for index, title in enumerate(topics):
            items.append(
                {
                    "title": f"{title} ({keyword})" if keyword and keyword != "latest" else title,
                    "name": title,
                    "description": f"Demo news item about {title.lower()}.",
                    "source": "NewsAPI Demo",
                    "source_label": "NEWS",
                    "source_uid": f"news-demo:{keyword}:{index}",
                    "platform": "news",
                    "source_type": "news_demo",
                    "subreddit": "n/a",
                    "url": "https://newsapi.org/",
                    "upvotes": 0,
                    "comments": 0,
                    "trend_score": 100.0 - (index * 8.0),
                    "published_at": now,
                    "created_utc": now,
                    "fetched_at": now,
                    "search_keyword": keyword,
                }
            )
        return items

    def _parse_datetime(self, value: Any):
        if not value:
            return None
        try:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None
