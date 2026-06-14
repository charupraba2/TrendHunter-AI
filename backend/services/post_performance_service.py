"""Post performance intelligence for tracked published content."""

from __future__ import annotations

import hashlib
import logging
import math
import random
import re
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from typing import Any
from urllib.parse import urlparse

from backend.database import get_all_trends, get_post_performance_by_url, get_post_performance_records

logger = logging.getLogger(__name__)


class PostPerformanceService:
    """Analyze published post performance from user-entered engagement metrics."""

    PLATFORM_HINTS = {
        "linkedin.com": "linkedin",
        "www.linkedin.com": "linkedin",
        "instagram.com": "instagram",
        "www.instagram.com": "instagram",
        "youtube.com": "youtube",
        "youtu.be": "youtube",
        "twitter.com": "twitter",
        "x.com": "twitter",
    }

    PLATFORM_LABELS = {
        "linkedin": "LinkedIn",
        "instagram": "Instagram",
        "youtube": "YouTube",
        "twitter": "Twitter/X",
        "x": "Twitter/X",
    }

    def _coerce_int(self, value: Any) -> int:
        try:
            if value is None or value == "":
                return 0
            return max(0, int(float(value)))
        except (TypeError, ValueError):
            return 0

    def _parse_post_age_minutes(self, post_age: str | None) -> int:
        label = str(post_age or "2 hours").strip().lower()
        known = {
            "30 mins": 30,
            "1 hour": 60,
            "2 hours": 120,
            "6 hours": 360,
            "24 hours": 1440,
        }
        if label in known:
            return known[label]
        match = re.search(r"(\d+(?:\.\d+)?)\s*(min|mins|minute|minutes|hour|hours|hr|hrs|day|days)", label)
        if not match:
            return 120
        value = float(match.group(1))
        unit = match.group(2)
        if unit.startswith("day"):
            return int(value * 1440)
        if unit.startswith("hour") or unit.startswith("hr"):
            return int(value * 60)
        return int(value)

    def _estimate_impressions(self, likes: int, comments: int, shares: int, platform: str, region: str, age_hours: float) -> int:
        base = (likes * 11.0) + (comments * 18.0) + (shares * 26.0)
        platform_multiplier = {
            "linkedin": 1.18,
            "instagram": 1.28,
            "youtube": 1.22,
            "twitter": 1.12,
        }.get(platform, 1.0)
        region_multiplier = 1.1 if region.lower() in {"india", "tamil nadu", "chennai", "trichy"} and platform == "linkedin" else 1.0
        age_multiplier = 1.0 + min(0.45, max(0.0, age_hours) / 48.0)
        estimate = int(max(likes + comments + shares, base * platform_multiplier * region_multiplier * age_multiplier))
        return estimate

    def _engagement_total(self, likes: int, comments: int, shares: int) -> int:
        return max(0, likes + (comments * 2) + (shares * 3))

    def _platform_expected_velocity(self, platform: str, region: str) -> float:
        base = {
            "linkedin": 38.0,
            "instagram": 58.0,
            "youtube": 32.0,
            "twitter": 42.0,
        }.get(platform, 40.0)
        if region.lower() in {"india", "tamil nadu", "chennai", "trichy"} and platform == "linkedin":
            base *= 0.92
        return base

    def _build_manual_profile(
        self,
        likes: int,
        comments: int,
        shares: int,
        impressions: int | None,
        post_age: str,
        platform: str,
        region: str,
        trend_relevance: float,
        previous: dict[str, Any] | None,
    ) -> dict[str, Any]:
        age_minutes = self._parse_post_age_minutes(post_age)
        age_hours = max(0.5, age_minutes / 60.0)
        actual_impressions = self._coerce_int(impressions)
        estimated_impressions = actual_impressions or self._estimate_impressions(likes, comments, shares, platform, region, age_hours)
        total_engagement = self._engagement_total(likes, comments, shares)
        engagement_rate = (total_engagement / max(1, estimated_impressions)) * 100.0
        comment_ratio = comments / max(1, likes)
        share_ratio = shares / max(1, comments or 1)
        share_weight = shares / max(1, likes)
        engagement_quality = self._clamp(
            (engagement_rate * 1.6)
            + (comment_ratio * 24.0)
            + (share_weight * 35.0)
            + (trend_relevance * 0.18),
            0.0,
            100.0,
        )
        velocity_baseline = self._platform_expected_velocity(platform, region)
        engagement_velocity = self._clamp((total_engagement / age_hours) / max(1.0, velocity_baseline) * 100.0, 0.0, 100.0)

        previous_total = 0
        historical_growth = 0.0
        if previous:
            previous_total = self._engagement_total(
                self._coerce_int(previous.get("likes")),
                self._coerce_int(previous.get("comments")),
                self._coerce_int(previous.get("shares")),
            )
            previous_age_hours = max(0.5, self._elapsed_hours(previous.get("last_tracked_at")) or age_hours)
            delta = total_engagement - previous_total
            delta_rate = (delta / max(1, previous_total)) * 100.0
            historical_growth = self._clamp(50.0 + (delta_rate / max(0.5, previous_age_hours)), 0.0, 100.0)

        growth_speed = self._clamp(
            (engagement_velocity * 0.52)
            + (engagement_quality * 0.28)
            + (trend_relevance * 0.15)
            + (historical_growth * 0.05),
            0.0,
            100.0,
        )
        virality_momentum = self._clamp(
            (engagement_quality * 0.30)
            + (engagement_velocity * 0.30)
            + (growth_speed * 0.22)
            + (trend_relevance * 0.18),
            0.0,
            100.0,
        )
        trend_strength = self._clamp(
            (trend_relevance * 0.45)
            + (engagement_quality * 0.22)
            + (engagement_velocity * 0.20)
            + (share_ratio * 12.0),
            0.0,
            100.0,
        )
        saturation_risk = self._clamp(
            (age_hours * 2.4)
            + (100.0 - virality_momentum) * 0.38
            + max(0.0, 24.0 - share_ratio * 30.0)
            - (trend_relevance * 0.12),
            0.0,
            100.0,
        )
        algorithm_pickup_probability = self._clamp(
            (virality_momentum * 0.45)
            + (engagement_quality * 0.22)
            + (trend_relevance * 0.18)
            + ((100.0 - saturation_risk) * 0.15),
            0.0,
            100.0,
        )
        engagement_growth = self._clamp(
            (growth_speed * 0.64)
            + (engagement_quality * 0.21)
            + (trend_relevance * 0.15)
            - (saturation_risk * 0.12),
            0.0,
            100.0,
        )
        reach = max(estimated_impressions, int(total_engagement * (4.2 + (trend_relevance / 100.0))))

        return {
            "likes": likes,
            "comments": comments,
            "shares": shares,
            "reach": reach,
            "impressions": estimated_impressions,
            "engagement_growth": engagement_growth,
            "virality_momentum": virality_momentum,
            "growth_speed": growth_speed,
            "trend_strength": trend_strength,
            "engagement_velocity": engagement_velocity,
            "engagement_quality": engagement_quality,
            "algorithm_pickup_probability": algorithm_pickup_probability,
            "saturation_risk": saturation_risk,
            "age_minutes": age_minutes,
            "age_hours": age_hours,
            "historical_growth": historical_growth,
        }

    def _classify_lifecycle_manual(self, profile: dict[str, Any]) -> str:
        momentum = self._safe_number(profile.get("virality_momentum"))
        growth_speed = self._safe_number(profile.get("growth_speed"))
        engagement_velocity = self._safe_number(profile.get("engagement_velocity"))
        saturation_risk = self._safe_number(profile.get("saturation_risk"))
        age_hours = self._safe_number(profile.get("age_hours"))
        share_ratio = self._safe_number(profile.get("shares")) / max(1.0, self._safe_number(profile.get("comments")))

        if momentum >= 82 and growth_speed >= 65 and engagement_velocity >= 60 and age_hours <= 6:
            return "Rising"
        if momentum >= 76 and growth_speed >= 58 and age_hours <= 12:
            return "Peaking"
        if age_hours >= 24 and momentum < 50:
            return "Declining"
        if saturation_risk >= 60 or (age_hours >= 6 and share_ratio < 0.35 and engagement_velocity < 50):
            return "Saturated"
        if momentum >= 50 and growth_speed >= 40:
            return "Stable"
        return "Declining"

    def _comment_reply_urgency(self, lifecycle_stage: str, comments: int, age_hours: float) -> str:
        if comments >= 10 and age_hours <= 6:
            return "High"
        if lifecycle_stage in {"Rising", "Peaking"}:
            return "High"
        if lifecycle_stage == "Stable":
            return "Medium"
        return "Low"

    def track_post_performance(
        self,
        post_url: str,
        region: str = "India",
        platform: str = "",
        user_id: int | None = None,
        manual_metrics: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        post_url = (post_url or "").strip()
        if not post_url:
            raise ValueError("publishedPostUrl is required")

        resolved_platform = self._detect_platform(post_url, platform)
        region_label = (region or "India").strip() or "India"
        title_guess = self._infer_title_from_url(post_url)
        previous = get_post_performance_by_url(post_url, user_id=user_id)
        current_trends = get_all_trends(limit=250)
        trend_relevance = self._trend_relevance(title_guess, resolved_platform, region_label, current_trends)
        metrics = manual_metrics or {}
        likes = self._coerce_int(metrics.get("likes"))
        comments = self._coerce_int(metrics.get("comments"))
        shares = self._coerce_int(metrics.get("shares"))
        impressions = metrics.get("impressions")
        post_age = str(metrics.get("post_age") or "2 hours")

        if likes <= 0 and comments <= 0 and shares <= 0:
            raise ValueError("Manual likes, comments, and shares are required.")

        profile = self._build_manual_profile(
            likes=likes,
            comments=comments,
            shares=shares,
            impressions=impressions,
            post_age=post_age,
            platform=resolved_platform,
            region=region_label,
            trend_relevance=trend_relevance,
            previous=previous,
        )

        lifecycle_stage = self._classify_lifecycle_manual(profile)
        momentum = profile["virality_momentum"]
        growth_speed = profile["growth_speed"]
        trend_strength = profile["trend_strength"]
        engagement_velocity = profile["engagement_velocity"]
        engagement_decay = self._engagement_decay(momentum, growth_speed, lifecycle_stage)

        recommendations = self._recommendations(
            platform=resolved_platform,
            region=region_label,
            title_guess=title_guess,
            lifecycle_stage=lifecycle_stage,
            momentum=momentum,
            growth_speed=growth_speed,
            trend_strength=trend_strength,
            engagement_velocity=engagement_velocity,
            engagement_decay=engagement_decay,
            profile=profile,
        )
        recommendations["comment_reply_urgency"] = self._comment_reply_urgency(lifecycle_stage, comments, profile["age_hours"])
        recommendations["engagement_recommendation"] = self._recommendation_line(
            resolved_platform,
            region_label,
            lifecycle_stage,
            engagement_velocity >= 55,
        )
        recommendations["platform_tip"] = self._platform_recommendation(resolved_platform)
        recommendations["algorithm_pickup_probability"] = round(profile["algorithm_pickup_probability"], 2)
        recommendations["saturation_risk"] = round(profile["saturation_risk"], 2)

        forecast = self._forecast(
            platform=resolved_platform,
            region=region_label,
            lifecycle_stage=lifecycle_stage,
            momentum=momentum,
            growth_speed=growth_speed,
            engagement_velocity=engagement_velocity,
            trend_strength=trend_strength,
            engagement_decay=engagement_decay,
            profile=profile,
        )
        forecast["expected_engagement_growth"] = round(profile["engagement_growth"], 2)
        forecast["peak_engagement_window"] = forecast["peak_engagement_time"]

        chart_data = self._build_chart_data(profile, lifecycle_stage, momentum, growth_speed, engagement_decay)
        summary = self._summary(title_guess, resolved_platform, region_label, lifecycle_stage, momentum, trend_relevance)

        performance = {
            "post_url": post_url,
            "content_title": title_guess,
            "platform": resolved_platform,
            "platform_label": self.PLATFORM_LABELS.get(resolved_platform, resolved_platform.title()),
            "region": region_label,
            "source_label": self.PLATFORM_LABELS.get(resolved_platform, resolved_platform.title()),
            "likes": profile["likes"],
            "comments": profile["comments"],
            "shares": profile["shares"],
            "reach": profile["reach"],
            "impressions": profile["impressions"],
            "engagement_growth": round(profile["engagement_growth"], 2),
            "virality_momentum": round(momentum, 2),
            "growth_speed": round(growth_speed, 2),
            "trend_strength": round(trend_strength, 2),
            "engagement_velocity": round(engagement_velocity, 2),
            "engagement_quality": round(profile["engagement_quality"], 2),
            "trend_relevance": round(trend_relevance, 2),
            "virality_score": round(momentum, 2),
            "engagement_probability": round(profile["algorithm_pickup_probability"], 2),
            "forecast_confidence": round(forecast["forecast_confidence_score"], 2),
            "growth_status": forecast["growth_status"],
            "viral_probability": round(forecast["viral_probability"], 2),
            "trend_momentum_score": round(forecast["trend_momentum_score"], 2),
            "algorithm_pickup_probability": round(profile["algorithm_pickup_probability"], 2),
            "saturation_risk": round(profile["saturation_risk"], 2),
            "post_age": post_age,
            "post_age_minutes": profile["age_minutes"],
            "lifecycle_stage": lifecycle_stage,
            "should_repost": recommendations["should_repost"],
            "should_improve_hook": recommendations["should_improve_hook"],
            "should_shorten_caption": recommendations["should_shorten_caption"],
            "should_follow_up": recommendations["should_follow_up"],
            "is_saturated": lifecycle_stage == "Saturated",
            "expected_reach": forecast["expected_reach"],
            "expected_impressions": forecast["expected_impressions"],
            "peak_engagement_time": forecast["peak_engagement_time"],
            "engagement_decay": round(engagement_decay, 2),
            "live_metrics_available": False,
            "summary": summary,
            "analysis_notes": self._analysis_notes(lifecycle_stage, momentum, trend_relevance, region_label, resolved_platform),
            "post_age_label": post_age,
            "trend_lifecycle": lifecycle_stage,
            "momentum_score": round(momentum, 2),
            "trend_strength_score": round(trend_strength, 2),
            "recommendation": recommendations.get("engagement_recommendation"),
        }

        payload = {
            "post_url": post_url,
            "content_title": title_guess,
            "platform": resolved_platform,
            "platform_label": performance["platform_label"],
            "region": region_label,
            "source_label": performance["source_label"],
            "live_metrics_available": False,
            "manual_metrics": {
                "likes": likes,
                "comments": comments,
                "shares": shares,
                "impressions": self._coerce_int(impressions) or profile["impressions"],
                "post_age": post_age,
            },
        }

        logger.info(
            "Post performance tracked: platform=%s region=%s stage=%s likes=%s comments=%s shares=%s",
            resolved_platform,
            region_label,
            lifecycle_stage,
            likes,
            comments,
            shares,
        )

        return {
            "success": True,
            "current_post": payload,
            "performance": performance,
            "analysis": performance,
            "recommendations": recommendations,
            "forecast": forecast,
            "chart_data": chart_data,
            "history": self._history_snapshot(previous, profile, lifecycle_stage, recommendations, forecast),
            "demo_mode": False,
            "manual_mode": True,
            "momentum_score": round(momentum, 2),
            "lifecycle_stage": lifecycle_stage,
            "trend_relevance": round(trend_relevance, 2),
            "algorithm_pickup_probability": round(profile["algorithm_pickup_probability"], 2),
            "saturation_risk": round(profile["saturation_risk"], 2),
            "recommendation": recommendations.get("engagement_recommendation"),
        }

    def _detect_platform(self, post_url: str, platform_hint: str = "") -> str:
        hint = (platform_hint or "").strip().lower()
        if hint in self.PLATFORM_LABELS:
            return hint
        domain = urlparse(post_url).netloc.lower()
        for token, resolved in self.PLATFORM_HINTS.items():
            if token in domain:
                return resolved
        return "linkedin"

    def _infer_title_from_url(self, post_url: str) -> str:
        parsed = urlparse(post_url)
        slug = "/".join(part for part in parsed.path.split("/") if part)
        slug = re.sub(r"[-_]+", " ", slug).strip()
        slug = re.sub(r"\s+", " ", slug)
        if not slug:
            slug = "published post"
        return slug[:80].strip().title()

    def _seed_value(self, post_url: str, region: str, platform: str) -> int:
        value = f"{post_url}|{region}|{platform}".encode("utf-8")
        return int(hashlib.sha256(value).hexdigest()[:16], 16)

    def _build_base_profile(
        self,
        rng: random.Random,
        platform: str,
        title_guess: str,
        trend_relevance: float,
        platform_boost: float,
        region_boost: float,
    ) -> dict[str, float | int]:
        topic_strength = 0.65 + (trend_relevance / 300.0)
        base_reach = int((1200 + rng.randint(200, 2400)) * platform_boost * region_boost * (0.9 + topic_strength))
        likes = int(base_reach * rng.uniform(0.025, 0.075) * platform_boost)
        comments = int(max(3, base_reach * rng.uniform(0.003, 0.013)))
        shares = int(max(1, base_reach * rng.uniform(0.0015, 0.009)))
        impressions = int(base_reach * rng.uniform(1.18, 1.75))
        engagement_velocity = self._clamp(((likes + comments + shares) / max(1, impressions)) * 120.0, 0.0, 100.0)
        growth_speed = self._clamp((trend_relevance * 0.38) + (platform_boost * 18.0) + rng.uniform(10.0, 28.0), 0.0, 100.0)
        engagement_growth = self._clamp((growth_speed * 0.45) + rng.uniform(4.0, 18.0), -20.0, 100.0)
        virality_momentum = self._clamp((trend_relevance * 0.42) + (growth_speed * 0.28) + (engagement_velocity * 0.18) + (platform_boost * 10.0), 0.0, 100.0)
        trend_strength = self._clamp((trend_relevance * 0.55) + (platform_boost * 12.0) + (region_boost * 10.0) + (engagement_velocity * 0.14), 0.0, 100.0)
        return {
            "likes": likes,
            "comments": comments,
            "shares": shares,
            "reach": max(base_reach, likes + comments + shares),
            "impressions": max(impressions, base_reach),
            "engagement_growth": engagement_growth,
            "virality_momentum": virality_momentum,
            "growth_speed": growth_speed,
            "trend_strength": trend_strength,
            "engagement_velocity": engagement_velocity,
        }

    def _apply_growth(
        self,
        base_profile: dict[str, Any],
        previous: dict[str, Any],
        growth_factor: float,
        rng: random.Random,
    ) -> dict[str, Any]:
        previous_total = max(1, int(previous.get("likes", 0)) + int(previous.get("comments", 0)) + int(previous.get("shares", 0)))
        next_reach = int(max(base_profile["reach"], previous.get("reach", 0) * growth_factor))
        next_impressions = int(max(base_profile["impressions"], previous.get("impressions", 0) * growth_factor))
        likes = int(max(base_profile["likes"], previous.get("likes", 0) * (growth_factor + rng.uniform(0.02, 0.08))))
        comments = int(max(base_profile["comments"], previous.get("comments", 0) * (growth_factor + rng.uniform(0.015, 0.05))))
        shares = int(max(base_profile["shares"], previous.get("shares", 0) * (growth_factor + rng.uniform(0.02, 0.06))))
        current_total = max(1, likes + comments + shares)
        engagement_growth = ((current_total - previous_total) / previous_total) * 100.0
        engagement_velocity = self._clamp((current_total / max(1, next_impressions)) * 120.0, 0.0, 100.0)
        growth_speed = self._clamp(base_profile["growth_speed"] + (growth_factor - 1.0) * 28.0, 0.0, 100.0)
        virality_momentum = self._clamp(base_profile["virality_momentum"] + (engagement_growth * 0.25) + (growth_speed * 0.12), 0.0, 100.0)
        trend_strength = self._clamp(base_profile["trend_strength"] + (engagement_velocity * 0.18), 0.0, 100.0)
        return {
            "likes": likes,
            "comments": comments,
            "shares": shares,
            "reach": next_reach,
            "impressions": next_impressions,
            "engagement_growth": engagement_growth,
            "virality_momentum": virality_momentum,
            "growth_speed": growth_speed,
            "trend_strength": trend_strength,
            "engagement_velocity": engagement_velocity,
        }

    def _growth_factor(
        self,
        previous: dict[str, Any],
        elapsed_hours: float,
        trend_relevance: float,
        platform_boost: float,
        region_boost: float,
    ) -> float:
        previous_stage = str(previous.get("lifecycle_stage") or "Stable").lower()
        base = 1.0 + min(0.18, elapsed_hours * 0.008)
        relevance_lift = trend_relevance / 220.0
        platform_lift = (platform_boost - 1.0) * 0.55
        region_lift = (region_boost - 1.0) * 0.45

        if previous_stage == "rising":
            base += 0.10
        elif previous_stage == "peaking":
            base += 0.04
        elif previous_stage == "saturated":
            base -= 0.03
        elif previous_stage == "declining":
            base -= 0.10

        return max(0.75, min(1.35, base + relevance_lift + platform_lift + region_lift))

    def _classify_lifecycle(self, profile: dict[str, Any], trend_relevance: float) -> str:
        momentum = self._safe_number(profile.get("virality_momentum"))
        growth_speed = self._safe_number(profile.get("growth_speed"))
        engagement_velocity = self._safe_number(profile.get("engagement_velocity"))
        growth = self._safe_number(profile.get("engagement_growth"))
        trend_strength = self._safe_number(profile.get("trend_strength"))

        if momentum >= 80 and growth_speed >= 68 and engagement_velocity >= 58:
            return "Rising"
        if momentum >= 78 and growth_speed >= 60 and trend_strength >= 70 and growth >= 10:
            return "Peaking"
        if trend_strength >= 62 and growth_speed >= 45 and engagement_velocity >= 40:
            return "Stable"
        if trend_relevance < 35 and growth_speed < 45 and engagement_velocity < 35:
            return "Declining"
        if momentum >= 58 and growth_speed < 48:
            return "Saturated"
        return "Stable"

    def _recommendations(
        self,
        platform: str,
        region: str,
        title_guess: str,
        lifecycle_stage: str,
        momentum: float,
        growth_speed: float,
        trend_strength: float,
        engagement_velocity: float,
        engagement_decay: float,
        profile: dict[str, Any],
    ) -> dict[str, Any]:
        high_engagement = engagement_velocity >= 55
        should_repost = lifecycle_stage in {"Rising", "Peaking"} and momentum >= 70
        should_improve_hook = lifecycle_stage in {"Stable", "Saturated", "Declining"} or growth_speed < 55
        should_shorten_caption = platform in {"instagram", "twitter"} or safe_len(title_guess) > 70
        should_follow_up = lifecycle_stage in {"Rising", "Peaking", "Stable"} and trend_strength >= 60
        best_next_content = self._best_next_content(platform, lifecycle_stage, title_guess, region)

        recommendations = [
            self._recommendation_line(platform, region, lifecycle_stage, high_engagement),
            f"Virality momentum is {momentum:.0f}/100, so the post is currently {lifecycle_stage.lower()}.",
            f"Trend strength is {trend_strength:.0f}/100 and engagement velocity is {engagement_velocity:.0f}/100.",
            best_next_content,
        ]
        if lifecycle_stage in {"Rising", "Peaking"}:
            recommendations.append("Reply to comments quickly to keep the first-hour signal strong.")
        if lifecycle_stage in {"Declining", "Saturated"}:
            recommendations.append("Create a follow-up angle within 24 hours to revive attention.")

        return {
            "should_repost": should_repost,
            "should_improve_hook": should_improve_hook,
            "should_shorten_caption": should_shorten_caption,
            "should_follow_up": should_follow_up,
            "best_next_content": best_next_content,
            "recommendation_cards": recommendations,
            "ai_recommendations": {
                "repost_advice": "Yes, repost with a stronger hook." if should_repost else "Wait and refine before reposting.",
                "hook_advice": "Improve the hook with a clearer promise and outcome." if should_improve_hook else "The hook is strong enough to keep testing.",
                "caption_advice": "Shorten the caption and move the key promise higher." if should_shorten_caption else "Caption length is acceptable for this platform.",
                "trend_saturation": "This topic looks saturated." if lifecycle_stage == "Saturated" else "The topic still has room to grow.",
                "follow_up_advice": "Create Part 2 within the next 24 hours." if should_follow_up else "A follow-up is optional, not urgent.",
                "next_action": best_next_content,
            },
        }

    def _best_next_content(self, platform: str, lifecycle_stage: str, title_guess: str, region: str) -> str:
        if platform == "linkedin":
            return f"Publish a thoughtful follow-up post for {region} and add a quick comment reply strategy."
        if platform == "instagram":
            return f"Turn {title_guess} into a short reel sequel with a sharper opening hook."
        if platform == "youtube":
            return f"Create a short follow-up video or pinned comment update for {title_guess}."
        if platform == "twitter":
            return f"Build a thread follow-up and pin the strongest reply to keep engagement moving."
        return f"Create Part 2 for {title_guess} and keep the format easy to scan."

    def _forecast(
        self,
        platform: str,
        region: str,
        lifecycle_stage: str,
        momentum: float,
        growth_speed: float,
        engagement_velocity: float,
        trend_strength: float,
        engagement_decay: float,
        profile: dict[str, Any],
    ) -> dict[str, Any]:
        base_reach = max(1.0, self._safe_number(profile.get("reach")))
        base_likes = max(1.0, self._safe_number(profile.get("likes")))
        base_comments = max(0.0, self._safe_number(profile.get("comments")))
        base_shares = max(0.0, self._safe_number(profile.get("shares")))
        age_hours = max(0.5, self._safe_number(profile.get("age_hours")) or 0.5)
        engagement_quality = self._safe_number(profile.get("engagement_quality"))
        algorithm_pickup_probability = self._safe_number(profile.get("algorithm_pickup_probability"))
        saturation_risk = self._safe_number(profile.get("saturation_risk"))

        viral_probability = self._clamp(
            (algorithm_pickup_probability * 0.68)
            + (trend_strength * 0.18)
            + (momentum * 0.08)
            + ((100.0 - engagement_decay) * 0.06),
            0.0,
            100.0,
        )
        trend_momentum_score = self._clamp(
            (momentum * 0.52)
            + (growth_speed * 0.18)
            + (engagement_velocity * 0.18)
            + (trend_strength * 0.12),
            0.0,
            100.0,
        )
        forecast_confidence = self._clamp(
            45.0
            + (viral_probability * 0.22)
            + (engagement_quality * 0.14)
            + (trend_strength * 0.10)
            - (saturation_risk * 0.10)
            - min(age_hours, 48.0) * 0.18,
            35.0,
            98.0,
        )
        base_growth = self._clamp(
            ((momentum * 0.32) + (growth_speed * 0.22) + (engagement_velocity * 0.16) + (engagement_quality * 0.18) + (trend_strength * 0.12)) / 100.0,
            0.0,
            0.28,
        )
        decay_drag = self._clamp((engagement_decay / 260.0) + (age_hours / 120.0) + (saturation_risk / 420.0), 0.02, 0.38)
        net_growth = self._clamp(base_growth - decay_drag, -0.16, 0.24)

        window_hours = [1, 6, 24, 168]
        window_labels = ["Next 1 Hour", "Next 6 Hours", "Next 24 Hours", "Next 7 Days"]
        likes_forecast: dict[str, int] = {}
        reach_forecast: dict[str, int] = {}
        engagement_forecast: dict[str, int] = {}
        timeline_likes: list[int] = []
        timeline_reach: list[int] = []
        timeline_engagement: list[int] = []

        for hours, label in zip(window_hours, window_labels):
            window_scale = 0.28 + (math.sqrt(hours / 168.0) * 0.92)
            window_decay = (engagement_decay / 300.0) * (hours / 168.0) * 1.25
            age_decay = (age_hours / 96.0) * (hours / 168.0) * 0.55
            multiplier = self._clamp(1.0 + (net_growth * window_scale * 3.4) - window_decay - age_decay, 0.45, 4.5)

            likes_value = max(1, int(round(base_likes * multiplier)))
            comments_value = max(0, int(round(base_comments * (multiplier * 0.92 + (viral_probability / 460.0)))))
            shares_value = max(0, int(round(base_shares * (multiplier * 0.86 + (trend_momentum_score / 560.0)))))
            reach_value = max(1, int(round(base_reach * (multiplier + (viral_probability / 540.0)))))
            engagement_value = max(1, int(round(likes_value + (comments_value * 2.0) + (shares_value * 3.0))))

            likes_forecast[label] = likes_value
            reach_forecast[label] = reach_value
            engagement_forecast[label] = engagement_value
            timeline_likes.append(likes_value)
            timeline_reach.append(reach_value)
            timeline_engagement.append(engagement_value)

        expected_reach = reach_forecast["Next 24 Hours"]
        expected_impressions = int(expected_reach * (1.12 + viral_probability / 260.0))
        peak_engagement_time = self._peak_time(platform, region, lifecycle_stage)
        if net_growth <= -0.03 or engagement_decay >= 68.0:
            growth_status = "Declining"
        elif net_growth >= 0.12 or viral_probability >= 82.0:
            growth_status = "Exploding"
        elif net_growth >= 0.04:
            growth_status = "Growing"
        else:
            growth_status = "Stable"

        return {
            "expected_reach": expected_reach,
            "expected_impressions": expected_impressions,
            "peak_engagement_time": peak_engagement_time,
            "engagement_decay": round(engagement_decay, 2),
            "viral_probability": round(viral_probability, 2),
            "trend_momentum_score": round(trend_momentum_score, 2),
            "forecast_confidence_score": round(forecast_confidence, 2),
            "growth_status": growth_status,
            "likes_forecast": likes_forecast,
            "reach_forecast": reach_forecast,
            "engagement_forecast": engagement_forecast,
            "forecast_timeline": {
                "labels": window_labels,
                "hours": window_hours,
                "likes": timeline_likes,
                "reach": timeline_reach,
                "engagement": timeline_engagement,
            },
            "forecast_summary": f"{growth_status} outlook with {viral_probability:.0f}% viral probability and {forecast_confidence:.0f}% confidence",
        }

    def _peak_time(self, platform: str, region: str, lifecycle_stage: str) -> str:
        if platform == "linkedin":
            return f"9:00 AM - 11:00 AM {self._region_suffix(region)}"
        if platform == "instagram":
            return f"6:30 PM - 9:30 PM {self._region_suffix(region)}"
        if platform == "youtube":
            return f"12:00 PM - 3:00 PM {self._region_suffix(region)}"
        if platform == "twitter":
            return f"8:00 AM - 10:00 AM {self._region_suffix(region)}"
        if lifecycle_stage == "Peaking":
            return f"Next 2-4 hours {self._region_suffix(region)}"
        return f"Late afternoon {self._region_suffix(region)}"

    def _region_suffix(self, region: str) -> str:
        region_key = (region or "").strip().lower()
        if region_key in {"india", "tamil nadu", "chennai", "trichy"}:
            return "IST"
        return "local time"

    def _analysis_notes(self, lifecycle_stage: str, momentum: float, trend_relevance: float, region: str, platform: str) -> list[str]:
        notes = [
            f"{platform.title()} performance in {region} is currently {lifecycle_stage.lower()} with momentum at {momentum:.0f}/100.",
            f"Trend relevance is {trend_relevance:.0f}/100, so the post still has topic alignment.",
        ]
        if lifecycle_stage in {"Declining", "Saturated"}:
            notes.append("The content likely needs a sharper hook or a new angle to regain traction.")
        elif lifecycle_stage in {"Rising", "Peaking"}:
            notes.append("Replying to comments quickly should help extend the engagement window.")
        return notes

    def _build_chart_data(
        self,
        profile: dict[str, Any],
        lifecycle_stage: str,
        momentum: float,
        growth_speed: float,
        engagement_decay: float,
    ) -> dict[str, Any]:
        base_reach = self._safe_number(profile.get("reach"))
        base_likes = self._safe_number(profile.get("likes"))
        base_comments = self._safe_number(profile.get("comments"))
        base_shares = self._safe_number(profile.get("shares"))
        stage_curve = self._stage_curve(lifecycle_stage)
        labels = [f"T{i}" for i in range(1, 8)]
        likes = []
        comments = []
        shares = []
        reach = []
        lifecycle = []
        base_decay = 1.0 - min(0.55, engagement_decay / 220.0)

        for index, curve in enumerate(stage_curve, start=1):
            multiplier = max(0.55, min(1.75, curve * base_decay))
            reach.append(max(1, int(base_reach * multiplier)))
            likes.append(max(1, int(base_likes * multiplier * (1 + momentum / 260.0))))
            comments.append(max(1, int(base_comments * multiplier * (1 + growth_speed / 300.0))))
            shares.append(max(1, int(base_shares * multiplier * (1 + momentum / 340.0))))
            lifecycle.append(round(curve * 100.0, 1))

        return {
            "labels": labels,
            "likes": likes,
            "comments": comments,
            "shares": shares,
            "reach": reach,
            "lifecycle": lifecycle,
            "momentum": round(momentum, 2),
            "growth_speed": round(growth_speed, 2),
        }

    def _stage_curve(self, lifecycle_stage: str) -> list[float]:
        mapping = {
            "Rising": [0.72, 0.84, 0.98, 1.08, 1.18, 1.28, 1.38],
            "Stable": [0.95, 0.98, 1.0, 1.02, 1.01, 1.0, 0.99],
            "Peaking": [0.9, 1.03, 1.16, 1.28, 1.22, 1.08, 0.96],
            "Saturated": [1.0, 1.01, 1.0, 0.99, 0.97, 0.96, 0.95],
            "Declining": [1.0, 0.96, 0.91, 0.86, 0.8, 0.74, 0.69],
        }
        return mapping.get(lifecycle_stage, mapping["Stable"])

    def _trend_relevance(self, title: str, platform: str, region: str, trends: list[dict[str, Any]]) -> float:
        query = f"{title} {platform} {region}".lower()
        query_tokens = self._keywords(query)
        if not query_tokens:
            return 42.0

        scores: list[float] = []
        for trend in trends:
            trend_text = " ".join(
                str(trend.get(key) or "")
                for key in ("title", "description", "platform", "source_label", "source_type", "category")
            ).lower()
            if not trend_text.strip():
                continue
            trend_tokens = self._keywords(trend_text)
            if not trend_tokens:
                continue
            overlap = len(query_tokens & trend_tokens) / len(query_tokens | trend_tokens)
            similarity = SequenceMatcher(None, query, trend_text).ratio()
            scores.append((overlap * 65.0) + (similarity * 35.0))

        if not scores:
            return self._clamp(40.0 + (len(query_tokens) * 4.5), 25.0, 72.0)
        return self._clamp(sum(scores) / len(scores), 20.0, 92.0)

    def _platform_boost(self, platform: str) -> float:
        mapping = {
            "linkedin": 1.12,
            "instagram": 1.18,
            "youtube": 1.15,
            "twitter": 1.08,
        }
        return mapping.get(platform, 1.0)

    def _region_boost(self, region: str, platform: str) -> float:
        region_key = (region or "").strip().lower()
        if region_key in {"india", "tamil nadu", "chennai", "trichy"}:
            if platform == "linkedin":
                return 1.12
            if platform == "instagram":
                return 1.1
            return 1.07
        return 1.0

    def _engagement_decay(self, momentum: float, growth_speed: float, lifecycle_stage: str) -> float:
        stage_penalty = {
            "Rising": 8.0,
            "Stable": 18.0,
            "Peaking": 24.0,
            "Saturated": 42.0,
            "Declining": 58.0,
        }.get(lifecycle_stage, 20.0)
        return self._clamp(stage_penalty + (100.0 - momentum) * 0.28 + (55.0 - growth_speed) * 0.22, 5.0, 92.0)

    def _history_snapshot(
        self,
        previous: dict[str, Any] | None,
        profile: dict[str, Any],
        lifecycle_stage: str,
        recommendations: dict[str, Any],
        forecast: dict[str, Any],
    ) -> dict[str, Any]:
        history = {
            "previous_track": previous or None,
            "current_total_engagement": int(profile["likes"] + profile["comments"] + profile["shares"]),
            "trend_lifecycle": lifecycle_stage,
            "recommendation_preview": recommendations.get("ai_recommendations", {}),
            "forecast_preview": forecast,
        }
        return history

    def _recommendation_line(self, platform: str, region: str, lifecycle_stage: str, high_engagement: bool) -> str:
        if platform == "linkedin":
            return "Reply to comments quickly for better LinkedIn reach."
        if platform == "instagram":
            return "Keep the reel short and rehook viewers in the first 2 seconds."
        if platform == "youtube":
            return "Use a stronger thumbnail/title combination and pin a comment update."
        if platform == "twitter":
            return "Keep the thread concise and repost the strongest insight."
        if high_engagement:
            return f"Momentum is healthy in {region}; publish a follow-up while the conversation is active."
        if lifecycle_stage in {"Declining", "Saturated"}:
            return "Create Part 2 within next 24 hours."
        return "Should improve hook and tighten the call to action."

    def _platform_recommendation(self, platform: str) -> str:
        if platform == "linkedin":
            return "LinkedIn: prioritize comments, saves, and a follow-up reply within the first hour."
        if platform == "instagram":
            return "Instagram: keep the opening hook fast and optimize for shares and reel retention."
        if platform == "youtube":
            return "YouTube: improve title/thumbnail clarity and watch for early click-through momentum."
        if platform == "twitter":
            return "Twitter/X: keep the post concise and encourage replies to extend the thread."
        return "Match the format to the audience and keep the next post easy to scan."

    def _safe_number(self, value: Any) -> float:
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0

    def _clamp(self, value: float, minimum: float, maximum: float) -> float:
        return max(minimum, min(maximum, value))

    def _elapsed_hours(self, value: Any) -> float:
        parsed = self._parse_datetime(value)
        if parsed is None:
            return 0.0
        return max(0.0, (datetime.now(timezone.utc) - parsed).total_seconds() / 3600.0)

    def _parse_datetime(self, value: Any) -> datetime | None:
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        if isinstance(value, str):
            try:
                parsed = datetime.fromisoformat(value)
                return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
            except ValueError:
                return None
        return None

    def _keywords(self, text: str) -> set[str]:
        return {
            token.strip(".,!?;:\"'()[]{}").lower()
            for token in text.split()
            if len(token.strip(".,!?;:\"'()[]{}")) > 2
        }

    def _summary(self, title: str, platform: str, region: str, lifecycle_stage: str, momentum: float, trend_relevance: float) -> str:
        return (
            f"{title} is currently {lifecycle_stage.lower()} on {self.PLATFORM_LABELS.get(platform, platform.title())} in {region}. "
            f"Momentum is {momentum:.0f}/100 and trend relevance is {trend_relevance:.0f}/100."
        )


def safe_len(text: Any) -> int:
    return len(str(text or "").strip())


def track_post_performance(
    post_url: str,
    region: str = "India",
    platform: str = "",
    user_id: int | None = None,
    manual_metrics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return PostPerformanceService().track_post_performance(
        post_url=post_url,
        region=region,
        platform=platform,
        user_id=user_id,
        manual_metrics=manual_metrics,
    )
