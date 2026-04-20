from __future__ import annotations

from dataclasses import dataclass
import math

FEATURE_NAMES = ["age", "bmi", "blood_pressure", "cholesterol", "glucose", "smoker"]

TARGET_CONFIGS = {
    "readmission": {
        "weights": {"age": 0.9, "bmi": 0.45, "blood_pressure": 0.5, "cholesterol": 0.2, "glucose": 0.6, "smoker": 0.55},
        "intercept": -1.9,
        "thresholds": {"medium": 0.45, "high": 0.72},
        "summary": "30-day readmission risk",
    },
    "deterioration": {
        "weights": {"age": 0.7, "bmi": 0.2, "blood_pressure": 0.65, "cholesterol": 0.15, "glucose": 0.75, "smoker": 0.45},
        "intercept": -1.8,
        "thresholds": {"medium": 0.48, "high": 0.75},
        "summary": "Inpatient deterioration risk",
    },
    "adverse_event": {
        "weights": {"age": 0.8, "bmi": 0.3, "blood_pressure": 0.4, "cholesterol": 0.45, "glucose": 0.55, "smoker": 0.6},
        "intercept": -2.0,
        "thresholds": {"medium": 0.42, "high": 0.7},
        "summary": "Adverse event risk",
    },
}

NORMALIZATION = {
    "age": (20, 90),
    "bmi": (15, 45),
    "blood_pressure": (90, 180),
    "cholesterol": (120, 300),
    "glucose": (70, 240),
    "smoker": (0, 1),
}

BASELINE_WEIGHTS = {
    "age": 0.28,
    "blood_pressure": 0.26,
    "glucose": 0.22,
    "smoker": 0.24,
}

PROTECTIVE_CUTOFF = {
    "age": 0.35,
    "bmi": 0.45,
    "blood_pressure": 0.4,
    "cholesterol": 0.4,
    "glucose": 0.4,
    "smoker": 0.5,
}


@dataclass
class TieredPredictionResult:
    target_type: str
    risk_score: float
    baseline_risk_score: float
    confidence_score: float
    risk_category: str
    threshold_used: float
    reason_codes: list[str]
    top_factors: list[dict[str, float | str]]
    risk_factors: list[dict[str, float | str]]
    protective_factors: list[dict[str, float | str]]
    plain_summary: str
    rationale_summary: str
    provenance: str


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return min(high, max(low, value))


def _sigmoid(value: float) -> float:
    if value >= 0:
        z = math.exp(-value)
        return 1.0 / (1.0 + z)
    z = math.exp(value)
    return z / (1.0 + z)


def _normalize(feature: str, value: float) -> float:
    low, high = NORMALIZATION[feature]
    return _clamp((value - low) / (high - low))


def _risk_category(score: float, medium_threshold: float, high_threshold: float) -> str:
    if score >= high_threshold:
        return "high"
    if score >= medium_threshold:
        return "medium"
    return "low"


def _confidence(score: float, alert_threshold: float) -> float:
    distance = abs(score - alert_threshold)
    return round(_clamp(0.5 + (distance * 1.4), 0.5, 0.99), 4)


def _feature_values(patient) -> dict[str, float]:
    return {
        "age": float(patient.age),
        "bmi": float(patient.bmi),
        "blood_pressure": float(patient.blood_pressure),
        "cholesterol": float(patient.cholesterol),
        "glucose": float(patient.glucose),
        "smoker": float(bool(patient.smoker)),
    }


def _feature_label(feature: str) -> str:
    return feature.replace("_", " ").title()


def _reason_code(feature: str, contribution: float) -> str:
    direction = "ELEVATED" if contribution >= 0 else "LOWERED"
    return f"{feature.upper()}_{direction}"


def _build_clinician_summary(target_type: str, category: str, score: float, confidence: float, top_feature: str) -> str:
    return (
        f"{TARGET_CONFIGS[target_type]['summary']} is {category} "
        f"(score {score:.2f}, confidence {confidence:.2f}) with strongest signal from {_feature_label(top_feature)}."
    )


def _build_rationale(target_type: str, reason_codes: list[str]) -> str:
    if not reason_codes:
        return f"No dominant driver identified for {target_type}."
    joined = ", ".join(reason_codes[:3])
    return f"Risk rationale for {target_type}: {joined}."


def _baseline_score(features: dict[str, float]) -> float:
    baseline = (
        BASELINE_WEIGHTS["age"] * _normalize("age", features["age"]) +
        BASELINE_WEIGHTS["blood_pressure"] * _normalize("blood_pressure", features["blood_pressure"]) +
        BASELINE_WEIGHTS["glucose"] * _normalize("glucose", features["glucose"]) +
        BASELINE_WEIGHTS["smoker"] * features["smoker"]
    )
    return round(_clamp(baseline), 4)


def predict_tiered(patient) -> list[TieredPredictionResult]:
    feature_values = _feature_values(patient)
    normalized = {feature: _normalize(feature, value) for feature, value in feature_values.items()}
    baseline = _baseline_score(feature_values)
    results: list[TieredPredictionResult] = []

    for target_type, config in TARGET_CONFIGS.items():
        contributions = {
            feature: normalized[feature] * float(weight)
            for feature, weight in config["weights"].items()
        }
        raw_score = float(config["intercept"]) + sum(contributions.values())
        score = round(_clamp(_sigmoid(raw_score)), 4)
        medium_threshold = float(config["thresholds"]["medium"])
        high_threshold = float(config["thresholds"]["high"])
        category = _risk_category(score, medium_threshold, high_threshold)
        confidence = _confidence(score, medium_threshold)

        ranked = sorted(contributions.items(), key=lambda item: abs(item[1]), reverse=True)
        top = ranked[:3]

        reason_codes = [_reason_code(feature, value) for feature, value in top]
        top_factors = [
            {"feature": feature, "impact": round(float(value), 4)} for feature, value in top
        ]

        risk_factors = [
            {"feature": feature, "impact": round(float(value), 4)}
            for feature, value in ranked
            if normalized[feature] >= PROTECTIVE_CUTOFF[feature]
        ][:3]

        protective_factors = [
            {"feature": feature, "impact": round(float(value), 4)}
            for feature, value in ranked
            if normalized[feature] < PROTECTIVE_CUTOFF[feature]
        ][:3]

        plain_summary = _build_clinician_summary(target_type, category, score, confidence, top[0][0])
        rationale_summary = _build_rationale(target_type, reason_codes)

        results.append(
            TieredPredictionResult(
                target_type=target_type,
                risk_score=score,
                baseline_risk_score=baseline,
                confidence_score=confidence,
                risk_category=category,
                threshold_used=medium_threshold,
                reason_codes=reason_codes,
                top_factors=top_factors,
                risk_factors=risk_factors,
                protective_factors=protective_factors,
                plain_summary=plain_summary,
                rationale_summary=rationale_summary,
                provenance="tiered-risk-engine-v1",
            )
        )

    return results
