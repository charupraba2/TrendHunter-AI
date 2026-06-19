"""Hybrid ML engine for Product Impact Intelligence."""

from __future__ import annotations

import logging
import random
from pathlib import Path
from statistics import mean, pstdev
from typing import Any

try:
    import joblib
except Exception:  # pragma: no cover - optional dependency guard
    joblib = None

try:
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.linear_model import LinearRegression, LogisticRegression
    from sklearn.metrics import accuracy_score, r2_score
except Exception:  # pragma: no cover - optional dependency guard
    RandomForestRegressor = None
    LinearRegression = None
    LogisticRegression = None
    accuracy_score = None
    r2_score = None

logger = logging.getLogger(__name__)


class ProductImpactMLEngine:
    launch_features = [
        "market_demand",
        "enterprise_fit",
        "revenue_opportunity",
        "competitive_advantage",
        "risk_score",
        "trend_strength",
        "competitor_density",
        "opportunity_count",
    ]
    risk_features = [
        "compliance_complexity",
        "security_risk",
        "adoption_difficulty",
        "integration_complexity",
        "market_competition",
    ]
    revenue_features = [
        "market_demand",
        "enterprise_fit",
        "adoption_score",
        "competitive_advantage",
    ]

    def __init__(self, model_dir: Path | None = None, seed: int = 42) -> None:
        self.seed = seed
        self.model_dir = model_dir or Path(__file__).resolve().parents[2] / "models" / "product_impact"
        self.bundle_path = self.model_dir / "product_impact_models.joblib"
        self.ready = False
        self.available = False
        self.models: dict[str, Any] = {}
        self.metadata: dict[str, Any] = {}
        self._ensure_models()

    def _ensure_models(self) -> None:
        if self.ready:
            return
        self.ready = True

        if joblib is None or RandomForestRegressor is None or LogisticRegression is None or LinearRegression is None:
            logger.info("Product impact ML dependencies are unavailable. Falling back to heuristics.")
            return

        self.model_dir.mkdir(parents=True, exist_ok=True)
        if self.bundle_path.exists():
            try:
                bundle = joblib.load(self.bundle_path)
                self._load_bundle(bundle)
                self.available = True
                logger.info("Loaded product impact ML models from %s", self.bundle_path)
                return
            except Exception as exc:
                logger.warning("Failed to load product impact ML bundle: %s", exc)

        try:
            bundle = self._train_bundle()
            joblib.dump(bundle, self.bundle_path)
            self._load_bundle(bundle)
            self.available = True
            logger.info("Trained and saved product impact ML models to %s", self.bundle_path)
        except Exception as exc:
            logger.exception("Product impact ML initialization failed: %s", exc)
            self.available = False

    def _load_bundle(self, bundle: dict[str, Any]) -> None:
        self.models = bundle.get("models") or {}
        self.metadata = bundle.get("metadata") or {}

    def _train_bundle(self) -> dict[str, Any]:
        dataset = self._build_synthetic_dataset(720)
        launch_model = RandomForestRegressor(n_estimators=160, random_state=self.seed, max_depth=10, min_samples_leaf=2)
        risk_model = LogisticRegression(max_iter=2000, random_state=self.seed)
        revenue_model = LinearRegression()

        launch_model.fit(dataset["launch_x"], dataset["launch_y"])
        risk_model.fit(dataset["risk_x"], dataset["risk_y"])
        revenue_model.fit(dataset["revenue_x"], dataset["revenue_y"])

        launch_pred = launch_model.predict(dataset["launch_x"])
        risk_pred = risk_model.predict(dataset["risk_x"])
        revenue_pred = revenue_model.predict(dataset["revenue_x"])
        risk_proba = risk_model.predict_proba(dataset["risk_x"])

        launch_metrics = {
            "r2": float(r2_score(dataset["launch_y"], launch_pred)) if r2_score is not None else 0.0,
            "mae": self._mae(dataset["launch_y"], launch_pred),
            "feature_importances": dict(zip(self.launch_features, [float(value) for value in launch_model.feature_importances_])),
        }
        risk_metrics = {
            "accuracy": float(accuracy_score(dataset["risk_y"], risk_pred)) if accuracy_score is not None else 0.0,
            "class_balance": self._class_balance(dataset["risk_y"]),
            "feature_importances": self._average_abs_coefficients(risk_model.coef_, self.risk_features),
        }
        revenue_metrics = {
            "r2": float(r2_score(dataset["revenue_y"], revenue_pred)) if r2_score is not None else 0.0,
            "mae": self._mae(dataset["revenue_y"], revenue_pred),
            "feature_importances": self._linear_importance(revenue_model.coef_, self.revenue_features),
        }

        return {
            "models": {
                "launch_readiness": launch_model,
                "risk_classification": risk_model,
                "revenue_opportunity": revenue_model,
            },
            "metadata": {
                "version": "1.0",
                "feature_means": {
                    "launch_readiness": self._feature_means(dataset["launch_x"]),
                    "risk_classification": self._feature_means(dataset["risk_x"]),
                    "revenue_opportunity": self._feature_means(dataset["revenue_x"]),
                },
                "feature_stds": {
                    "launch_readiness": self._feature_stds(dataset["launch_x"]),
                    "risk_classification": self._feature_stds(dataset["risk_x"]),
                    "revenue_opportunity": self._feature_stds(dataset["revenue_x"]),
                },
                "launch_metrics": launch_metrics,
                "risk_metrics": risk_metrics,
                "revenue_metrics": revenue_metrics,
                "risk_class_labels": ["Low Risk", "Medium Risk", "High Risk"],
            },
        }

    def predict(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.available:
            return {"available": False}

        launch_input = [self._safe_number(payload.get(name)) for name in self.launch_features]
        risk_input = [self._safe_number(payload.get(name)) for name in self.risk_features]
        revenue_input = [self._safe_number(payload.get(name)) for name in self.revenue_features]

        launch_result = self._predict_launch_readiness(launch_input)
        risk_result = self._predict_risk_classification(risk_input)
        revenue_result = self._predict_revenue_opportunity(revenue_input)

        return {
            "available": True,
            "model_version": self.metadata.get("version", "1.0"),
            "launch_readiness": launch_result,
            "risk_classification": risk_result,
            "revenue_opportunity": revenue_result,
        }

    def _predict_launch_readiness(self, values: list[float]) -> dict[str, Any]:
        model = self.models.get("launch_readiness")
        means = self.metadata.get("feature_means", {}).get("launch_readiness") or [0.0] * len(self.launch_features)
        if model is None:
            return {"available": False}

        prediction = float(model.predict([values])[0])
        tree_predictions = [float(estimator.predict([values])[0]) for estimator in getattr(model, "estimators_", [])]
        spread = pstdev(tree_predictions) if len(tree_predictions) > 1 else 0.0
        confidence = self._clamp(92.0 - (spread * 1.2) + (self.metadata.get("launch_metrics", {}).get("r2", 0.0) * 10.0), 35.0, 95.0)

        top_factors = self._feature_contributions(
            model_name="launch_readiness",
            values=values,
            baseline=means,
            feature_names=self.launch_features,
            predict_fn=lambda row: float(model.predict([row])[0]),
            target_label="launch readiness",
            positive_meaning="higher readiness",
        )

        return {
            "predicted_score": round(self._clamp(prediction, 0.0, 100.0), 1),
            "confidence_score": round(confidence, 1),
            "model": "RandomForestRegressor",
            "top_factors": top_factors[:3],
        }

    def _predict_risk_classification(self, values: list[float]) -> dict[str, Any]:
        model = self.models.get("risk_classification")
        means = self.metadata.get("feature_means", {}).get("risk_classification") or [0.0] * len(self.risk_features)
        labels = self.metadata.get("risk_class_labels") or ["Low Risk", "Medium Risk", "High Risk"]
        if model is None:
            return {"available": False}

        class_index = int(model.predict([values])[0])
        probabilities = [float(value) for value in model.predict_proba([values])[0]]
        predicted_probability = probabilities[class_index] if class_index < len(probabilities) else max(probabilities or [0.0])
        risk_index = 2 if len(probabilities) >= 3 else class_index
        probability = probabilities[risk_index] if risk_index < len(probabilities) else predicted_probability
        label = labels[class_index] if class_index < len(labels) else "Medium Risk"
        confidence = self._clamp(predicted_probability * 100.0, 35.0, 99.0)

        top_factors = self._feature_contributions(
            model_name="risk_classification",
            values=values,
            baseline=means,
            feature_names=self.risk_features,
            predict_fn=lambda row, idx=risk_index: float(model.predict_proba([row])[0][idx]),
            target_label="risk probability",
            positive_meaning="higher risk",
        )

        return {
            "predicted_label": label,
            "risk_probability": round(probability, 4),
            "predicted_label_probability": round(predicted_probability, 4),
            "confidence_score": round(confidence, 1),
            "model": "LogisticRegression",
            "top_factors": top_factors[:3],
            "probabilities": {
                labels[index] if index < len(labels) else f"Class {index}": round(value, 4)
                for index, value in enumerate(probabilities)
            },
        }

    def _predict_revenue_opportunity(self, values: list[float]) -> dict[str, Any]:
        model = self.models.get("revenue_opportunity")
        means = self.metadata.get("feature_means", {}).get("revenue_opportunity") or [0.0] * len(self.revenue_features)
        if model is None:
            return {"available": False}

        prediction = float(model.predict([values])[0])
        train_r2 = float(self.metadata.get("revenue_metrics", {}).get("r2", 0.0))
        confidence = self._clamp(75.0 + (train_r2 * 15.0), 35.0, 95.0)

        top_factors = self._feature_contributions(
            model_name="revenue_opportunity",
            values=values,
            baseline=means,
            feature_names=self.revenue_features,
            predict_fn=lambda row: float(model.predict([row])[0]),
            target_label="revenue opportunity",
            positive_meaning="higher revenue",
        )

        return {
            "predicted_score": round(self._clamp(prediction, 0.0, 100.0), 1),
            "confidence_score": round(confidence, 1),
            "model": "LinearRegression",
            "top_factors": top_factors[:3],
        }

    def _build_synthetic_dataset(self, sample_count: int) -> dict[str, list[list[float]] | list[float]]:
        rng = random.Random(self.seed)
        launch_x: list[list[float]] = []
        launch_y: list[float] = []
        risk_x: list[list[float]] = []
        risk_y: list[int] = []
        revenue_x: list[list[float]] = []
        revenue_y: list[float] = []

        for _ in range(sample_count):
            market_demand = self._clamp(rng.gauss(58.0, 18.0), 5.0, 98.0)
            enterprise_fit = self._clamp(rng.gauss(56.0, 17.0), 5.0, 98.0)
            trend_strength = self._clamp(rng.gauss(54.0, 18.0) + (market_demand * 0.12), 5.0, 98.0)
            competitor_density = self._clamp(rng.gauss(42.0, 16.0) + ((100.0 - enterprise_fit) * 0.18), 0.0, 100.0)
            opportunity_count = float(self._clamp(round(rng.gauss(3.0, 1.6)), 0.0, 10.0))

            competitive_advantage = self._clamp(
                18.0
                + (enterprise_fit * 0.33)
                + (trend_strength * 0.12)
                + max(0.0, 70.0 - competitor_density) * 0.18
                + rng.gauss(0.0, 7.5),
                0.0,
                100.0,
            )
            risk_score = self._clamp(
                95.0
                - (market_demand * 0.22)
                - (enterprise_fit * 0.28)
                + (competitor_density * 0.18)
                + rng.gauss(0.0, 10.0),
                0.0,
                100.0,
            )
            adoption_score = self._clamp((market_demand * 0.34) + (enterprise_fit * 0.28) + (trend_strength * 0.12) + rng.gauss(0.0, 6.0), 0.0, 100.0)
            revenue_opportunity = self._clamp(
                12.0 + (market_demand * 0.34) + (enterprise_fit * 0.26) + (adoption_score * 0.18) + (competitive_advantage * 0.14) + rng.gauss(0.0, 6.0),
                0.0,
                100.0,
            )
            launch_readiness = self._clamp(
                10.0
                + (market_demand * 0.23)
                + (enterprise_fit * 0.2)
                + (revenue_opportunity * 0.16)
                + (competitive_advantage * 0.17)
                + (trend_strength * 0.13)
                - (risk_score * 0.15)
                - (competitor_density * 0.05)
                + (opportunity_count * 1.7)
                + rng.gauss(0.0, 5.0),
                0.0,
                100.0,
            )

            compliance_complexity = self._clamp((risk_score * 0.36) + (competitor_density * 0.12) + rng.gauss(0.0, 7.0), 0.0, 100.0)
            security_risk = self._clamp((risk_score * 0.42) + rng.gauss(0.0, 8.5), 0.0, 100.0)
            adoption_difficulty = self._clamp(100.0 - (enterprise_fit * 0.45) + ((100.0 - market_demand) * 0.2) + rng.gauss(0.0, 7.0), 0.0, 100.0)
            integration_complexity = self._clamp(25.0 + rng.gauss(28.0, 14.0) + ((100.0 - enterprise_fit) * 0.1), 0.0, 100.0)
            market_competition = self._clamp((competitor_density * 0.78) + rng.gauss(0.0, 8.0), 0.0, 100.0)

            risk_composite = (
                (compliance_complexity * 0.24)
                + (security_risk * 0.28)
                + (adoption_difficulty * 0.18)
                + (integration_complexity * 0.16)
                + (market_competition * 0.14)
            )
            if risk_composite < 36.0:
                risk_label = 0
            elif risk_composite < 64.0:
                risk_label = 1
            else:
                risk_label = 2

            launch_x.append([
                market_demand,
                enterprise_fit,
                revenue_opportunity,
                competitive_advantage,
                risk_score,
                trend_strength,
                competitor_density,
                opportunity_count,
            ])
            launch_y.append(launch_readiness)

            risk_x.append([
                compliance_complexity,
                security_risk,
                adoption_difficulty,
                integration_complexity,
                market_competition,
            ])
            risk_y.append(risk_label)

            revenue_x.append([
                market_demand,
                enterprise_fit,
                adoption_score,
                competitive_advantage,
            ])
            revenue_y.append(revenue_opportunity)

        return {
            "launch_x": launch_x,
            "launch_y": launch_y,
            "risk_x": risk_x,
            "risk_y": risk_y,
            "revenue_x": revenue_x,
            "revenue_y": revenue_y,
        }

    def _feature_contributions(
        self,
        *,
        model_name: str,
        values: list[float],
        baseline: list[float],
        feature_names: list[str],
        predict_fn,
        target_label: str,
        positive_meaning: str,
    ) -> list[dict[str, Any]]:
        base_prediction = float(predict_fn(baseline))
        factors: list[dict[str, Any]] = []
        for index, feature_name in enumerate(feature_names):
            variant = list(values)
            variant[index] = baseline[index]
            variant_prediction = float(predict_fn(variant))
            signed_impact = float(base_prediction - variant_prediction)
            direction = "Positive" if signed_impact >= 0 else "Negative"
            factors.append(
                {
                    "factor": self._label_feature(feature_name),
                    "signed_impact": round(signed_impact, 2),
                    "impact": round(abs(signed_impact), 2),
                    "input_delta": round(float(values[index] - baseline[index]), 2),
                    "direction": direction,
                    "contribution_direction": direction,
                    "business_explanation": self._build_business_explanation(
                        feature_name=feature_name,
                        target_label=target_label,
                        positive_meaning=positive_meaning,
                        signed_impact=signed_impact,
                        actual_value=values[index],
                        baseline_value=baseline[index],
                        base_prediction=base_prediction,
                        variant_prediction=variant_prediction,
                    ),
                    "base_prediction": round(base_prediction, 2),
                    "variant_prediction": round(variant_prediction, 2),
                    "signed_display": f"{signed_impact:+.2f}",
                    "model": model_name,
                }
            )
        factors.sort(key=lambda item: abs(item["signed_impact"]), reverse=True)
        return factors

    def _build_business_explanation(
        self,
        *,
        feature_name: str,
        target_label: str,
        positive_meaning: str,
        signed_impact: float,
        actual_value: float,
        baseline_value: float,
        base_prediction: float,
        variant_prediction: float,
    ) -> str:
        feature_label = self._label_feature(feature_name)
        if signed_impact >= 0:
            return (
                f"{feature_label} increased {target_label} by {abs(signed_impact):.2f} points because the current value "
                f"({actual_value:.2f}) is above the baseline ({baseline_value:.2f}), which supports {positive_meaning}."
            )
        return (
            f"{feature_label} decreased {target_label} by {abs(signed_impact):.2f} points because the current value "
            f"({actual_value:.2f}) is below the baseline ({baseline_value:.2f}), which weakens {positive_meaning}."
        )

    def _label_feature(self, name: str) -> str:
        return {
            "market_demand": "Market Demand",
            "enterprise_fit": "Enterprise Fit",
            "revenue_opportunity": "Revenue Opportunity",
            "competitive_advantage": "Competitive Advantage",
            "risk_score": "Risk Score",
            "trend_strength": "Trend Strength",
            "competitor_density": "Competitor Density",
            "opportunity_count": "Opportunity Count",
            "compliance_complexity": "Compliance Complexity",
            "security_risk": "Security Risk",
            "adoption_difficulty": "Adoption Difficulty",
            "integration_complexity": "Integration Complexity",
            "market_competition": "Market Competition",
            "adoption_score": "Adoption Score",
        }.get(name, name.replace("_", " ").title())

    def _feature_means(self, rows: list[list[float]]) -> list[float]:
        if not rows:
            return []
        return [round(mean(column), 4) for column in zip(*rows, strict=False)]

    def _feature_stds(self, rows: list[list[float]]) -> list[float]:
        if not rows:
            return []
        return [round(pstdev(column), 4) for column in zip(*rows, strict=False)]

    def _average_abs_coefficients(self, coefficients: Any, feature_names: list[str]) -> dict[str, float]:
        result: dict[str, float] = {}
        for index, feature_name in enumerate(feature_names):
            if hasattr(coefficients, "__len__") and len(coefficients):
                value = coefficients
                if len(getattr(coefficients, "shape", [])) > 1:
                    value = [abs(row[index]) for row in coefficients]
                    result[self._label_feature(feature_name)] = round(sum(value) / max(1, len(value)), 4)
                else:
                    result[self._label_feature(feature_name)] = round(abs(float(coefficients[index])), 4)
        return result

    def _linear_importance(self, coefficients: Any, feature_names: list[str]) -> dict[str, float]:
        values = [abs(float(value)) for value in coefficients] if hasattr(coefficients, "__iter__") else []
        return {
            self._label_feature(feature_names[index]): round(values[index], 4)
            for index in range(min(len(feature_names), len(values)))
        }

    def _class_balance(self, labels: list[int]) -> dict[str, int]:
        counts = {"Low Risk": 0, "Medium Risk": 0, "High Risk": 0}
        mapping = {0: "Low Risk", 1: "Medium Risk", 2: "High Risk"}
        for label in labels:
            counts[mapping.get(int(label), "Medium Risk")] += 1
        return counts

    def _mae(self, expected: list[float], predicted: list[float]) -> float:
        if not expected:
            return 0.0
        return round(sum(abs(exp - pred) for exp, pred in zip(expected, predicted)) / len(expected), 4)

    def _safe_number(self, value: Any, default: float = 0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def _clamp(self, value: float, minimum: float, maximum: float) -> float:
        return max(minimum, min(maximum, value))


product_impact_ml_engine = ProductImpactMLEngine()
