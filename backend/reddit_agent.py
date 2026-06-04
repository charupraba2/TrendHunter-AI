"""Reddit trend collection using PRAW with a demo fallback."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from backend.config import settings

SUBREDDITS = [
    "technology",
    "artificial",
    "MachineLearning",
    "ChatGPT",
    "socialmedia",
    "YouTubers",
]


@dataclass
class RedditTrend:
    title: str
    subreddit: str
    url: str
    upvotes: int
    comments: int
    created_utc: datetime
    source: str = "reddit"
    sort: str = "hot"

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "subreddit": self.subreddit,
            "url": self.url,
            "upvotes": self.upvotes,
            "comments": self.comments,
            "created_utc": self.created_utc,
            "source": self.source,
            "platform": "reddit",
            "sort": self.sort,
        }


class RedditAgent:
    def __init__(self) -> None:
        self.client_id = settings.reddit_client_id
        self.client_secret = settings.reddit_client_secret
        self.user_agent = settings.reddit_user_agent

    def has_credentials(self) -> bool:
        return bool(self.client_id and self.client_secret and self.user_agent)

    def _get_reddit_client(self):
        try:
            import praw
        except ImportError as exc:  # pragma: no cover - dependency issue
            raise RuntimeError(
                "PRAW is not installed. Install dependencies with pip install -r requirements.txt."
            ) from exc

        if not self.has_credentials():
            return None

        try:
            return praw.Reddit(
                client_id=self.client_id,
                client_secret=self.client_secret,
                user_agent=self.user_agent,
            )
        except Exception as exc:
            raise RuntimeError(f"Failed to initialize Reddit client: {exc}") from exc

    def _demo_trends(self) -> list[dict[str, Any]]:
        now = datetime.now(timezone.utc)
        demo_posts = [
            ("AI video editing workflows are exploding", "technology", "hot", 18420, 612),
            ("Best prompts for creators this week", "ChatGPT", "hot", 13870, 481),
            ("Rising machine learning tools for solo builders", "MachineLearning", "rising", 9620, 245),
            ("What social media trends will dominate next month?", "socialmedia", "rising", 7420, 198),
            ("YouTubers are shifting to short-form again", "YouTubers", "hot", 11950, 407),
        ]
        return [
            {
                "title": title,
                "subreddit": subreddit,
                "url": f"https://www.reddit.com/r/{subreddit.lower()}/",
                "upvotes": upvotes,
                "comments": comments,
                "created_utc": now,
                "source": "reddit",
                "platform": "reddit",
                "sort": sort,
            }
            for title, subreddit, sort, upvotes, comments in demo_posts
        ]

    def _convert_submission(self, submission, sort: str) -> dict[str, Any]:
        created = getattr(submission, "created_utc", None)
        created_dt = datetime.fromtimestamp(created, tz=timezone.utc) if created else datetime.now(timezone.utc)
        return {
            "title": getattr(submission, "title", "").strip(),
            "subreddit": str(getattr(submission, "subreddit", "unknown")),
            "url": getattr(submission, "url", ""),
            "upvotes": int(getattr(submission, "ups", 0) or 0),
            "comments": int(getattr(submission, "num_comments", 0) or 0),
            "created_utc": created_dt,
            "source": "reddit",
            "platform": "reddit",
            "sort": sort,
        }

    def fetch_trends(self, limit_per_sort: int = 10) -> list[dict[str, Any]]:
        """Fetch hot and rising Reddit posts from configured subreddits."""

        if not self.has_credentials():
            return self._demo_trends()

        reddit = self._get_reddit_client()
        if reddit is None:
            return self._demo_trends()

        trends: list[dict[str, Any]] = []
        try:
            for subreddit_name in SUBREDDITS:
                subreddit = reddit.subreddit(subreddit_name)

                for submission in subreddit.hot(limit=limit_per_sort):
                    trends.append(self._convert_submission(submission, "hot"))

                for submission in subreddit.rising(limit=limit_per_sort):
                    trends.append(self._convert_submission(submission, "rising"))

            return trends
        except Exception as exc:
            raise RuntimeError(f"Failed to fetch Reddit trends: {exc}") from exc

    def fetch_hot_topics(self, limit_per_sort: int = 10) -> list[dict[str, Any]]:
        """Backward-compatible alias used by older parts of the app."""

        return self.fetch_trends(limit_per_sort=limit_per_sort)
