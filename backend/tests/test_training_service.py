import json
from datetime import datetime, timezone

import numpy as np

from app.models import Patient
from app.services import training


def _patient(idx: int, *, outcome: bool) -> Patient:
    return Patient(
        id=idx,
        full_name=f"Patient {idx}",
        masked_identifier=f"PAT-{idx:04d}",
        age=35 + idx,
        bmi=24.0 + idx,
        blood_pressure=115.0 + idx,
        cholesterol=170.0 + idx,
        glucose=95.0 + idx,
        smoker=(idx % 2 == 0),
        has_historical_outcome=outcome,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


def test_run_offline_training_skips_when_not_enough_labeled_patients(tmp_path) -> None:  # noqa: ARG001
    result = training.run_offline_training([_patient(i, outcome=(i % 2 == 0)) for i in range(1, 7)], "readmission", run_id=1)

    assert result["status"] == "skipped"
    assert result["artifact_path"] == ""
    assert json.loads(result["metrics_json"]) == {"reason": "not_enough_labeled_patients", "sample_size": 6}


def test_run_offline_training_handles_single_class_with_stubbed_model(tmp_path, monkeypatch) -> None:  # noqa: ANN001
    class _StubLogisticRegression:
        def __init__(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003, ARG002
            pass

        def fit(self, x, y):  # noqa: ANN001, ANN201
            assert len(x) == len(y)
            return self

        def predict_proba(self, x) -> np.ndarray:  # noqa: ANN001
            return np.column_stack([np.zeros(len(x)), np.ones(len(x))])

    monkeypatch.setattr(training, "LogisticRegression", _StubLogisticRegression)
    monkeypatch.setattr(training, "ARTIFACT_DIR", tmp_path)

    patients = [_patient(i, outcome=True) for i in range(1, 10)]
    result = training.run_offline_training(patients, "readmission", run_id=2)
    metrics = json.loads(result["metrics_json"])

    assert result["status"] == "completed"
    assert metrics["sample_size"] == 9
    assert metrics["roc_auc"] == 0.5
    assert metrics["pr_auc"] == 1.0
    assert result["artifact_path"].endswith(".joblib")


def test_run_offline_training_completes_and_writes_artifact(tmp_path, monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setattr(training, "ARTIFACT_DIR", tmp_path)

    patients = [_patient(i, outcome=(i % 2 == 0)) for i in range(1, 11)]
    result = training.run_offline_training(patients, "readmission", run_id=3)
    metrics = json.loads(result["metrics_json"])

    assert result["status"] == "completed"
    assert metrics["sample_size"] == 10
    assert metrics["target_type"] == "readmission"
    assert metrics["model_family"] == "logistic_regression"
    assert 0.0 <= metrics["roc_auc"] <= 1.0
    assert 0.0 <= metrics["pr_auc"] <= 1.0
    assert tmp_path.joinpath(result["artifact_path"].split("/")[-1]).exists()
