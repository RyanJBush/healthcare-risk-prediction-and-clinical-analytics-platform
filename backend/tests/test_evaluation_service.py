from datetime import datetime, timedelta, timezone

import numpy as np
import pytest

from app.models import Patient
from app.services import evaluation


def _patient(idx: int, *, outcome: bool, smoker: bool) -> Patient:
    return Patient(
        id=idx,
        full_name=f"Patient {idx}",
        masked_identifier=f"PAT-{idx:04d}",
        age=40 + idx,
        bmi=25.0 + (idx * 0.1),
        blood_pressure=120.0 + idx,
        cholesterol=180.0 + idx,
        glucose=100.0 + idx,
        smoker=smoker,
        has_historical_outcome=outcome,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(days=idx),
    )


class _StubModel:
    def __init__(self, probabilities: list[float]) -> None:
        self._probabilities = np.array(probabilities, dtype=float)

    def fit(self, x_train, y_train) -> "_StubModel":  # noqa: ANN001
        assert len(x_train) == len(y_train)
        return self

    def predict_proba(self, x_test) -> np.ndarray:  # noqa: ANN001
        probs = self._probabilities[: len(x_test)]
        return np.column_stack([1 - probs, probs])


def test_time_aware_split_handles_single_patient() -> None:
    only = _patient(1, outcome=True, smoker=False)
    train, test = evaluation._time_aware_split([only])  # noqa: SLF001

    assert len(train) == 1
    assert len(test) == 1
    assert train[0] is only
    assert test[0] is only


def test_safe_auc_helpers_fallback_on_single_class() -> None:
    y_true = np.array([1, 1, 1], dtype=int)
    y_score = np.array([0.6, 0.7, 0.8], dtype=float)

    assert evaluation._safe_roc_auc(y_true, y_score) == 0.5  # noqa: SLF001
    assert evaluation._safe_pr_auc(y_true, y_score) == 1.0  # noqa: SLF001


def test_evaluate_models_returns_empty_for_small_or_single_class_training_set() -> None:
    small = [_patient(i, outcome=(i % 2 == 0), smoker=False) for i in range(1, 8)]
    small_result = evaluation.evaluate_models(small)
    assert small_result["models"] == []

    all_positive = [_patient(i, outcome=True, smoker=(i % 2 == 0)) for i in range(1, 11)]
    single_class_result = evaluation.evaluate_models(all_positive)
    assert single_class_result["models"] == []


def test_evaluate_models_returns_sorted_metrics_and_subgroups(monkeypatch) -> None:  # noqa: ANN001
    patients = [_patient(i, outcome=(i % 2 == 0), smoker=(i % 3 == 0)) for i in range(1, 11)]
    patients[-2].smoker = True
    patients[-2].has_historical_outcome = True
    patients[-1].smoker = False
    patients[-1].has_historical_outcome = False

    monkeypatch.setattr(
        evaluation,
        "_model_candidates",
        lambda: [
            ("higher_cost", _StubModel([0.9, 0.8])),
            ("lower_cost", _StubModel([0.6, 0.2])),
        ],
    )

    result = evaluation.evaluate_models(patients, threshold=0.55)

    assert [model["model_name"] for model in result["models"]] == ["lower_cost", "higher_cost"]
    assert result["models"][0]["cost_score"] <= result["models"][1]["cost_score"]
    assert result["subgroup_outcomes"]["smoker"] == 1.0
    assert result["subgroup_outcomes"]["non_smoker"] == 0.0
    assert result["threshold_sweep"] == [
        {"threshold": 0.4, "alerts": 2},
        {"threshold": 0.5, "alerts": 2},
        {"threshold": 0.6, "alerts": 2},
        {"threshold": 0.7, "alerts": 2},
    ]


def test_model_candidates_include_expected_baselines() -> None:
    models = evaluation._model_candidates()  # noqa: SLF001
    names = [name for name, _ in models]

    assert "logistic_regression" in names
    assert "random_forest" in names
    assert ("xgboost" in names) == (evaluation.XGBClassifier is not None)


def test_evaluate_models_returns_empty_with_no_candidates(monkeypatch: pytest.MonkeyPatch) -> None:
    patients = [_patient(i, outcome=(i % 2 == 0), smoker=(i % 3 == 0)) for i in range(1, 11)]
    monkeypatch.setattr(evaluation, "_model_candidates", lambda: [])

    result = evaluation.evaluate_models(patients, threshold=0.55)

    assert result["models"] == []
    assert result["threshold_sweep"] == [
        {"threshold": 0.4, "alerts": 0},
        {"threshold": 0.5, "alerts": 0},
        {"threshold": 0.6, "alerts": 0},
        {"threshold": 0.7, "alerts": 0},
    ]
