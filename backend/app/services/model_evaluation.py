from __future__ import annotations

import numpy as np
from sklearn.calibration import calibration_curve
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss

from app.models import Patient
from app.services.feature_engineering import build_feature_matrix


def calibration_metrics(patients: list[Patient]) -> dict[str, list[float] | float]:
    eligible = [patient for patient in patients if patient.has_historical_outcome in {True, False}]
    if len(eligible) < 10:
        return {"fraction_of_positives": [], "mean_predicted_value": [], "brier_score": 0.0}

    x = build_feature_matrix(eligible)
    y = np.array([1 if patient.has_historical_outcome else 0 for patient in eligible], dtype=int)
    if len(np.unique(y)) < 2:
        return {"fraction_of_positives": [], "mean_predicted_value": [], "brier_score": 0.0}

    model = LogisticRegression(max_iter=200, class_weight="balanced", random_state=42)
    model.fit(x, y)
    y_prob = model.predict_proba(x)[:, 1]

    frac_pos, mean_pred = calibration_curve(y, y_prob, n_bins=10)
    brier = float(brier_score_loss(y, y_prob))
    return {
        "fraction_of_positives": [float(v) for v in frac_pos],
        "mean_predicted_value": [float(v) for v in mean_pred],
        "brier_score": round(brier, 4),
    }
