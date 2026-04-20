# ruff: noqa: E402
import os
from pathlib import Path

from fastapi.testclient import TestClient

_db_url = os.getenv("DATABASE_URL", "")
if _db_url.startswith("sqlite") and "///" in _db_url:
    db_path = _db_url.split("///", maxsplit=1)[1]
    if db_path.startswith("./"):
        db_file = Path(__file__).resolve().parents[1] / db_path[2:]
    else:
        db_file = Path(db_path)
    if db_file.exists():
        db_file.unlink()

from app.main import app


def auth_headers(username: str = "clinician", password: str = "clinician123") -> dict[str, str]:
    with TestClient(app) as client:
        response = client.post("/auth/login", json={"username": username, "password": password})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_health() -> None:
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_phase1_tiered_prediction_and_workflow_flow() -> None:
    clinician_headers = auth_headers()
    analyst_headers = auth_headers("analyst", "analyst123")

    with TestClient(app) as client:
        create_resp = client.post(
            "/api/patients",
            headers=clinician_headers,
            json={
                "full_name": "Jane Doe",
                "age": 59,
                "bmi": 31.2,
                "blood_pressure": 142,
                "cholesterol": 220,
                "glucose": 128,
                "smoker": True,
                "has_historical_outcome": True,
            },
        )
        assert create_resp.status_code == 201
        patient = create_resp.json()
        patient_id = patient["id"]
        assert patient["masked_identifier"].startswith("PAT-")

        tiered_resp = client.post("/api/predict/tiered", headers=clinician_headers, json={"patient_id": patient_id})
        assert tiered_resp.status_code == 200
        tiered_body = tiered_resp.json()
        assert tiered_body["patient_id"] == patient_id
        assert {item["target_type"] for item in tiered_body["predictions"]} == {"readmission", "deterioration", "adverse_event"}

        preds_resp = client.get(f"/api/predictions/{patient_id}", headers=clinician_headers)
        assert preds_resp.status_code == 200
        predictions = preds_resp.json()
        assert len(predictions) >= 3
        assert all("confidence_score" in item for item in predictions)

        expl_resp = client.get(f"/api/explanations/{patient_id}", headers=clinician_headers)
        assert expl_resp.status_code == 200
        explanations = expl_resp.json()
        assert len(explanations) >= 3
        assert all(item["plain_summary"] for item in explanations)
        assert all(item["provenance"] == "tiered-risk-engine-v1" for item in explanations)

        observation_resp = client.post(
            f"/api/patients/{patient_id}/observations",
            headers=clinician_headers,
            json={"heart_rate": 102, "systolic_bp": 148, "oxygen_saturation": 94, "glucose": 136},
        )
        assert observation_resp.status_code == 201
        assert observation_resp.json()["missingness_flags"]

        observation_list_resp = client.get(f"/api/patients/{patient_id}/observations", headers=clinician_headers)
        assert observation_list_resp.status_code == 200
        assert len(observation_list_resp.json()) >= 1

        review_resp = client.patch(
            f"/api/patients/{patient_id}/review-status",
            headers=clinician_headers,
            json={"review_status": "monitored", "assigned_reviewer": "clinician"},
        )
        assert review_resp.status_code == 200
        assert review_resp.json()["review_status"] == "monitored"

        triage_resp = client.get("/api/triage/queue", headers=clinician_headers)
        assert triage_resp.status_code == 200

        metrics_resp = client.get("/api/metrics/summary", headers=clinician_headers)
        assert metrics_resp.status_code == 200
        metrics = metrics_resp.json()
        assert metrics["total_patients"] >= 1
        assert "high_risk_patients" in metrics
        assert "recall_at_threshold" in metrics

        cohort_resp = client.get("/api/metrics/cohorts", headers=clinician_headers)
        assert cohort_resp.status_code == 200
        cohort = cohort_resp.json()
        assert "average_risk_by_target" in cohort

        model_cards_resp = client.get("/api/model-cards", headers=clinician_headers)
        assert model_cards_resp.status_code == 200
        assert len(model_cards_resp.json()) >= 3

        audit_resp = client.get("/api/audit/logs?limit=20", headers=analyst_headers)
        assert audit_resp.status_code == 200
        assert len(audit_resp.json()) >= 1
