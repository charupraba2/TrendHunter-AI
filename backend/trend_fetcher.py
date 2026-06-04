"""Trend aggregation helpers for Reddit and Google Trends."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from backend.config import settings
from backend.reddit_agent import RedditAgent


class TrendFetcher:
    def __init__(self, reddit_agent: RedditAgent | None = None) -> None:
        self.reddit_agent = reddit_agent or RedditAgent()

    def fetch_reddit_trends(self, limit_per_sort: int = 10) -> list[dict[str, Any]]:
        return self.reddit_agent.fetch_trends(limit_per_sort=limit_per_sort)

    def fetch_google_trends(self, limit: int = 10, geo: str = "IN") -> list[dict[str, Any]]:
        """Fetch trending searches from Google Trends with a safe fallback."""

        try:
            from pytrends.request import TrendReq
        except ImportError:
            return self._demo_google_trends()

        try:
            pytrends = TrendReq(hl=settings.google_trends_hl, tz=settings.google_trends_tz)
            trending = pytrends.trending_searches(pn="india" if geo.upper() == "IN" else geo.lower())
            if trending is None or trending.empty:
                return self._demo_google_trends()

            keywords = trending.iloc[:, 0].astype(str).tolist()[:limit]
            fetched_at = datetime.now(timezone.utc)
            items: list[dict[str, Any]] = []

            for index, keyword in enumerate(keywords, start=1):
                trend_score = max(10.0, float(100 - ((index - 1) * 7)))
                items.append(
                    {
                        "title": keyword,
                        "name": keyword,
                        "platform": "google_trends",
                        "subreddit": "n/a",
                        "url": f"https://trends.google.com/trends/trendingsearches/daily?geo={geo.upper()}",
                        "upvotes": 0,
                        "comments": 0,
                        "trend_score": trend_score,
                        "search_interest": trend_score,
                        "source": "google_trends",
                        "source_type": "google_trending_searches",
                        "created_utc": fetched_at,
                        "fetched_at": fetched_at,
                    }
                )

            return items or self._demo_google_trends()
        except Exception:
            return self._demo_google_trends()

    def fetch_trends(self) -> list[dict[str, Any]]:
        """Return a combined live snapshot from Reddit and Google Trends."""

        reddit_trends = self.fetch_reddit_trends()
        google_trends = self.fetch_google_trends()
        combined = [*reddit_trends, *google_trends]

        normalized: list[dict[str, Any]] = []
        for index, trend in enumerate(combined, start=1):
            title = str(trend.get("title") or trend.get("name") or "Untitled trend").strip()
            subreddit = str(trend.get("subreddit", "unknown")).strip() or "unknown"
            upvotes = int(trend.get("upvotes", 0) or 0)
            comments = int(trend.get("comments", 0) or 0)
            trend_score = trend.get("trend_score")
            if trend_score is None and trend.get("search_interest") is not None:
                trend_score = trend.get("search_interest")

            created_utc = trend.get("created_utc")
            if isinstance(created_utc, datetime):
                created_dt = created_utc
            else:
                created_dt = datetime.utcnow()

            normalized.append(
                {
                    "id": index,
                    "name": title,
                    "title": title,
                    "source": trend.get("source", "mixed"),
                    "source_type": trend.get("source_type", trend.get("sort", "")),
                    "platform": trend.get("platform", "reddit"),
                    "subreddit": subreddit,
                    "category": subreddit if trend.get("platform") == "reddit" else "google_trends",
                    "url": trend.get("url", ""),
                    "upvotes": upvotes,
                    "comments": comments,
                    "trend_score": trend_score,
                    "search_interest": trend.get("search_interest", trend_score),
                    "created_utc": created_dt,
                    "summary": self._build_summary(trend),
                }
            )

        return normalized

    def fetch_hot_topics(self, limit_per_sort: int = 10) -> list[dict[str, Any]]:
        """Backward-compatible alias used by older parts of the app."""

        return self.fetch_reddit_trends(limit_per_sort=limit_per_sort)

    def _demo_google_trends(self) -> list[dict[str, Any]]:
        fetched_at = datetime.now(timezone.utc)
        demo_terms = [
            "AI productivity tools",
            "prompt engineering",
            "short-form video ideas",
            "creator analytics",
            "viral content strategy",
        ]
        return [
            {
                "title": term,
                "name": term,
                "platform": "google_trends",
                "subreddit": "n/a",
                "url": "https://trends.google.com/trends/trendingsearches/daily?geo=IN",
                "upvotes": 0,
                "comments": 0,
                "trend_score": float(100 - (index * 8)),
                "search_interest": float(100 - (index * 8)),
                "source": "google_trends",
                "source_type": "google_demo",
                "created_utc": fetched_at,
                "fetched_at": fetched_at,
            }
            for index, term in enumerate(demo_terms)
        ]

    def _build_summary(self, trend: dict[str, Any]) -> str:
        platform = trend.get("platform", "reddit")
        if platform == "google_trends":
            score = trend.get("trend_score", trend.get("search_interest", 0))
            return f"Trending Google search with a score of {score}."

        subreddit = trend.get("subreddit", "unknown")
        upvotes = trend.get("upvotes", 0)
        comments = trend.get("comments", 0)
        return f"Hot Reddit post from r/{subreddit} with {upvotes} upvotes and {comments} comments."
