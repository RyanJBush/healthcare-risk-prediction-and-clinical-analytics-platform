from __future__ import annotations

import numpy as np

from app.models import Patient

FEATURE_COLUMNS = [
    "age",
    "bmi",
    "blood_pressure",
    "cholesterol",
    "glucose",
    "smoker",
    "condition_hypertension",
    "condition_obesity",
    "condition_hyperglycemia",
    "condition_hyperlipidemia",
    "review_escalation_signal",
    "condition_burden_index",
    "metabolic_risk_index",
    "vitals_instability_index",
    "lifestyle_risk_index",
]

_BOUNDS = {
    "age": (18.0, 95.0),
    "bmi": (16.0, 45.0),
    "blood_pressure": (90.0, 190.0),
    "cholesterol": (120.0, 320.0),
    "glucose": (70.0, 260.0),
}

_REVIEW_SIGNAL = {
    "new": 0.05,
    "reviewed": 0.2,
    "monitored": 0.7,
    "escalated": 1.0,
}


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return min(high, max(low, value))


def _normalize(feature: str, value: float) -> float:
    low, high = _BOUNDS[feature]
    return _clamp((value - low) / (high - low))


def build_feature_vector(patient: Patient) -> dict[str, float]:
    age = float(patient.age)
    bmi = float(patient.bmi)
    blood_pressure = float(patient.blood_pressure)
    cholesterol = float(patient.cholesterol)
    glucose = float(patient.glucose)
    smoker = float(bool(patient.smoker))

    condition_hypertension = 1.0 if blood_pressure >= 140 else 0.0
    condition_obesity = 1.0 if bmi >= 30 else 0.0
    condition_hyperglycemia = 1.0 if glucose >= 126 else 0.0
    condition_hyperlipidemia = 1.0 if cholesterol >= 240 else 0.0
    review_escalation_signal = float(_REVIEW_SIGNAL.get(patient.review_status or "new", 0.1))

    condition_count = condition_hypertension + condition_obesity + condition_hyperglycemia + condition_hyperlipidemia
    condition_burden_index = round(_clamp(condition_count / 4.0), 4)
    metabolic_risk_index = round(
        _clamp((_normalize("bmi", bmi) + _normalize("cholesterol", cholesterol) + _normalize("glucose", glucose)) / 3.0), 4
    )
    vitals_instability_index = round(
        _clamp((_normalize("blood_pressure", blood_pressure) + _normalize("glucose", glucose)) / 2.0), 4
    )
    lifestyle_risk_index = round(_clamp((smoker * 0.65) + (_normalize("age", age) * 0.35)), 4)

    return {
        "age": age,
        "bmi": bmi,
        "blood_pressure": blood_pressure,
        "cholesterol": cholesterol,
        "glucose": glucose,
        "smoker": smoker,
        "condition_hypertension": condition_hypertension,
        "condition_obesity": condition_obesity,
        "condition_hyperglycemia": condition_hyperglycemia,
        "condition_hyperlipidemia": condition_hyperlipidemia,
        "review_escalation_signal": review_escalation_signal,
        "condition_burden_index": condition_burden_index,
        "metabolic_risk_index": metabolic_risk_index,
        "vitals_instability_index": vitals_instability_index,
        "lifestyle_risk_index": lifestyle_risk_index,
    }


def build_feature_matrix(patients: list[Patient]) -> np.ndarray:
    return np.array(
        [[build_feature_vector(patient)[column] for column in FEATURE_COLUMNS] for patient in patients],
        dtype=float,
    )
