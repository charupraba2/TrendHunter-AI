"""Sentiment analysis helpers using VADER with a safe fallback."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class SentimentResult:
    positive_score: float
    negative_score: float
    neutral_score: float
    compound_score: float
    sentiment_label: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "positive_score": self.positive_score,
            "negative_score": self.negative_score,
            "neutral_score": self.neutral_score,
            "compound_score": self.compound_score,
            "sentiment_label": self.sentiment_label,
        }


class SentimentAgent:
    def __init__(self) -> None:
        self._analyzer = self._load_analyzer()

    def _load_analyzer(self):
        try:
            from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
        except Exception:
            return None

        try:
            return SentimentIntensityAnalyzer()
        except Exception:
            return None

    def analyze_text(self, text: str) -> dict[str, Any]:
        text = (text or "").strip()
        if not text:
            return SentimentResult(0.0, 0.0, 1.0, 0.0, "Neutral").to_dict()

        if self._analyzer is not None:
            scores = self._analyzer.polarity_scores(text)
            compound = float(scores.get("compound", 0.0))
            return SentimentResult(
                positive_score=float(scores.get("pos", 0.0)),
                negative_score=float(scores.get("neg", 0.0)),
                neutral_score=float(scores.get("neu", 0.0)),
                compound_score=compound,
                sentiment_label=self._label_from_compound(compound),
            ).to_dict()

        return self._fallback_analysis(text)

    def score_text(self, text: str) -> float:
        """Backward-compatible helper returning the compound sentiment score."""

        return float(self.analyze_text(text)["compound_score"])

    def _label_from_compound(self, compound: float) -> str:
        if compound >= 0.05:
            return "Positive"
        if compound <= -0.05:
            return "Negative"
        return "Neutral"

    def _fallback_analysis(self, text: str) -> dict[str, Any]:
        positive_words = {
            "good",
            "great",
            "best",
            "love",
            "boost",
            "win",
            "viral",
            "growth",
            "amazing",
            "awesome",
        }
        negative_words = {
            "bad",
            "worst",
            "hate",
            "drop",
            "fail",
            "problem",
            "risk",
            "slow",
            "awful",
        }

        words = [word.lower().strip(".,!?") for word in text.split() if word.strip()]
        if not words:
            return SentimentResult(0.0, 0.0, 1.0, 0.0, "Neutral").to_dict()

        positive_hits = sum(1 for word in words if word in positive_words)
        negative_hits = sum(1 for word in words if word in negative_words)
        total_hits = positive_hits + negative_hits

        if total_hits == 0:
            return SentimentResult(0.0, 0.0, 1.0, 0.0, "Neutral").to_dict()

        positive_score = positive_hits / total_hits
        negative_score = negative_hits / total_hits
        neutral_score = max(0.0, 1.0 - min(1.0, positive_score + negative_score))
        compound = round(positive_score - negative_score, 3)

        return SentimentResult(
            positive_score=round(positive_score, 3),
            negative_score=round(negative_score, 3),
            neutral_score=round(neutral_score, 3),
            compound_score=compound,
            sentiment_label=self._label_from_compound(compound),
        ).to_dict()
