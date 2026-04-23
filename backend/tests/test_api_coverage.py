# ruff: noqa: E402
import os
from pathlib import Path

from fastapi.testclient import TestClient

db_url = os.getenv("DATABASE_URL", "")
if db_url.startswith("sqlite") and "///" in db_url:
    db_path = db_url.split("///", maxsplit=1)[1]
    if db_path.startswith("./"):
        db_file = Path(__file__).resolve().parents[1] / db_path[2:]
    else:
        db_file = Path(db_path)
    if db_file.exists():
        db_file.unlink()

from app.main import app
from app.database import SessionLocal
from app.models import Patient, Prediction


def auth_headers(username: str = "clinician", password: str = "clinician123") -> dict[str, str]:
    with TestClient(app) as client:
        response = client.post("/auth/login", json={"username": username, "password": password})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_patient(
    client: TestClient,
    headers: dict[str, str],
    *,
    full_name: str,
    age: int,
    has_historical_outcome: bool = False,
    review_status: str = "new",
) -> int:
    create_resp = client.post(
        "/api/patients",
        headers=headers,
        json={
            "full_name": full_name,
            "age": age,
            "bmi": 29.1,
            "blood_pressure": 130,
            "cholesterol": 210,
            "glucose": 120,
            "smoker": False,
            "has_historical_outcome": has_historical_outcome,
        },
    )
    assert create_resp.status_code == 201
    patient_id = create_resp.json()["id"]

    if review_status != "new":
        review_resp = client.patch(
            f"/api/patients/{patient_id}/review-status",
            headers=headers,
            json={"review_status": review_status, "assigned_reviewer": "clinician"},
        )
        assert review_resp.status_code == 200

    return patient_id


def insert_readmission_prediction(patient_id: int, risk_score: float, risk_category: str) -> None:
    with SessionLocal() as db:
        db.add(
            Prediction(
                patient_id=patient_id,
                target_type="readmission",
                risk_score=risk_score,
                baseline_risk_score=0.35,
                confidence_score=0.88,
                risk_category=risk_category,
                threshold_used=0.55,
                reason_codes="[]",
                model_version="tiered-v1",
            )
        )
        db.commit()


def clear_historical_outcomes() -> None:
    with SessionLocal() as db:
        db.query(Patient).update({Patient.has_historical_outcome: False})
        db.commit()


def clear_non_readmission_predictions() -> None:
    with SessionLocal() as db:
        db.query(Prediction).filter(Prediction.target_type != "readmission").delete()
        db.commit()


def test_missing_branch_paths_for_error_handling_and_filters() -> None:
    admin_headers = auth_headers("admin", "admin123")
    clinician_headers = auth_headers("clinician", "clinician123")
    analyst_headers = auth_headers("analyst", "analyst123")

    with TestClient(app) as client:
        invalid_login = client.post("/auth/login", json={"username": "clinician", "password": "wrong"})
        assert invalid_login.status_code == 401
        assert invalid_login.json()["detail"] == "Invalid credentials"

        middle_age_patient_id = create_patient(client, clinician_headers, full_name="Sort One", age=50)
        oldest_patient_id = create_patient(client, clinician_headers, full_name="Sort Two", age=70)
        youngest_patient_id = create_patient(client, clinician_headers, full_name="Sort Three", age=30)

        created_sort = client.get("/api/patients?sort=created_at_asc", headers=clinician_headers)
        assert created_sort.status_code == 200
        created_ids = [
            item["id"]
            for item in created_sort.json()
            if item["id"] in {middle_age_patient_id, oldest_patient_id, youngest_patient_id}
        ]
        assert created_ids == [middle_age_patient_id, oldest_patient_id, youngest_patient_id]

        age_desc = client.get("/api/patients?sort=age_desc", headers=clinician_headers)
        age_desc_ids = [
            item["id"]
            for item in age_desc.json()
            if item["id"] in {middle_age_patient_id, oldest_patient_id, youngest_patient_id}
        ]
        assert age_desc_ids == [oldest_patient_id, middle_age_patient_id, youngest_patient_id]

        age_asc = client.get("/api/patients?sort=age_asc", headers=clinician_headers)
        age_asc_ids = [
            item["id"]
            for item in age_asc.json()
            if item["id"] in {middle_age_patient_id, oldest_patient_id, youngest_patient_id}
        ]
        assert age_asc_ids == [youngest_patient_id, middle_age_patient_id, oldest_patient_id]

        fallback_sort = client.get("/api/patients?sort=unsupported", headers=clinician_headers)
        assert fallback_sort.status_code == 200

        assert client.get("/api/patients/999999", headers=admin_headers).status_code == 404
        assert (
            client.patch(
                "/api/patients/999999/review-status",
                headers=clinician_headers,
                json={"review_status": "monitored", "assigned_reviewer": "clinician"},
            ).status_code
            == 404
        )
        assert (
            client.post(
                "/api/patients/999999/observations",
                headers=clinician_headers,
                json={"heart_rate": 88, "systolic_bp": 120, "oxygen_saturation": 98, "glucose": 100},
            ).status_code
            == 404
        )
        assert client.post("/api/predict", headers=clinician_headers, json={"patient_id": 999999}).status_code == 404

        prediction_resp = client.post("/api/predict", headers=clinician_headers, json={"patient_id": middle_age_patient_id})
        assert prediction_resp.status_code == 200
        assert prediction_resp.json()["target_type"] == "readmission"

        assert client.post("/api/predict/tiered", headers=clinician_headers, json={"patient_id": 999999}).status_code == 404
        assert client.get("/api/jobs/batch-score/999999", headers=analyst_headers).status_code == 404

        assert (
            client.post(
                "/api/patients/999999/notes",
                headers=clinician_headers,
                json={
                    "note_text": "Missing patient note",
                    "recommendation": "N/A",
                    "state_from": "new",
                    "state_to": "monitored",
                },
            ).status_code
            == 404
        )

        assert client.get("/api/evaluation/runs/999999", headers=analyst_headers).status_code == 404
        assert client.get("/api/training/runs/999999", headers=analyst_headers).status_code == 404

        invalid_thresholds = client.post(
            "/api/model-config/thresholds",
            headers=admin_headers,
            json={
                "target_type": "readmission",
                "medium_threshold": 0.7,
                "high_threshold": 0.6,
                "rationale": "invalid for branch coverage",
            },
        )
        assert invalid_thresholds.status_code == 422
        assert invalid_thresholds.json()["detail"] == "high_threshold must be greater than medium_threshold"

        missing_grant_target = client.post(
            "/api/access/grants",
            headers=admin_headers,
            json={"user_id": 4, "patient_id": 999999, "can_view": True},
        )
        assert missing_grant_target.status_code == 404

        first_grant = client.post(
            "/api/access/grants",
            headers=admin_headers,
            json={"user_id": 4, "patient_id": middle_age_patient_id, "can_view": True},
        )
        assert first_grant.status_code == 201

        updated_grant = client.post(
            "/api/access/grants",
            headers=admin_headers,
            json={"user_id": 4, "patient_id": middle_age_patient_id, "can_view": False},
        )
        assert updated_grant.status_code == 201
        assert updated_grant.json()["id"] == first_grant.json()["id"]
        assert updated_grant.json()["can_view"] is False

        filtered_grants = client.get("/api/access/grants?user_id=4", headers=analyst_headers)
        assert filtered_grants.status_code == 200
        assert all(item["user_id"] == 4 for item in filtered_grants.json())

        assert client.get("/api/patients/999999/ai-summary", headers=admin_headers).status_code == 404


def test_triage_cohort_and_metrics_branch_paths() -> None:
    clinician_headers = auth_headers("clinician", "clinician123")

    with TestClient(app) as client:
        clear_historical_outcomes()
        metrics = client.get("/api/metrics/summary", headers=clinician_headers)
        assert metrics.status_code == 200
        assert metrics.json()["recall_at_threshold"] == 0.0

        no_prediction_patient_id = create_patient(
            client, clinician_headers, full_name="No Prediction", age=44, has_historical_outcome=False
        )
        medium_risk_patient_id = create_patient(
            client,
            clinician_headers,
            full_name="Medium Risk",
            age=45,
            has_historical_outcome=False,
            review_status="monitored",
        )
        low_risk_patient_id = create_patient(
            client, clinician_headers, full_name="Low Risk", age=46, has_historical_outcome=False
        )
        high_risk_patient_id = create_patient(
            client, clinician_headers, full_name="High Risk", age=47, has_historical_outcome=False
        )

        insert_readmission_prediction(medium_risk_patient_id, risk_score=0.6, risk_category="medium")
        insert_readmission_prediction(low_risk_patient_id, risk_score=0.2, risk_category="low")
        insert_readmission_prediction(high_risk_patient_id, risk_score=0.9, risk_category="high")

        queue = client.get("/api/triage/queue", headers=clinician_headers)
        queue_ids = [item["patient_id"] for item in queue.json()]
        assert high_risk_patient_id in queue_ids
        assert medium_risk_patient_id in queue_ids
        assert low_risk_patient_id not in queue_ids
        assert no_prediction_patient_id not in queue_ids

        monitored_queue = client.get("/api/triage/queue?status=monitored", headers=clinician_headers)
        assert monitored_queue.status_code == 200
        monitored_queue_ids = [item["patient_id"] for item in monitored_queue.json()]
        assert medium_risk_patient_id in monitored_queue_ids
        assert high_risk_patient_id not in monitored_queue_ids
        assert low_risk_patient_id not in monitored_queue_ids
        assert no_prediction_patient_id not in monitored_queue_ids

        watchlist = client.get("/api/triage/watchlist", headers=clinician_headers)
        watchlist_ids = [item["patient_id"] for item in watchlist.json()]
        assert high_risk_patient_id in watchlist_ids
        assert medium_risk_patient_id not in watchlist_ids
        assert low_risk_patient_id not in watchlist_ids
        assert no_prediction_patient_id not in watchlist_ids

        filtered = client.get(
            "/api/cohorts/filter?review_status=monitored&risk_category=high&target_type=readmission",
            headers=clinician_headers,
        )
        assert filtered.status_code == 200
        filtered_ids = {item["patient_id"] for item in filtered.json()}
        assert all(
            patient_id not in filtered_ids
            for patient_id in (
                no_prediction_patient_id,
                medium_risk_patient_id,
                low_risk_patient_id,
                high_risk_patient_id,
            )
        )

        clear_non_readmission_predictions()
        cohort_metrics = client.get("/api/metrics/cohorts", headers=clinician_headers)
        assert cohort_metrics.status_code == 200
        assert cohort_metrics.json()["average_risk_by_target"]["deterioration"] == 0.0
        assert cohort_metrics.json()["average_risk_by_target"]["adverse_event"] == 0.0
