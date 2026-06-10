"""Shared content intelligence helpers for posts, trends, and competitors."""

from __future__ import annotations

import re
import warnings
from collections import Counter
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote_plus
from xml.etree import ElementTree as ET

import requests
from bs4 import BeautifulSoup, MarkupResemblesLocatorWarning
from nltk.corpus import stopwords as nltk_stopwords

STOPWORDS = {
    "a",
    "about",
    "after",
    "again",
    "all",
    "and",
    "are",
    "at",
    "be",
    "because",
    "been",
    "before",
    "but",
    "by",
    "can",
    "could",
    "did",
    "do",
    "does",
    "for",
    "from",
    "get",
    "go",
    "has",
    "have",
    "how",
    "if",
    "in",
    "into",
    "is",
    "it",
    "just",
    "like",
    "more",
    "most",
    "new",
    "not",
    "of",
    "on",
    "or",
    "our",
    "out",
    "over",
    "should",
    "that",
    "the",
    "their",
    "this",
    "to",
    "trend",
    "trends",
    "html",
    "href",
    "nbsp",
    "blank",
    "use",
    "using",
    "was",
    "what",
    "when",
    "why",
    "with",
    "you",
    "your",
}

CUSTOM_STOPWORDS = {
    "nbsp",
    "href",
    "font",
    "blank",
    "https",
    "http",
    "com",
    "rss",
    "google",
    "target",
    "news",
    "feed",
    "html",
    "www",
    "articles",
    "demo",
    "snapshot",
    "region",
    "india",
    "tamil",
    "nadu",
    "chennai",
    "trichy",
    "global",
}

REGION_PROFILES: dict[str, dict[str, Any]] = {
    "global": {
        "label": "Global",
        "geo": "US",
        "country": "US",
        "language": "en-US",
        "queries": ["AI", "startups", "tech", "students"],
        "fallback": [
            "AI jobs",
            "startups",
            "internships",
            "Python",
            "automation",
            "placements",
        ],
    },
    "india": {
        "label": "India",
        "geo": "IN",
        "country": "IN",
        "language": "en-IN",
        "queries": [
            "AI India",
            "startups India",
            "tech India",
            "students India",
            "Python India",
        ],
        "fallback": [
            "AI jobs",
            "startups",
            "internships",
            "Python",
            "automation",
            "placements",
        ],
    },
    "tamil nadu": {
        "label": "Tamil Nadu",
        "geo": "IN",
        "country": "IN",
        "language": "en-IN",
        "queries": [
            "AI Tamil Nadu",
            "tech jobs Tamil Nadu",
            "college students Tamil Nadu",
            "startups Tamil Nadu",
            "internships Tamil Nadu",
        ],
        "fallback": [
            "college projects",
            "placements",
            "AI tools",
            "government jobs",
            "internships",
        ],
    },
    "chennai": {
        "label": "Chennai",
        "geo": "IN",
        "country": "IN",
        "language": "en-IN",
        "queries": [
            "AI Chennai",
            "tech Chennai",
            "startups Chennai",
            "students Chennai",
            "internships Chennai",
        ],
        "fallback": [
            "AI projects",
            "placements",
            "internships",
            "startup news",
            "college projects",
        ],
    },
    "trichy": {
        "label": "Trichy",
        "geo": "IN",
        "country": "IN",
        "language": "en-IN",
        "queries": [
            "Trichy tech",
            "Trichy jobs",
            "Trichy college",
            "AI students Trichy",
            "Python jobs Trichy",
        ],
        "fallback": [
            "MCA projects",
            "internships",
            "campus drive",
            "AI projects",
            "Python jobs",
        ],
    },
}


class InsightTools:
    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "TrendHunterAI/1.0 (+https://trendhunter.local)",
                "Accept": "application/rss+xml,application/xml,text/xml,text/html;q=0.9,*/*;q=0.8",
            }
        )
        self.stopwords = self._load_stopwords()
        self._trend_cache: dict[str, tuple[datetime, dict[str, Any]]] = {}

    def fetch_current_trends(self, region: str = "US", limit: int = 12, niche: str | None = None, platform: str | None = None) -> dict[str, Any]:
        profile = self._region_profile(region)
        queries = self._build_region_queries(profile, niche=niche, platform=platform)
        cache_key = self._cache_key(profile["label"], limit, queries)
        cached = self._trend_cache.get(cache_key)
        if cached:
            cached_at, payload = cached
            if (datetime.now(timezone.utc) - cached_at).total_seconds() < 600:
                return dict(payload)
        feeds: list[tuple[str, str, str]] = []

        if profile.get("geo"):
            feeds.append(
                (
                    "google_trends",
                    f"Google Trends - {profile['label']}",
                    f"https://trends.google.com/trends/trendingsearches/daily/rss?geo={profile['geo']}",
                )
            )

        if profile["key"] == "global":
            feeds.append(("reddit", "Reddit", f"https://www.reddit.com/r/popular/.rss?limit={limit}"))

        for query in queries:
            encoded = quote_plus(query)
            feeds.append(("reddit", f"Reddit - {profile['label']}", f"https://www.reddit.com/search.rss?q={encoded}&sort=new"))
            feeds.append(
                (
                    "news",
                    f"Google News - {profile['label']}",
                    f"https://news.google.com/rss/search?q={encoded}&hl={profile['language']}&gl={profile['country']}&ceid={profile['country']}:en",
                )
            )

        items: list[dict[str, Any]] = []
        for source_type, source_label, feed_url in feeds:
            items.extend(self._fetch_rss_feed(feed_url, source_type=source_type, source_label=source_label))

        if not items:
            items = self._fallback_trends(region=profile["label"])

        seen: set[tuple[str, str]] = set()
        deduped: list[dict[str, Any]] = []
        for item in items:
            title = str(item.get("title") or "").strip()
            url = str(item.get("url") or "").strip()
            key = (title.lower(), url.lower())
            if key in seen:
                continue
            seen.add(key)
            deduped.append(item)
            if len(deduped) >= max(limit * 2, limit):
                break

        normalized: list[dict[str, Any]] = []
        for index, item in enumerate(deduped[:limit], start=1):
            title = str(item.get("title") or "Untitled trend").strip()
            keywords = self.extract_keywords(f"{title} {item.get('description') or ''}")
            source_label = str(item.get("source_label") or item.get("source_type") or item.get("platform") or "Trend").strip()
            normalized.append(
                {
                    **item,
                    "title": title,
                    "name": title,
                    "keywords": keywords,
                    "source_label": source_label,
                    "trend_score": item.get("trend_score") or max(10.0, 100.0 - ((index - 1) * 6.5)),
                    "created_utc": item.get("created_utc") or datetime.now(timezone.utc),
                    "fetched_at": datetime.now(timezone.utc),
                }
            )

        payload = {
            "success": True,
            "count": len(normalized),
            "items": normalized,
            "trend_keywords": self._top_keywords(normalized, limit=10),
            "region": region,
            "region_key": profile["key"],
            "region_label": profile["label"],
            "region_queries": queries,
            "source_labels": sorted({str(item.get("source_label") or item.get("source_type") or item.get("platform") or "Trend") for item in normalized}),
            "demo_mode": all(item.get("source_type", "").endswith("_demo") for item in normalized) if normalized else True,
        }
        self._trend_cache[cache_key] = (datetime.now(timezone.utc), payload)
        return dict(payload)

    def compare_keywords(self, content_text: str, trends: list[dict[str, Any]], region: str | None = None) -> dict[str, Any]:
        content_keywords = self.extract_keywords(content_text)
        trend_keywords = self._top_keywords(trends, limit=10)
        trend_keyword_set = {item["keyword"] for item in trend_keywords}
        content_set = set(content_keywords)

        if not content_set and not trend_keyword_set:
            return {
                "trend_match_score": 0.0,
                "matched_keywords": [],
                "content_keywords": [],
                "trend_keywords": trend_keywords,
            }

        overlap = content_set.intersection(trend_keyword_set)
        denominator = max(len(content_set.union(trend_keyword_set)), 1)
        trend_match_score = round((len(overlap) / denominator) * 100, 1)
        return {
            "trend_match_score": trend_match_score,
            "matched_keywords": sorted(overlap),
            "content_keywords": content_keywords[:12],
            "trend_keywords": trend_keywords[:12],
            "region": self._region_profile(region or "Global")["label"],
        }

    def generate_linkedin_post(self, analysis: dict[str, Any]) -> str:
        title = str(analysis.get("title") or analysis.get("current_request", {}).get("title") or "Untitled idea").strip()
        caption = str(analysis.get("caption") or analysis.get("current_request", {}).get("caption") or "").strip()
        audience = str(analysis.get("audience") or analysis.get("current_request", {}).get("audience") or "professionals").strip()
        platform = str(analysis.get("platform") or analysis.get("current_request", {}).get("platform") or "LinkedIn").strip().title()
        virality = float(analysis.get("virality_score") or analysis.get("analysis", {}).get("virality_score") or 0)
        recommendations = analysis.get("recommendations") or analysis.get("analysis", {}).get("recommendations") or {}
        forecast = analysis.get("forecast") or analysis.get("analysis", {}).get("forecast") or {}
        hashtags = self._normalize_hashtags(
            analysis.get("hashtags")
            or analysis.get("current_request", {}).get("hashtags")
            or analysis.get("analysis", {}).get("normalized_hashtags")
            or []
        )
        if not hashtags:
            hashtags = [self._slug_hashtag(title), "#LinkedIn", "#creator"]

        hook = self._build_hook(title, virality, analysis)
        story = caption or str(recommendations.get("summary") or forecast.get("forecast_explanation") or "I wanted to share the idea behind this workflow and why it matters.").strip()
        stack = self._build_tech_stack(analysis, recommendations, forecast)
        impact = self._build_impact(analysis, recommendations, forecast)

        sections = [
            hook,
            "",
            story,
            "",
            f"Tech stack / workflow: {stack}",
            f"Impact: {impact}",
            "",
            "What do you think? Would you use this approach on your team?",
            "",
            " ".join(hashtags),
            "",
            "LinkedIn: https://www.linkedin.com/in/charuka-p-91578b311",
            "GitHub: https://github.com/charupraba2",
        ]
        return "\n".join(section for section in sections if section is not None).strip()

    def analyze_competitor(self, competitor: str, topic: str | None = None, platform: str | None = None, region: str | None = None) -> dict[str, Any]:
        competitor = (competitor or "").strip()
        topic = (topic or "").strip()
        platform = (platform or "").strip()
        profile = self._region_profile(region or "Global")
        query = topic or competitor
        sample_titles = self._fetch_sample_titles(query=query, region_profile=profile) if query else []
        if not sample_titles:
            sample_titles = self._fallback_titles(competitor=competitor, topic=topic, region_label=profile["label"])

        hook_words = self._common_hook_words(sample_titles)
        style = self._content_style(sample_titles, region_label=profile["label"])
        pattern = self._posting_pattern(sample_titles, region_label=profile["label"])
        themes = self._keyword_themes(sample_titles, competitor=competitor, topic=topic, region_label=profile["label"])
        recommendations = self._strategy_recommendations(style, pattern, themes, hook_words, profile["label"])

        return {
            "success": True,
            "competitor": competitor or topic or "Unknown competitor",
            "topic": topic or competitor or "General",
            "platform": platform or "mixed",
            "platform_label": platform.title() if platform else "Mixed",
            "region": profile["label"],
            "region_key": profile["key"],
            "sample_titles": sample_titles,
            "common_hook_words": hook_words,
            "content_style": style,
            "posting_pattern": pattern,
            "keyword_themes": themes,
            "strategy_recommendations": recommendations,
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }

    def _fetch_rss_feed(self, url: str, source_type: str, source_label: str) -> list[dict[str, Any]]:
        try:
            response = self.session.get(url, timeout=12)
            response.raise_for_status()
        except Exception:
            return []

        try:
            root = ET.fromstring(response.content)
        except Exception:
            return []

        items: list[dict[str, Any]] = []
        for entry in root.findall(".//item"):
            title = self._text(entry, "title")
            if not title:
                continue
            description = self._text(entry, "description") or self._text(entry, "summary")
            link = self._text(entry, "link") or url
            pub_date = self._text(entry, "pubDate") or self._text(entry, "published")
            items.append(
                {
                    "title": title,
                    "description": description,
                    "url": link,
                    "source_label": source_label,
                    "source_type": source_type,
                    "platform": source_type,
                    "subreddit": "n/a",
                    "created_utc": self._parse_date(pub_date) or datetime.now(timezone.utc),
                }
            )
        return items

    def _fetch_sample_titles(self, query: str, region_profile: dict[str, Any] | None = None) -> list[str]:
        encoded = quote_plus(query)
        profile = region_profile or self._region_profile("Global")
        urls = [
            f"https://www.reddit.com/search.rss?q={encoded}&sort=new",
            f"https://news.google.com/rss/search?q={encoded}&hl={profile['language']}&gl={profile['country']}&ceid={profile['country']}:en",
        ]
        titles: list[str] = []
        for url in urls:
            try:
                response = self.session.get(url, timeout=12)
                response.raise_for_status()
                root = ET.fromstring(response.content)
            except Exception:
                continue
            for entry in root.findall(".//item")[:10]:
                title = self._text(entry, "title")
                if title:
                    titles.append(title)
        return titles

    def _fallback_trends(self, region: str) -> list[dict[str, Any]]:
        now = datetime.now(timezone.utc)
        label = str(region or "Global").strip() or "Global"
        lookup_key = label.lower()
        fallback_terms = REGION_PROFILES.get(lookup_key, {}).get("fallback") or REGION_PROFILES["global"]["fallback"]
        items: list[dict[str, Any]] = []
        for index, term in enumerate(fallback_terms, start=1):
            items.append(
                {
                    "title": term,
                    "description": f"Demo trend snapshot for {label}.",
                    "url": "https://example.com",
                    "source_label": f"{label} Demo",
                    "source_type": "demo",
                    "platform": "demo",
                    "subreddit": "n/a",
                    "created_utc": now,
                    "trend_score": max(40.0, 100.0 - ((index - 1) * 8.0)),
                }
            )
        return items

    def _fallback_titles(self, competitor: str, topic: str, region_label: str = "Global") -> list[str]:
        subject = competitor or topic or "creator"
        return [
            f"How {subject} is turning ideas into repeatable content for {region_label}",
            f"The exact {subject} formula that drives more engagement in {region_label}",
            f"Why {subject} is leaning into simple hooks and bigger outcomes",
            f"3 lessons from {subject} that creators in {region_label} can copy this week",
            f"What makes {subject} posts stand out in a crowded feed",
        ]

    def _top_keywords(self, items: list[dict[str, Any]], limit: int = 12) -> list[dict[str, Any]]:
        counter: Counter[str] = Counter()
        for item in items:
            counter.update(self.extract_keywords(f"{item.get('title', '')} {item.get('description', '')}"))
        keywords = [
            {"keyword": keyword, "count": count}
            for keyword, count in counter.items()
            if keyword.isalpha() and len(keyword) > 3
        ]
        keywords.sort(key=lambda item: (-item["count"], item["keyword"]))
        final_keywords = keywords[:limit]
        print("FINAL CLEAN KEYWORDS:", final_keywords)
        return final_keywords

    def extract_keywords(self, text: str) -> list[str]:
        cleaned_text = self._clean_text(text)
        cleaned_text = re.sub(r"http\S+", " ", cleaned_text)
        cleaned_text = re.sub(r"[^a-zA-Z\s]", " ", cleaned_text)
        cleaned_text = cleaned_text.lower()
        tokens = re.findall(r"[a-zA-Z]+", cleaned_text)
        keywords: list[str] = []
        for token in tokens:
            cleaned = token.strip("#").lower()
            if len(cleaned) <= 3 or cleaned in self.stopwords or not cleaned.isalpha():
                continue
            keywords.append(cleaned)
        return list(dict.fromkeys(keywords))

    def _build_hook(self, title: str, virality: float, analysis: dict[str, Any]) -> str:
        if virality >= 75:
            return f"Most people will miss this, but {title} is exactly where the momentum is building."
        if virality >= 45:
            return f"Quick take: {title} is getting strong early signals and deserves attention."
        label = analysis.get("prediction_label") or analysis.get("analysis", {}).get("prediction_label") or "a topic worth tracking"
        return f"I've been tracking {title}, and it looks like {label.lower()} if packaged well."

    def _build_tech_stack(self, analysis: dict[str, Any], recommendations: dict[str, Any], forecast: dict[str, Any]) -> str:
        stack_bits = [
            str(analysis.get("platform") or analysis.get("current_request", {}).get("platform") or "LinkedIn").title(),
            "fast hook",
            "story-led structure",
            "clear CTA",
        ]
        if recommendations.get("tech_stack"):
            stack_bits.append(str(recommendations.get("tech_stack")))
        if forecast.get("recommended_creator_actions"):
            stack_bits.append(str(forecast.get("recommended_creator_actions")[0]))
        return ", ".join(dict.fromkeys(bit for bit in stack_bits if bit))

    def _build_impact(self, analysis: dict[str, Any], recommendations: dict[str, Any], forecast: dict[str, Any]) -> str:
        impact_bits = [
            str(recommendations.get("summary") or forecast.get("forecast_explanation") or "It helps turn attention into a practical workflow.").strip(),
        ]
        if analysis.get("trend_match_score") is not None:
            impact_bits.append(f"Trend match score: {analysis.get('trend_match_score')}%.")
        if forecast.get("why_the_trend_may_grow"):
            impact_bits.append(str(forecast.get("why_the_trend_may_grow")))
        return " ".join(bit for bit in impact_bits if bit).strip()

    def _normalize_hashtags(self, hashtags: Any) -> list[str]:
        if hashtags is None:
            return []
        if isinstance(hashtags, list):
            items = hashtags
        else:
            items = re.split(r"[,\s]+", str(hashtags))
        normalized: list[str] = []
        for item in items:
            if not item:
                continue
            value = str(item).strip()
            if not value:
                continue
            if not value.startswith("#"):
                value = f"#{value.lstrip('#')}"
            normalized.append(value)
        return list(dict.fromkeys(normalized))

    def _slug_hashtag(self, value: str) -> str:
        slug = re.sub(r"[^a-zA-Z0-9]+", "", (value or "").lower())
        return f"#{slug[:24] or 'trending'}"

    def _common_hook_words(self, titles: list[str]) -> list[dict[str, Any]]:
        counter: Counter[str] = Counter()
        for title in titles:
            words = self.extract_keywords(title)
            counter.update(words[:8])
        return [{"word": word, "count": count} for word, count in counter.most_common(8)]

    def _content_style(self, titles: list[str], region_label: str = "Global") -> str:
        lowered = " ".join(titles).lower()
        if any(word in lowered for word in ["how", "guide", "step", "learn", "build"]):
            return f"Educational and instructional for {region_label}"
        if any(word in lowered for word in ["why", "mistake", "truth", "secret", "behind"]):
            return f"Insight-driven and curiosity-led for {region_label}"
        if any(word in lowered for word in ["best", "top", "tools", "templates", "workflow"]):
            return f"List-driven and practical for {region_label}"
        return f"Balanced and topic-focused for {region_label}"

    def _posting_pattern(self, titles: list[str], region_label: str = "Global") -> str:
        count = len(titles)
        if count >= 8:
            return f"High publishing cadence with multiple angle tests in {region_label}"
        if count >= 4:
            return f"Steady cadence with repeatable framing in {region_label}"
        return f"Occasional publishing with selective high-signal posts in {region_label}"

    def _keyword_themes(self, titles: list[str], competitor: str, topic: str, region_label: str = "Global") -> list[dict[str, Any]]:
        counter: Counter[str] = Counter()
        for title in titles:
            counter.update(self.extract_keywords(title))
        for seed in [competitor, topic]:
            counter.update(self.extract_keywords(seed))
        counter.update(self.extract_keywords(region_label))
        return [{"theme": word, "weight": count} for word, count in counter.most_common(10)]

    def _strategy_recommendations(self, style: str, pattern: str, themes: list[dict[str, Any]], hook_words: list[dict[str, Any]], region_label: str = "Global") -> list[str]:
        top_theme = themes[0]["theme"] if themes else "the core topic"
        hook_word = hook_words[0]["word"] if hook_words else "curiosity"
        return [
            f"Lead with {hook_word} in the opening line and anchor the post around {top_theme} for {region_label}.",
            f"Match the observed style by keeping the content {style.lower()}.",
            f"Mirror the posting pattern by testing a {pattern.lower()} rather than a one-off post.",
            "Use one strong proof point, one clear takeaway, and one direct CTA.",
        ]

    def _text(self, entry: ET.Element, name: str) -> str:
        node = entry.find(name)
        if node is not None and node.text:
            return self._clean_text(node.text)
        return ""

    def _cache_key(self, region_label: str, limit: int, queries: list[str]) -> str:
        return f"{region_label.lower()}:{limit}:{'|'.join(sorted(queries))}"

    def _region_profile(self, region: str | None) -> dict[str, Any]:
        normalized = self._normalize_region_key(region)
        return REGION_PROFILES.get(normalized, REGION_PROFILES["global"]) | {"key": normalized}

    def _normalize_region_key(self, region: str | None) -> str:
        if not region:
            return "global"
        value = str(region).strip().lower()
        aliases = {
            "in": "india",
            "india": "india",
            "tamilnadu": "tamil nadu",
            "tamil nadu": "tamil nadu",
            "tn": "tamil nadu",
            "chennai": "chennai",
            "trichy": "trichy",
            "tiruchirappalli": "trichy",
            "global": "global",
            "world": "global",
            "us": "global",
            "usa": "global",
        }
        return aliases.get(value, value if value in REGION_PROFILES else "global")

    def _region_profile(self, region: str) -> dict[str, Any]:
        normalized = self._normalize_region_key(region)
        return REGION_PROFILES.get(normalized, REGION_PROFILES["global"]) | {"key": normalized}

    def _normalize_region_key(self, region: str | None) -> str:
        if not region:
            return "global"
        value = str(region).strip().lower()
        aliases = {
            "in": "india",
            "india": "india",
            "tamilnadu": "tamil nadu",
            "tamil nadu": "tamil nadu",
            "tn": "tamil nadu",
            "chennai": "chennai",
            "trichy": "trichy",
            "tiruchirappalli": "trichy",
            "global": "global",
            "world": "global",
            "usa": "global",
            "us": "global",
        }
        return aliases.get(value, value if value in REGION_PROFILES else "global")

    def _build_region_queries(self, profile: dict[str, Any], niche: str | None = None, platform: str | None = None) -> list[str]:
        queries = [str(query).strip() for query in profile.get("queries", []) if str(query).strip()]
        niche_text = str(niche or "").strip()
        platform_text = str(platform or "").strip()
        if niche_text:
            queries.insert(0, f"{niche_text} {profile['label']}")
        if platform_text:
            queries.insert(0, f"{platform_text} {profile['label']}")
        return list(dict.fromkeys(queries))

    def _parse_date(self, value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            from email.utils import parsedate_to_datetime

            parsed = parsedate_to_datetime(value)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except Exception:
            return None

    def _clean_text(self, value: str | None) -> str:
        if not value:
            return ""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", MarkupResemblesLocatorWarning)
            soup = BeautifulSoup(str(value), "html.parser")
        for tag in soup(["script", "style"]):
            tag.decompose()
        text = soup.get_text(separator=" ")
        return re.sub(r"\s+", " ", text)

    def _load_stopwords(self) -> set[str]:
        stopword_set = set(STOPWORDS)
        try:
            stopword_set.update(nltk_stopwords.words("english"))
        except Exception:
            pass
        stopword_set.update(CUSTOM_STOPWORDS)
        return {word.lower() for word in stopword_set}
