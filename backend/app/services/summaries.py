from __future__ import annotations

import json
from datetime import datetime, timezone

from app.models import Explanation, Patient, Prediction


def _parse_factor_labels(raw_value: str, max_items: int = 3) -> list[str]:
    try:
        parsed = json.loads(raw_value)
    except json.JSONDecodeError:
        return []
    labels = []
    for item in parsed[:max_items]:
        feature = str(item.get("feature", "")).replace("_", " ").strip()
        if feature:
            labels.append(feature.title())
    return labels


def build_patient_summary(patient: Patient, latest_prediction: Prediction | None, latest_explanation: Explanation | None) -> dict:
    risk_line = (
        f"Latest readmission risk is {latest_prediction.risk_score:.2f} ({latest_prediction.risk_category}) "
        f"with confidence {latest_prediction.confidence_score:.2f}."
        if latest_prediction
        else "No readmission prediction is available yet."
    )
    trend_line = (
        f"Review status is {patient.review_status} and assigned reviewer is {patient.assigned_reviewer or 'unassigned'}."
    )

    top_risk_drivers = _parse_factor_labels(latest_explanation.risk_factors) if latest_explanation else []
    protective_factors = _parse_factor_labels(latest_explanation.protective_factors) if latest_explanation else []

    follow_up_questions = [
        "Have there been medication changes in the last 24 hours?",
        "Are there any new symptoms or overnight deterioration concerns?",
        "Is discharge planning aligned with current risk and social support?",
    ]

    summary = f"{risk_line} {trend_line}"
    return {
        "patient_id": patient.id,
        "generated_at": datetime.now(timezone.utc),
        "summary": summary,
        "top_risk_drivers": top_risk_drivers,
        "protective_factors": protective_factors,
        "follow_up_questions": follow_up_questions,
    }


def build_handoff_summary(
    masked_identifiers: list[str], high_risk_count: int, monitored_count: int, escalated_count: int, panel_size: int
) -> dict:
    summary = (
        f"Shift handoff panel includes {panel_size} patients, with {high_risk_count} high risk, "
        f"{escalated_count} escalated, and {monitored_count} currently monitored."
    )
    return {
        "generated_at": datetime.now(timezone.utc),
        "panel_size": panel_size,
        "high_risk_count": high_risk_count,
        "monitored_count": monitored_count,
        "escalated_count": escalated_count,
        "summary": summary,
        "priority_patients": masked_identifiers[:10],
    }


def build_follow_up_recommendations(patient_id: int, risk_category: str) -> dict:
    base = [
        "Review medication adherence and recent regimen changes.",
        "Confirm follow-up appointment and care-transition plan.",
    ]
    if risk_category == "high":
        base = [
            "Escalate to clinician review within 2 hours.",
            "Obtain repeat vitals and key labs within shift.",
            "Consider case-manager outreach before discharge.",
        ] + base
    elif risk_category == "medium":
        base = [
            "Schedule same-day risk huddle review.",
            "Reassess risk after next observation update.",
        ] + base
    else:
        base = ["Continue routine monitoring cadence."] + base
    return {
        "patient_id": patient_id,
        "generated_at": datetime.now(timezone.utc),
        "risk_category": risk_category,
        "recommendations": base,
    }


def build_note_summary(patient_id: int, notes: list[str]) -> dict:
    if not notes:
        text = "No review notes are available for this patient."
    else:
        combined = " ".join(note.strip() for note in notes if note.strip())
        text = combined[:480]
        if len(combined) > 480:
            text += "..."
    return {
        "patient_id": patient_id,
        "generated_at": datetime.now(timezone.utc),
        "note_count": len(notes),
        "summary": text,
    }


def build_follow_up_questions(patient_id: int, risk_category: str) -> dict:
    common = [
        "Has there been a new symptom change in the past 12 hours?",
        "Are there unresolved barriers to safe discharge or follow-up?",
    ]
    if risk_category == "high":
        questions = [
            "Should this patient be escalated to rapid review now?",
            "Are any pending labs likely to change immediate management?",
        ] + common
    elif risk_category == "medium":
        questions = [
            "Do we need an additional observation cycle before disposition?",
            "Is medication reconciliation complete and confirmed?",
        ] + common
    else:
        questions = ["Can this patient remain on standard monitoring cadence?"] + common
    return {"patient_id": patient_id, "generated_at": datetime.now(timezone.utc), "questions": questions}
