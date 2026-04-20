from __future__ import annotations

import json
from functools import lru_cache

import numpy as np
import shap
from sklearn.datasets import make_classification
from xgboost import XGBClassifier

FEATURE_NAMES = ["age", "bmi", "blood_pressure", "cholesterol", "glucose", "smoker"]


@lru_cache(maxsize=1)
def get_model() -> XGBClassifier:
    X, y = make_classification(
        n_samples=500,
        n_features=len(FEATURE_NAMES),
        n_informative=4,
        n_redundant=0,
        random_state=42,
        class_sep=1.2,
    )
    model = XGBClassifier(
        n_estimators=60,
        max_depth=3,
        learning_rate=0.1,
        subsample=0.9,
        colsample_bytree=0.9,
        eval_metric="logloss",
        random_state=42,
    )
    model.fit(X, y)
    return model


def risk_category(score: float) -> str:
    if score < 0.35:
        return "low"
    if score < 0.7:
        return "medium"
    return "high"


def patient_to_vector(patient) -> np.ndarray:
    return np.array(
        [[patient.age, patient.bmi, patient.blood_pressure, patient.cholesterol, patient.glucose, float(patient.smoker)]],
        dtype=float,
    )


def predict_with_explanation(patient) -> tuple[float, str, str]:
    model = get_model()
    features = patient_to_vector(patient)
    score = float(model.predict_proba(features)[0][1])
    category = risk_category(score)

    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(features)
    values = shap_values[0] if isinstance(shap_values, np.ndarray) else shap_values[1][0]
    contributions = sorted(zip(FEATURE_NAMES, values, strict=True), key=lambda x: abs(float(x[1])), reverse=True)[:3]
    top_factors = json.dumps(
        [{"feature": feature, "impact": round(float(impact), 4)} for feature, impact in contributions]
    )
    return score, category, top_factors
