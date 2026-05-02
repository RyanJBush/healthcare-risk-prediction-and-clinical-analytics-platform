from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression

from app.models import Patient

FEATURE_COLUMNS = ["age", "bmi", "blood_pressure", "cholesterol", "glucose", "smoker"]
MODEL_THRESHOLD = 0.55


@dataclass
class ModelRiskPrediction:
    model_name: str
    risk_score: float
    risk_category: str


def _risk_category(score: float, threshold: float = MODEL_THRESHOLD) -> str:
    if score >= 0.75:
        return "high"
    if score >= threshold:
        return "medium"
    return "low"


def _matrix(patients: list[Patient]) -> np.ndarray:
    return np.array(
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


def compare_patient_risk_models(patients: list[Patient], patient: Patient) -> list[ModelRiskPrediction]:
    # Exclude the index patient from training to avoid target leakage in patient-level scoring.
    eligible = [entry for entry in patients if entry.id != patient.id and entry.has_historical_outcome in {True, False}]
    if len(eligible) < 8:
        return []

    x_train = _matrix(eligible)
    y_train = np.array([int(entry.has_historical_outcome) for entry in eligible], dtype=int)
    if len(np.unique(y_train)) < 2:
        return []

    x_target = _matrix([patient])
    models = [
        ("logistic_regression", LogisticRegression(max_iter=250, class_weight="balanced", random_state=42)),
        ("random_forest", RandomForestClassifier(n_estimators=120, class_weight="balanced", random_state=42)),
    ]

    predictions: list[ModelRiskPrediction] = []
    for model_name, model in models:
        model.fit(x_train, y_train)
        score = float(model.predict_proba(x_target)[0][1])
        predictions.append(
            ModelRiskPrediction(
                model_name=model_name,
                risk_score=round(score, 4),
                risk_category=_risk_category(score),
            )
        )
    return predictions
