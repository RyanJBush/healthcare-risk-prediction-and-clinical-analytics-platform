from app.models import Patient
from app.services.risk_models import _risk_category, compare_patient_risk_models, model_feature_importance_snapshot


def _patient(pid: int, high_risk: bool) -> Patient:
    return Patient(
        id=pid,
        full_name=f"Patient {pid}",
        masked_identifier=f"PAT-{pid:04d}",
        age=72 if high_risk else 34,
        bmi=34.0 if high_risk else 22.0,
        blood_pressure=165.0 if high_risk else 118.0,
        cholesterol=260.0 if high_risk else 172.0,
        glucose=210.0 if high_risk else 95.0,
        smoker=high_risk,
        has_historical_outcome=high_risk,
    )


def test_compare_patient_risk_models_returns_both_models() -> None:
    training = [_patient(i, high_risk=i % 2 == 0) for i in range(1, 15)]
    target = _patient(99, high_risk=True)

    predictions = compare_patient_risk_models(training + [target], target)

    names = {prediction.model_name for prediction in predictions}
    assert names == {"logistic_regression", "random_forest"}
    assert all(0.0 <= prediction.risk_score <= 1.0 for prediction in predictions)
    assert all(prediction.risk_category in {"low", "medium", "high"} for prediction in predictions)
    assert all(len(prediction.top_contributing_features) >= 1 for prediction in predictions)


def test_risk_category_boundaries() -> None:
    assert _risk_category(0.80) == "high"
    assert _risk_category(0.60) == "medium"
    assert _risk_category(0.40) == "low"


def test_compare_patient_risk_models_rejects_unknown_target() -> None:
    training = [_patient(i, high_risk=i % 2 == 0) for i in range(1, 15)]
    target = _patient(99, high_risk=True)

    predictions = compare_patient_risk_models(training + [target], target, target_type="unknown_target")

    assert predictions == []


def test_model_feature_importance_snapshot_returns_baseline_models() -> None:
    training = [_patient(i, high_risk=i % 2 == 0) for i in range(1, 15)]

    snapshot = model_feature_importance_snapshot(training, target_type="readmission")

    assert {"logistic_regression", "random_forest"}.issubset(snapshot.keys())
    assert all(len(features) >= 1 for features in snapshot.values())
