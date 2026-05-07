from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from app.models import Patient
from app.services.feature_engineering import FEATURE_COLUMNS, build_feature_matrix, build_feature_vector

MODEL_THRESHOLD = 0.55
HIGH_RISK_THRESHOLD = 0.75
MIN_TRAINING_PATIENTS = 8


@dataclass
class ModelRiskPrediction:
    model_name: str
    risk_score: float
    risk_category: str
    top_contributing_features: list[dict[str, float | str]]


def _risk_category(score: float, threshold: float = MODEL_THRESHOLD) -> str:
    if score >= HIGH_RISK_THRESHOLD:
        return "high"
    if score >= threshold:
        return "medium"
    return "low"


def _matrix(patients: list[Patient]) -> np.ndarray:
    return build_feature_matrix(patients)


def _build_models() -> list[tuple[str, object]]:
    # Logistic regression is the interpretable baseline model.
    logistic_baseline = Pipeline(
        steps=[
            ("scaler", StandardScaler()),
            ("model", LogisticRegression(max_iter=500, class_weight="balanced", random_state=42)),
        ]
    )
    tree_model = RandomForestClassifier(
        n_estimators=200,
        max_depth=6,
        min_samples_leaf=2,
        class_weight="balanced",
        random_state=42,
    )
    return [
        ("logistic_regression", logistic_baseline),
        ("random_forest", tree_model),
    ]


def _model_for_feature_importance(model: object) -> object:
    if isinstance(model, Pipeline):
        return model.named_steps["model"]
    return model


def _feature_importance_map(model: object) -> dict[str, float]:
    estimator = _model_for_feature_importance(model)
    if hasattr(estimator, "coef_"):
        coefficients = np.asarray(estimator.coef_).ravel()
        return {
            feature: float(coefficients[idx]) if idx < len(coefficients) else 0.0
            for idx, feature in enumerate(FEATURE_COLUMNS)
        }
    if hasattr(estimator, "feature_importances_"):
        importances = np.asarray(estimator.feature_importances_).ravel()
        return {
            feature: float(importances[idx]) if idx < len(importances) else 0.0
            for idx, feature in enumerate(FEATURE_COLUMNS)
        }
    return {feature: 0.0 for feature in FEATURE_COLUMNS}


def _top_contributing_features(importance: dict[str, float], patient: Patient, limit: int = 4) -> list[dict[str, float | str]]:
    values = build_feature_vector(patient)
    ranked = sorted(
        (
            (feature, float(weight) * float(values.get(feature, 0.0)))
            for feature, weight in importance.items()
        ),
        key=lambda item: abs(item[1]),
        reverse=True,
    )
    return [
        {"feature": feature, "impact": round(impact, 4)}
        for feature, impact in ranked[:limit]
    ]


def model_feature_importance_snapshot(
    patients: list[Patient],
    target_type: str = "readmission",
    limit: int = 6,
) -> dict[str, list[dict[str, float | str]]]:
    if target_type not in {"readmission", "deterioration", "adverse_event"}:
        return {}
    eligible = [entry for entry in patients if entry.has_historical_outcome in {True, False}]
    if len(eligible) < MIN_TRAINING_PATIENTS:
        return {}
    x_train = _matrix(eligible)
    y_train = np.array([int(entry.has_historical_outcome) for entry in eligible], dtype=int)
    if len(np.unique(y_train)) < 2:
        return {}

    snapshots: dict[str, list[dict[str, float | str]]] = {}
    for model_name, model in _build_models():
        model.fit(x_train, y_train)
        weights = _feature_importance_map(model)
        ranked = sorted(weights.items(), key=lambda item: abs(item[1]), reverse=True)[:limit]
        snapshots[model_name] = [
            {"feature": feature, "importance": round(float(value), 4)}
            for feature, value in ranked
        ]
    return snapshots


def compare_patient_risk_models(
    patients: list[Patient],
    patient: Patient,
    target_type: str = "readmission",
) -> list[ModelRiskPrediction]:
    if target_type not in {"readmission", "deterioration", "adverse_event"}:
        return []

    eligible = [entry for entry in patients if entry.id != patient.id and entry.has_historical_outcome in {True, False}]
    if len(eligible) < MIN_TRAINING_PATIENTS:
        return []

    x_train = _matrix(eligible)
    y_train = np.array([int(entry.has_historical_outcome) for entry in eligible], dtype=int)
    if len(np.unique(y_train)) < 2:
        return []

    x_target = _matrix([patient])
    predictions: list[ModelRiskPrediction] = []
    for model_name, model in _build_models():
        model.fit(x_train, y_train)
        score = float(model.predict_proba(x_target)[0][1])
        contributors = _top_contributing_features(_feature_importance_map(model), patient)
        predictions.append(
            ModelRiskPrediction(
                model_name=model_name,
                risk_score=round(score, 4),
                risk_category=_risk_category(score),
                top_contributing_features=contributors,
            )
        )
    return predictions
