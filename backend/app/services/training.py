from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score

from app.models import Patient

ARTIFACT_DIR = Path("artifacts")


def run_offline_training(patients: list[Patient], target_type: str, run_id: int) -> dict:
    """Train a baseline offline model and persist an artifact path + training metrics."""
    eligible = [patient for patient in patients if patient.has_historical_outcome in {True, False}]
    if len(eligible) < 8:
        return {
            "status": "skipped",
            "artifact_path": "",
            "metrics_json": json.dumps({"reason": "not_enough_labeled_patients", "sample_size": len(eligible)}),
        }

    x = np.array(
        [
            [patient.age, patient.bmi, patient.blood_pressure, patient.cholesterol, patient.glucose, int(patient.smoker)]
            for patient in eligible
        ],
        dtype=float,
    )
    y = np.array([int(patient.has_historical_outcome) for patient in eligible], dtype=int)

    model = LogisticRegression(max_iter=250, class_weight="balanced", random_state=42)
    model.fit(x, y)
    probabilities = model.predict_proba(x)[:, 1]

    roc_auc = float(roc_auc_score(y, probabilities)) if len(np.unique(y)) > 1 else 0.5
    pr_auc = float(average_precision_score(y, probabilities)) if len(np.unique(y)) > 1 else float(np.mean(y))

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    artifact_name = f"{target_type}_run_{run_id}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}.joblib"
    artifact_path = ARTIFACT_DIR / artifact_name
    joblib.dump(model, artifact_path)

    metrics = {
        "sample_size": len(eligible),
        "target_type": target_type,
        "model_family": "logistic_regression",
        "roc_auc": round(roc_auc, 4),
        "pr_auc": round(pr_auc, 4),
    }
    return {"status": "completed", "artifact_path": str(artifact_path), "metrics_json": json.dumps(metrics)}
