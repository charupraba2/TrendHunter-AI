"""Analytics-first scoring engine for Industry Intelligence numeric scores."""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, pstdev
from typing import Any

try:
    import joblib
except Exception:  # pragma: no cover - optional dependency guard
    joblib = None

try:
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.preprocessing import MinMaxScaler
except Exception:  # pragma: no cover - optional dependency guard
    RandomForestRegressor = None
    MinMaxScaler = None

from backend.database import IndustryOpportunity, TrendHistory, get_db_session

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ScoreSpec:
    target: str
    weights: dict[str, float]
    positive_bias: float


class IndustryAnalyticsScoringEngine:
    feature_names = [
        "mention_count",
        "source_count",
        "evidence_count",
        "recency_score",
        "trend_frequency",
        "keyword_relevance",
        "competitor_activity",
        "market_gap",
        "historical_growth",
    ]

    target_specs = {
        "momentum": ScoreSpec(
            target="momentum",
            weights={
                "mention_count": 0.18,
                "source_count": 0.14,
                "evidence_count": 0.12,
                "recency_score": 0.16,
                "trend_frequency": 0.15,
                "keyword_relevance": 0.12,
                "competitor_activity": 0.04,
                "market_gap": 0.09,
                "historical_growth": 0.10,
            },
            positive_bias=12.0,
        ),
        "growth": ScoreSpec(
            target="growth",
            weights={
                "mention_count": 0.10,
                "source_count": 0.14,
                "evidence_count": 0.14,
                "recency_score": 0.12,
                "trend_frequency": 0.18,
                "keyword_relevance": 0.16,
                "competitor_activity": 0.03,
                "market_gap": 0.10,
                "historical_growth": 0.13,
            },
            positive_bias=10.0,
        ),
        "threat": ScoreSpec(
            target="threat",
            weights={
                "mention_count": 0.08,
                "source_count": 0.08,
                "evidence_count": 0.06,
                "recency_score": 0.10,
                "trend_frequency": 0.08,
                "keyword_relevance": 0.08,
                "competitor_activity": 0.26,
                "market_gap": -0.15,
                "historical_growth": 0.11,
            },
            positive_bias=14.0,
        ),
        "opportunity": ScoreSpec(
            target="opportunity",
            weights={
                "mention_count": 0.07,
                "source_count": 0.08,
                "evidence_count": 0.10,
                "recency_score": 0.10,
                "trend_frequency": 0.15,
                "keyword_relevance": 0.17,
                "competitor_activity": -0.08,
                "market_gap": 0.18,
                "historical_growth": 0.15,
            },
            positive_bias=13.0,
        ),
        "product_impact": ScoreSpec(
            target="product_impact",
            weights={
                "mention_count": 0.06,
                "source_count": 0.08,
                "evidence_count": 0.08,
                "recency_score": 0.08,
                "trend_frequency": 0.14,
                "keyword_relevance": 0.15,
                "competitor_activity": -0.05,
                "market_gap": 0.17,
                "historical_growth": 0.18,
            },
            positive_bias=12.0,
        ),
    }

    def __init__(self, model_dir: Path | None = None, seed: int = 42) -> None:
        self.seed = seed
        self.model_dir = model_dir or Path(__file__).resolve().parents[2] / "models" / "industry_analytics"
        self.bundle_path = self.model_dir / "industry_analytics_models.joblib"
        self.ready = False
        self.available = False
        self.models: dict[str, Any] = {}
        self.scaler = None
        self.metadata: dict[str, Any] = {}
        self._ensure_models()

    def _ensure_models(self) -> None:
        if self.ready:
            return
        self.ready = True

        if joblib is None or RandomForestRegressor is None or MinMaxScaler is None:
            logger.info("Industry analytics ML dependencies are unavailable. Falling back to weighted analytics.")
            return

        self.model_dir.mkdir(parents=True, exist_ok=True)
        if self.bundle_path.exists():
            try:
                bundle = joblib.load(self.bundle_path)
                self._load_bundle(bundle)
                self.available = True
                return
            except Exception as exc:
                logger.warning("Failed to load industry analytics bundle: %s", exc)

        try:
            bundle = self._train_bundle()
            joblib.dump(bundle, self.bundle_path)
            self._load_bundle(bundle)
            self.available = True
        except Exception as exc:
            logger.exception("Industry analytics initialization failed: %s", exc)
            self.available = False

    def _load_bundle(self, bundle: dict[str, Any]) -> None:
        self.models = bundle.get("models") or {}
        self.scaler = bundle.get("scaler")
        self.metadata = bundle.get("metadata") or {}

    def _train_bundle(self) -> dict[str, Any]:
        dataset = self._build_training_dataset()
        scaler = MinMaxScaler()
        scaler.fit(dataset["x"])

        target_models: dict[str, Any] = {}
        for target_name in self.target_specs:
            target_values = dataset["targets"][target_name]
            if len(target_values) >= 40:
                model = RandomForestRegressor(
                    n_estimators=120,
                    random_state=self.seed,
                    max_depth=10,
                    min_samples_leaf=2,
                )
                model.fit(scaler.transform(dataset["x"]), target_values)
                target_models[target_name] = model

        metadata = {
            "version": "1.0",
            "feature_names": self.feature_names,
            "training_samples": len(dataset["x"]),
            "historical_samples": dataset["historical_samples"],
            "feature_means": [round(mean(column), 4) for column in zip(*dataset["x"], strict=False)],
            "feature_stds": [round(pstdev(column), 4) for column in zip(*dataset["x"], strict=False)],
            "target_means": {name: round(mean(values), 4) if values else 0.0 for name, values in dataset["targets"].items()},
        }
        return {"models": target_models, "scaler": scaler, "metadata": metadata}

    def _build_training_dataset(self) -> dict[str, Any]:
        synthetic = self._build_synthetic_dataset(900)
        historical = self._build_historical_samples()
        x = list(synthetic["x"])
        targets = {name: list(values) for name, values in synthetic["targets"].items()}
        historical_count = 0

        for sample in historical:
            x.append(sample["features"])
            for target_name, value in sample["targets"].items():
                targets[target_name].append(value)
            historical_count += 1

        return {"x": x, "targets": targets, "historical_samples": historical_count}

    def _build_historical_samples(self) -> list[dict[str, Any]]:
        samples: list[dict[str, Any]] = []
        session = get_db_session()
        try:
            history_rows = session.query(TrendHistory).order_by(TrendHistory.keyword.asc(), TrendHistory.timestamp.asc(), TrendHistory.id.asc()).all()
            previous_by_keyword: dict[str, TrendHistory] = {}
            for row in history_rows:
                keyword = str(row.keyword or "").strip()
                if not keyword:
                    continue
                mention_count = float((row.news_count or 0) + (row.rag_match_count or 0) + (row.competitor_mention_count or 0))
                source_count = float(row.source_count or 0)
                evidence_count = max(source_count, mention_count, 1.0)
                recency_score = self._recency_score(row.timestamp)
                trend_frequency = float(sum(1 for item in history_rows if item.keyword == keyword))
                keyword_relevance = self._clamp((row.trend_score * 0.55) + (row.growth_score * 0.45), 0.0, 100.0)
                competitor_activity = self._clamp((row.competitor_mention_count * 18.0) + (source_count * 5.0), 0.0, 100.0)
                market_gap = self._clamp(100.0 - competitor_activity - (source_count * 1.5), 0.0, 100.0)
                previous = previous_by_keyword.get(keyword)
                historical_growth = 0.0
                if previous is not None:
                    historical_growth = self._clamp(row.growth_score - float(previous.growth_score or 0.0), -100.0, 100.0)
                else:
                    historical_growth = self._clamp(row.growth_score * 0.5, 0.0, 100.0)
                previous_by_keyword[keyword] = row
                features = [
                    mention_count,
                    source_count,
                    evidence_count,
                    recency_score,
                    trend_frequency,
                    keyword_relevance,
                    competitor_activity,
                    market_gap,
                    historical_growth,
                ]
                samples.append(
                    {
                        "features": features,
                        "targets": {
                            "momentum": self._clamp(row.trend_score, 0.0, 100.0),
                            "growth": self._clamp(row.growth_score, 0.0, 100.0),
                            "threat": self._clamp((row.competitor_mention_count * 22.0) + source_count * 4.0, 0.0, 100.0),
                            "opportunity": self._clamp((row.trend_score * 0.48) + (row.growth_score * 0.52), 0.0, 100.0),
                            "product_impact": self._clamp((row.trend_score * 0.33) + (row.growth_score * 0.32) + (evidence_count * 2.0), 0.0, 100.0),
                        },
                    }
                )

            opportunity_rows = session.query(IndustryOpportunity).all()
            for row in opportunity_rows:
                inputs = row.signal_inputs or {}
                features = [
                    float(row.evidence_count or 0),
                    float(row.source_count or 0),
                    float(row.evidence_count or 0),
                    self._recency_score(row.updated_at or row.created_at),
                    float(inputs.get("opportunity_count") or 0),
                    float(inputs.get("search_relevance") or inputs.get("market_demand") or 0),
                    float(inputs.get("competitor_density") or 0),
                    self._clamp(100.0 - float(inputs.get("competitor_density") or 0), 0.0, 100.0),
                    float(inputs.get("historical_growth") or inputs.get("trend_strength") or 0),
                ]
                opportunity_score = float(row.opportunity_score or 0.0)
                samples.append(
                    {
                        "features": features,
                        "targets": {
                            "momentum": opportunity_score,
                            "growth": opportunity_score,
                            "threat": self._clamp(float(inputs.get("competitor_density") or 0), 0.0, 100.0),
                            "opportunity": opportunity_score,
                            "product_impact": self._clamp((opportunity_score * 0.7) + (float(row.confidence_score or 0.0) * 0.3), 0.0, 100.0),
                        },
                    }
                )
        finally:
            session.close()

        if len(samples) < 40:
            return self._synthetic_to_samples(self._build_synthetic_dataset(900))
        return samples

    def _synthetic_to_samples(self, dataset: dict[str, Any]) -> list[dict[str, Any]]:
        samples: list[dict[str, Any]] = []
        for index, row in enumerate(dataset["x"]):
            targets = {name: values[index] for name, values in dataset["targets"].items()}
            samples.append({"features": row, "targets": targets})
        return samples

    def _build_synthetic_dataset(self, sample_count: int) -> dict[str, Any]:
        rng = random.Random(self.seed)
        rows: list[list[float]] = []
        targets = {name: [] for name in self.target_specs}
        for _ in range(sample_count):
            mention_count = self._clamp(rng.gauss(6.0, 2.8), 0.0, 20.0)
            source_count = self._clamp(rng.gauss(5.0, 2.2), 0.0, 16.0)
            evidence_count = self._clamp(mention_count + source_count + rng.gauss(0.0, 1.2), 0.0, 24.0)
            recency_score = self._clamp(rng.gauss(7.5, 2.8), 0.0, 12.0)
            trend_frequency = self._clamp(rng.gauss(4.5, 2.5), 0.0, 16.0)
            keyword_relevance = self._clamp(rng.gauss(58.0, 15.0), 0.0, 100.0)
            competitor_activity = self._clamp(rng.gauss(42.0, 16.0), 0.0, 100.0)
            market_gap = self._clamp(100.0 - competitor_activity + rng.gauss(0.0, 8.0), 0.0, 100.0)
            historical_growth = self._clamp(rng.gauss(22.0, 18.0), -40.0, 100.0)
            rows.append([
                mention_count,
                source_count,
                evidence_count,
                recency_score,
                trend_frequency,
                keyword_relevance,
                competitor_activity,
                market_gap,
                historical_growth,
            ])
            targets["momentum"].append(self._clamp(8.0 + mention_count * 2.0 + source_count * 1.8 + evidence_count * 1.0 + recency_score * 2.2 + trend_frequency * 1.9 + keyword_relevance * 0.18 + (100.0 - competitor_activity) * 0.06 + market_gap * 0.09 + historical_growth * 0.10 + rng.gauss(0.0, 4.0), 0.0, 100.0))
            targets["growth"].append(self._clamp(6.0 + mention_count * 1.2 + source_count * 1.6 + evidence_count * 1.1 + recency_score * 1.6 + trend_frequency * 2.2 + keyword_relevance * 0.2 + market_gap * 0.16 + historical_growth * 0.18 - competitor_activity * 0.06 + rng.gauss(0.0, 4.2), 0.0, 100.0))
            targets["threat"].append(self._clamp(10.0 + competitor_activity * 0.32 + source_count * 1.0 + evidence_count * 0.7 + trend_frequency * 0.7 + keyword_relevance * 0.10 - market_gap * 0.14 + historical_growth * 0.04 + rng.gauss(0.0, 4.5), 0.0, 100.0))
            targets["opportunity"].append(self._clamp(12.0 + market_gap * 0.24 + trend_frequency * 1.5 + keyword_relevance * 0.16 + historical_growth * 0.16 + evidence_count * 0.8 + source_count * 0.7 - competitor_activity * 0.08 + rng.gauss(0.0, 4.2), 0.0, 100.0))
            targets["product_impact"].append(self._clamp(10.0 + market_gap * 0.20 + trend_frequency * 1.0 + keyword_relevance * 0.18 + historical_growth * 0.14 + evidence_count * 0.9 - competitor_activity * 0.06 + rng.gauss(0.0, 4.0), 0.0, 100.0))
        return {"x": rows, "targets": targets}

    def score(self, target: str, features: dict[str, Any]) -> dict[str, Any]:
        target_key = target if target in self.target_specs else "momentum"
        spec = self.target_specs[target_key]
        values = [self._clamp(self._safe_number(features.get(name)), -100.0 if name == "historical_growth" else 0.0, 100.0) for name in self.feature_names]
        normalized = self._normalize(values)
        model = self.models.get(target_key)
        method = "ML/analytics-based"
        weighted_score, weighted_factors, weighted_confidence = self._weighted_score(values, normalized, spec)
        if model is not None and self.scaler is not None:
            scaled = self.scaler.transform([values])[0]
            predicted = float(model.predict([scaled])[0])
            model_confidence = self._model_confidence(model, scaled, target_key, predicted)
            model_factors = self._feature_contributions(model, values, scaled, target_key)
            blend_weight = 0.62 if int(self.metadata.get("historical_samples", 0)) >= 40 else 0.5
            score = self._clamp((predicted * blend_weight) + (weighted_score * (1.0 - blend_weight)), 0.0, 100.0)
            confidence = self._clamp((model_confidence * blend_weight) + (weighted_confidence * (1.0 - blend_weight)), 35.0, 95.0)
            top_factors = (model_factors[:2] + weighted_factors[:2])[:4]
            scoring_method = "ML/analytics-based"
            model_name = "RandomForestRegressor"
        else:
            score, top_factors, confidence = weighted_score, weighted_factors, weighted_confidence
            scoring_method = "Analytics-weighted fallback"
            model_name = "Weighted Formula"

        score_features = {
            "raw": {name: round(values[index], 4) for index, name in enumerate(self.feature_names)},
            "normalized": {name: round(normalized[index], 4) for index, name in enumerate(self.feature_names)},
            "method": scoring_method,
            "model": model_name,
            "target": target_key,
            "historical_samples": int(self.metadata.get("historical_samples", 0)),
            "training_samples": int(self.metadata.get("training_samples", 0)),
        }
        return {
            "score": round(score, 1),
            "confidence_score": round(confidence, 1),
            "scoring_method": scoring_method,
            "llm_used_for_score": False,
            "score_features": score_features,
            "top_factors": top_factors[:4],
        }

    def _weighted_score(self, values: list[float], normalized: list[float], spec: ScoreSpec) -> tuple[float, list[dict[str, Any]], float]:
        baseline = 0.5
        contributions: list[dict[str, Any]] = []
        weighted = spec.positive_bias
        for index, feature_name in enumerate(self.feature_names):
            weight = spec.weights.get(feature_name, 0.0)
            centered = normalized[index] - baseline
            impact = centered * weight * 100.0
            weighted += impact
            contributions.append(self._contribution_dict(feature_name, values[index], normalized[index], weight, impact, "Weighted analytics"))
        contributions.sort(key=lambda item: abs(item["signed_impact"]), reverse=True)
        confidence = self._clamp(68.0 + min(20.0, sum(abs(item["signed_impact"]) for item in contributions[:4]) / 8.0), 35.0, 95.0)
        return self._clamp(weighted, 0.0, 100.0), contributions, confidence

    def _feature_contributions(self, model: Any, values: list[float], scaled: list[float], target: str) -> list[dict[str, Any]]:
        baseline = [0.5] * len(values)
        try:
            if hasattr(self.scaler, "inverse_transform"):
                baseline = list(self.scaler.inverse_transform([baseline])[0])
        except Exception:
            baseline = [0.0] * len(values)
        base_prediction = float(model.predict([scaled])[0])
        factors: list[dict[str, Any]] = []
        for index, feature_name in enumerate(self.feature_names):
            variant = list(scaled)
            variant[index] = 0.5
            variant_prediction = float(model.predict([variant])[0])
            signed_impact = base_prediction - variant_prediction
            factors.append(self._contribution_dict(feature_name, values[index], float(scaled[index]), 0.0, signed_impact, "ML perturbation", baseline[index], variant_prediction, base_prediction))
        factors.sort(key=lambda item: abs(item["signed_impact"]), reverse=True)
        return factors

    def _contribution_dict(
        self,
        feature_name: str,
        actual_value: float,
        normalized_value: float,
        weight: float,
        signed_impact: float,
        method: str,
        baseline_value: float | None = None,
        variant_prediction: float | None = None,
        base_prediction: float | None = None,
    ) -> dict[str, Any]:
        direction = "Positive" if signed_impact >= 0 else "Negative"
        return {
            "factor": self._label_feature(feature_name),
            "actual_value": round(actual_value, 4),
            "normalized_value": round(normalized_value, 4),
            "weight": round(weight, 4),
            "signed_impact": round(signed_impact, 2),
            "impact": round(abs(signed_impact), 2),
            "signed_display": f"{signed_impact:+.2f}",
            "direction": direction,
            "contribution_direction": direction,
            "business_explanation": self._build_business_explanation(feature_name, actual_value, normalized_value, signed_impact, method),
            "method": method,
            "baseline_value": round(baseline_value, 4) if baseline_value is not None else None,
            "variant_prediction": round(variant_prediction, 2) if variant_prediction is not None else None,
            "base_prediction": round(base_prediction, 2) if base_prediction is not None else None,
        }

    def _build_business_explanation(self, feature_name: str, actual_value: float, normalized_value: float, signed_impact: float, method: str) -> str:
        label = self._label_feature(feature_name)
        if signed_impact >= 0:
            return f"{label} increased the score because the feature is relatively strong in the current dataset."
        return f"{label} decreased the score because the feature is relatively weak versus the trained baseline."

    def _label_feature(self, name: str) -> str:
        labels = {
            "mention_count": "Mention Count",
            "source_count": "Source Count",
            "evidence_count": "Evidence Count",
            "recency_score": "Recency Score",
            "trend_frequency": "Trend Frequency",
            "keyword_relevance": "Keyword Relevance",
            "competitor_activity": "Competitor Activity",
            "market_gap": "Market Gap",
            "historical_growth": "Historical Growth",
        }
        return labels.get(name, name.replace("_", " ").title())

    def _normalize(self, values: list[float]) -> list[float]:
        mins = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, -40.0]
        maxs = [20.0, 16.0, 24.0, 12.0, 16.0, 100.0, 100.0, 100.0, 100.0]
        normalized: list[float] = []
        for index, value in enumerate(values):
            span = max(maxs[index] - mins[index], 1e-6)
            normalized.append(self._clamp((value - mins[index]) / span, 0.0, 1.0))
        return normalized

    def _recency_score(self, value: Any) -> float:
        if not value:
            return 0.0
        try:
            dt = value if hasattr(value, "tzinfo") else None
        except Exception:
            dt = None
        if dt is None:
            try:
                from datetime import datetime, timezone

                parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
                dt = parsed.astimezone(timezone.utc) if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
            except Exception:
                return 0.0
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        if getattr(dt, "tzinfo", None) is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        age_days = max(0.0, (now - dt).total_seconds() / 86400.0)
        return self._clamp(12.0 - min(12.0, age_days * 1.2), 0.0, 12.0)

    def _model_confidence(self, model: Any, scaled: list[float], target: str, predicted: float) -> float:
        tree_predictions = [float(estimator.predict([scaled])[0]) for estimator in getattr(model, "estimators_", [])]
        spread = pstdev(tree_predictions) if len(tree_predictions) > 1 else 0.0
        variance_penalty = min(24.0, spread * 1.4)
        return self._clamp(92.0 - variance_penalty, 35.0, 95.0)

    def _safe_number(self, value: Any, default: float = 0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def _clamp(self, value: float, minimum: float, maximum: float) -> float:
        return max(minimum, min(maximum, value))


industry_analytics_scoring_engine = IndustryAnalyticsScoringEngine()
