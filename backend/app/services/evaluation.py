from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from app.models import Patient

try:
    from xgboost import XGBClassifier
except Exception:  # pragma: no cover - optional dependency guard
    XGBClassifier = None

FEATURE_COLUMNS = ["age", "bmi", "blood_pressure", "cholesterol", "glucose", "smoker"]
DEFAULT_THRESHOLD = 0.55
FALSE_NEGATIVE_COST = 5.0
FALSE_POSITIVE_COST = 1.0


def _as_matrix(patients: list[Patient]) -> tuple[np.ndarray, np.ndarray]:
    x = np.array(
        [
            [
                float(patient.age),
                float(patient.bmi),
                float(patient.blood_pressure),
                float(patient.cholesterol),
                float(patient.glucose),
                float(bool(patient.smoker)),
            ]
            for patient in patients
        ],
        dtype=float,
    )
    y = np.array([1 if patient.has_historical_outcome else 0 for patient in patients], dtype=int)
    return x, y


def _time_aware_split(patients: list[Patient]) -> tuple[list[Patient], list[Patient]]:
    ordered = sorted(patients, key=lambda patient: patient.created_at)
    split_idx = max(1, int(len(ordered) * 0.8))
    train = ordered[:split_idx]
    test = ordered[split_idx:]
    if not test:
        test = ordered[-1:]
        train = ordered[:-1] or ordered[-1:]
    return train, test


def _model_candidates():
    models = [
        ("logistic_regression", LogisticRegression(max_iter=200, class_weight="balanced", random_state=42)),
        ("random_forest", RandomForestClassifier(n_estimators=120, class_weight="balanced", random_state=42)),
    ]
    if XGBClassifier is not None:
        models.append(
            (
                "xgboost",
                XGBClassifier(
                    n_estimators=100,
                    max_depth=4,
                    learning_rate=0.08,
                    subsample=0.9,
                    colsample_bytree=0.9,
                    random_state=42,
                    eval_metric="logloss",
                ),
            )
        )
    return models


def _safe_roc_auc(y_true: np.ndarray, y_score: np.ndarray) -> float:
    if len(np.unique(y_true)) < 2:
        return 0.5
    return float(roc_auc_score(y_true, y_score))


def _safe_pr_auc(y_true: np.ndarray, y_score: np.ndarray) -> float:
    if len(np.unique(y_true)) < 2:
        return float(np.mean(y_true))
    return float(average_precision_score(y_true, y_score))


def evaluate_models(patients: list[Patient], threshold: float = DEFAULT_THRESHOLD) -> dict:
    eligible = [patient for patient in patients if patient.has_historical_outcome in {True, False}]
    if len(eligible) < 8:
        return {
            "split": "time_aware_80_20",
            "evaluated_at": datetime.now(timezone.utc),
            "models": [],
        }

    train_patients, test_patients = _time_aware_split(eligible)
    x_train, y_train = _as_matrix(train_patients)
    x_test, y_test = _as_matrix(test_patients)

    if len(np.unique(y_train)) < 2:
        return {
            "split": "time_aware_80_20",
            "evaluated_at": datetime.now(timezone.utc),
            "models": [],
        }

    model_results: list[dict] = []
    reference_probabilities: np.ndarray | None = None
    for model_name, model in _model_candidates():
        model.fit(x_train, y_train)
        probabilities = model.predict_proba(x_test)[:, 1]
        if reference_probabilities is None:
            reference_probabilities = probabilities
        labels = (probabilities >= threshold).astype(int)

        false_negatives = int(np.sum((y_test == 1) & (labels == 0)))
        false_positives = int(np.sum((y_test == 0) & (labels == 1)))
        cost_score = float((false_negatives * FALSE_NEGATIVE_COST) + (false_positives * FALSE_POSITIVE_COST))

        model_results.append(
            {
                "model_name": model_name,
                "sample_size": int(len(y_test)),
                "positive_rate": round(float(np.mean(y_test)), 4),
                "roc_auc": round(_safe_roc_auc(y_test, probabilities), 4),
                "pr_auc": round(_safe_pr_auc(y_test, probabilities), 4),
                "precision": round(float(precision_score(y_test, labels, zero_division=0)), 4),
                "recall": round(float(recall_score(y_test, labels, zero_division=0)), 4),
                "f1": round(float(f1_score(y_test, labels, zero_division=0)), 4),
                "brier": round(float(brier_score_loss(y_test, probabilities)), 4),
                "false_negative_count": false_negatives,
                "false_positive_count": false_positives,
                "threshold": threshold,
                "cost_score": round(cost_score, 4),
            }
        )

    by_smoker = {
        "smoker": round(float(np.mean([patient.has_historical_outcome for patient in test_patients if patient.smoker])), 4)
        if any(patient.smoker for patient in test_patients)
        else 0.0,
        "non_smoker": round(float(np.mean([patient.has_historical_outcome for patient in test_patients if not patient.smoker])), 4)
        if any(not patient.smoker for patient in test_patients)
        else 0.0,
    }
    threshold_sweep = []
    for candidate in (0.4, 0.5, 0.6, 0.7):
        if reference_probabilities is None:
            alerts = 0
        else:
            alerts = int(np.sum(reference_probabilities >= candidate))
        threshold_sweep.append({"threshold": round(candidate, 2), "alerts": alerts})

    return {
        "split": "time_aware_80_20",
        "evaluated_at": datetime.now(timezone.utc),
        "models": sorted(model_results, key=lambda row: row["cost_score"]),
        "subgroup_outcomes": by_smoker,
        "threshold_sweep": threshold_sweep,
    }
