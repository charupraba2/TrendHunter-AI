"""YouTube Data API service for live trend collection."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from backend.config import settings

logger = logging.getLogger(__name__)


class YouTubeService:
    def __init__(self) -> None:
        self.api_key = settings.youtube_api_key.strip()
        self._client = self._load_client() if self.api_key else None

    def _load_client(self):
        try:
            from googleapiclient.discovery import build
        except Exception:
            logger.warning("google-api-python-client is not available.")
            return None

        try:
            return build("youtube", "v3", developerKey=self.api_key, cache_discovery=False)
        except Exception as exc:
            logger.warning("YouTube client could not be initialized: %s", exc)
            return None

    def fetch_trending_videos(self, region_code: str = "US", max_results: int = 10) -> list[dict[str, Any]]:
        if self._client is None:
            logger.info("YouTube API key missing or client unavailable. Using demo YouTube trends.")
            return self._demo_videos(region_code)

        try:
            response = (
                self._client.videos()
                .list(
                    part="snippet,statistics",
                    chart="mostPopular",
                    regionCode=region_code,
                    maxResults=max_results,
                )
                .execute()
            )

            if not isinstance(response, dict):
                raise ValueError("YouTube API returned an invalid response payload.")

            items = response.get("items")
            if items is None:
                raise ValueError("YouTube API response is missing the items field.")
            if not items:
                raise ValueError("YouTube API returned an empty items list.")

            normalized = [self._normalize_video(item, region_code) for item in items]
            if normalized:
                logger.info("Fetched %s YouTube trends for region %s with source type %s", len(normalized), region_code, "youtube_api")
                return normalized
            logger.info("YouTube returned no trending videos. Using demo YouTube trends.")
        except Exception as exc:
            logger.warning("YouTube fetch failed for region %s: %s", region_code, exc)
        return self._demo_videos(region_code)

    def _normalize_video(self, item: dict[str, Any], region_code: str) -> dict[str, Any]:
        snippet = item.get("snippet") or {}
        statistics = item.get("statistics") or {}
        video_id = str(item.get("id") or "").strip()
        title = str(snippet.get("title") or "Untitled video trend").strip()
        channel_name = str(snippet.get("channelTitle") or "YouTube").strip()
        published_at = self._parse_datetime(snippet.get("publishedAt"))
        thumbnail = (
            ((snippet.get("thumbnails") or {}).get("high") or {}).get("url")
            or ((snippet.get("thumbnails") or {}).get("default") or {}).get("url")
            or ""
        )
        view_count = self._safe_int(statistics.get("viewCount"))
        trend_score = max(20.0, min(100.0, (view_count / 1_000_000) * 100 if view_count else 70.0))

        return {
            "title": title,
            "name": title,
            "description": str(snippet.get("description") or "").strip() or None,
            "source": channel_name,
            "source_label": "YOUTUBE",
            "source_uid": f"youtube:{video_id or title}",
            "platform": "youtube",
            "source_type": "youtube_api",
            "subreddit": "n/a",
            "channel_name": channel_name,
            "view_count": view_count,
            "thumbnail": thumbnail,
            "url": f"https://www.youtube.com/watch?v={video_id}" if video_id else "https://www.youtube.com/",
            "upvotes": 0,
            "comments": 0,
            "trend_score": trend_score,
            "published_at": published_at,
            "created_utc": published_at or datetime.now(timezone.utc),
            "fetched_at": datetime.now(timezone.utc),
            "region_code": region_code,
        }

    def _demo_videos(self, region_code: str) -> list[dict[str, Any]]:
        now = datetime.now(timezone.utc)
        topics = [
            ("AI trend videos dominate recommendations", "TrendHunter AI", 1820000),
            ("How creators use short-form video to grow fast", "Creator Lab", 1490000),
            ("YouTube analytics hacks for 2026", "Growth Studio", 1180000),
            ("Best AI editing workflows for content teams", "Video Forge", 980000),
            ("Trending video ideas for tech audiences", "Creator Stack", 865000),
        ]
        items = []
        for index, (title, channel_name, views) in enumerate(topics):
            items.append(
                {
                    "title": title,
                    "name": title,
                    "description": f"Demo YouTube video about {title.lower()}.",
                    "source": channel_name,
                    "source_label": "YOUTUBE",
                    "source_uid": f"youtube-demo:{region_code}:{index}",
                    "platform": "youtube",
                    "source_type": "youtube_demo",
                    "subreddit": "n/a",
                    "channel_name": channel_name,
                    "view_count": views,
                    "thumbnail": "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg",
                    "url": "https://www.youtube.com/",
                    "upvotes": 0,
                    "comments": 0,
                    "trend_score": 100.0 - (index * 7.5),
                    "published_at": now,
                    "created_utc": now,
                    "fetched_at": now,
                    "region_code": region_code,
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

    def _safe_int(self, value: Any) -> int:
        try:
            return int(value or 0)
        except (TypeError, ValueError):
            return 0
