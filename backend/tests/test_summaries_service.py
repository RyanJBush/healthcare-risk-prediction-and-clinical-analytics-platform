from app.models import Explanation, Patient, Prediction
from app.services import summaries


def _patient() -> Patient:
    return Patient(
        id=123,
        full_name="Jane Doe",
        masked_identifier="PAT-0123",
        age=58,
        bmi=31.1,
        blood_pressure=142.0,
        cholesterol=220.0,
        glucose=130.0,
        smoker=True,
        has_historical_outcome=True,
    )


def test_parse_factor_labels_handles_invalid_json() -> None:
    assert summaries._parse_factor_labels("not-json") == []  # noqa: SLF001
    assert summaries._parse_factor_labels('[{"feature":"blood_pressure"},{"feature":""}]') == ["Blood Pressure"]  # noqa: SLF001


def test_build_patient_summary_handles_missing_prediction_and_explanation() -> None:
    patient = _patient()
    summary = summaries.build_patient_summary(patient, latest_prediction=None, latest_explanation=None)

    assert summary["patient_id"] == patient.id
    assert "No readmission prediction is available yet." in summary["summary"]
    assert summary["top_risk_drivers"] == []
    assert summary["protective_factors"] == []
    assert len(summary["follow_up_questions"]) == 3


def test_build_patient_summary_includes_prediction_and_explanation_details() -> None:
    patient = _patient()
    prediction = Prediction(
        patient_id=patient.id,
        target_type="readmission",
        risk_score=0.81,
        baseline_risk_score=0.4,
        confidence_score=0.92,
        risk_category="high",
        threshold_used=0.55,
        reason_codes="[]",
    )
    explanation = Explanation(
        patient_id=patient.id,
        prediction_id=1,
        target_type="readmission",
        top_factors="[]",
        risk_factors='[{"feature":"blood_pressure"},{"feature":"glucose"}]',
        protective_factors='[{"feature":"bmi"}]',
    )

    summary = summaries.build_patient_summary(patient, latest_prediction=prediction, latest_explanation=explanation)

    assert "Latest readmission risk is 0.81 (high) with confidence 0.92." in summary["summary"]
    assert summary["top_risk_drivers"] == ["Blood Pressure", "Glucose"]
    assert summary["protective_factors"] == ["Bmi"]


def test_build_follow_up_recommendations_by_risk_category() -> None:
    high = summaries.build_follow_up_recommendations(1, "high")
    medium = summaries.build_follow_up_recommendations(1, "medium")
    low = summaries.build_follow_up_recommendations(1, "low")

    assert high["recommendations"][0].startswith("Escalate to clinician review")
    assert medium["recommendations"][0].startswith("Schedule same-day risk huddle review")
    assert low["recommendations"][0] == "Continue routine monitoring cadence."


def test_build_note_summary_handles_empty_and_truncates_long_text() -> None:
    empty = summaries.build_note_summary(1, [])
    long_note = "x" * 500
    truncated = summaries.build_note_summary(1, [long_note])

    assert empty["summary"] == "No review notes are available for this patient."
    assert truncated["note_count"] == 1
    assert len(truncated["summary"]) == 483
    assert truncated["summary"].endswith("...")


def test_build_follow_up_questions_by_risk_category() -> None:
    high = summaries.build_follow_up_questions(1, "high")
    medium = summaries.build_follow_up_questions(1, "medium")
    low = summaries.build_follow_up_questions(1, "low")

    assert high["questions"][0].startswith("Should this patient be escalated")
    assert medium["questions"][0].startswith("Do we need an additional observation cycle")
    assert low["questions"][0] == "Can this patient remain on standard monitoring cadence?"


def test_build_handoff_summary_limits_priority_patients() -> None:
    payload = summaries.build_handoff_summary([f"PAT-{i:04d}" for i in range(15)], 7, 3, 2, 15)

    assert payload["panel_size"] == 15
    assert payload["high_risk_count"] == 7
    assert len(payload["priority_patients"]) == 10
