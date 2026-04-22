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


def test_readiness() -> None:
    with TestClient(app) as client:
        response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_phase1_tiered_prediction_and_workflow_flow() -> None:
    clinician_headers = auth_headers()
    analyst_headers = auth_headers("analyst", "analyst123")
    viewer_headers = auth_headers("viewer", "viewer123")

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

        forbidden_patient_view = client.get(f"/api/patients/{patient_id}", headers=viewer_headers)
        assert forbidden_patient_view.status_code == 403

        grant_resp = client.post(
            "/api/access/grants",
            headers=auth_headers("admin", "admin123"),
            json={"user_id": 4, "patient_id": patient_id, "can_view": True},
        )
        assert grant_resp.status_code == 201

        allowed_patient_view = client.get(f"/api/patients/{patient_id}", headers=viewer_headers)
        assert allowed_patient_view.status_code == 200

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

        history_resp = client.get(f"/api/explanations/{patient_id}/history?target_type=readmission", headers=clinician_headers)
        assert history_resp.status_code == 200
        history = history_resp.json()
        assert isinstance(history, list)

        review_resp = client.patch(
            f"/api/patients/{patient_id}/review-status",
            headers=clinician_headers,
            json={"review_status": "monitored", "assigned_reviewer": "clinician"},
        )
        assert review_resp.status_code == 200
        assert review_resp.json()["review_status"] == "monitored"

        triage_resp = client.get("/api/triage/queue", headers=clinician_headers)
        assert triage_resp.status_code == 200

        watchlist_resp = client.get("/api/triage/watchlist", headers=clinician_headers)
        assert watchlist_resp.status_code == 200
        assert all(item["risk_category"] == "high" for item in watchlist_resp.json())

        batch_job_resp = client.post(
            "/api/jobs/batch-score",
            headers=clinician_headers,
            json={"target_type": "readmission", "limit": 10},
        )
        assert batch_job_resp.status_code == 201
        batch_job = batch_job_resp.json()
        assert batch_job["status"] == "completed"

        batch_job_detail = client.get(f"/api/jobs/batch-score/{batch_job['id']}", headers=analyst_headers)
        assert batch_job_detail.status_code == 200

        note_create = client.post(
            f"/api/patients/{patient_id}/notes",
            headers=clinician_headers,
            json={
                "note_text": "Patient reviewed by care team; escalate if glucose remains elevated.",
                "recommendation": "Repeat glucose in 4 hours and monitor BP.",
                "state_from": "new",
                "state_to": "monitored",
            },
        )
        assert note_create.status_code == 201

        notes_list = client.get(f"/api/patients/{patient_id}/notes", headers=clinician_headers)
        assert notes_list.status_code == 200
        assert len(notes_list.json()) >= 1

        ai_summary = client.get(f"/api/patients/{patient_id}/ai-summary", headers=clinician_headers)
        assert ai_summary.status_code == 200
        assert "summary" in ai_summary.json()

        recommendations = client.get(f"/api/patients/{patient_id}/recommendations", headers=clinician_headers)
        assert recommendations.status_code == 200
        assert len(recommendations.json()["recommendations"]) >= 1

        followup_questions = client.get(f"/api/patients/{patient_id}/follow-up-questions", headers=clinician_headers)
        assert followup_questions.status_code == 200
        assert len(followup_questions.json()["questions"]) >= 1

        note_summary = client.get(f"/api/patients/{patient_id}/note-summary", headers=clinician_headers)
        assert note_summary.status_code == 200
        assert "summary" in note_summary.json()

        timeline = client.get(f"/api/patients/{patient_id}/timeline", headers=clinician_headers)
        assert timeline.status_code == 200
        assert isinstance(timeline.json(), list)

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

        cohort_filter = client.get("/api/cohorts/filter?target_type=readmission", headers=clinician_headers)
        assert cohort_filter.status_code == 200

        model_cards_resp = client.get("/api/model-cards", headers=clinician_headers)
        assert model_cards_resp.status_code == 200
        assert len(model_cards_resp.json()) >= 3

        model_eval = client.get("/api/evaluation/model-comparison", headers=analyst_headers)
        assert model_eval.status_code == 200
        assert "models" in model_eval.json()
        assert "subgroup_outcomes" in model_eval.json()

        model_registry = client.get("/api/model-registry", headers=clinician_headers)
        assert model_registry.status_code == 200
        assert len(model_registry.json()) >= 3

        threshold_update = client.post(
            "/api/model-config/thresholds",
            headers=auth_headers("admin", "admin123"),
            json={
                "target_type": "readmission",
                "medium_threshold": 0.5,
                "high_threshold": 0.76,
                "rationale": "Phase 3 calibration update for operational precision.",
            },
        )
        assert threshold_update.status_code == 201

        config_changes = client.get("/api/model-config/changes?target_type=readmission", headers=analyst_headers)
        assert config_changes.status_code == 200
        assert len(config_changes.json()) >= 1

        handoff = client.get("/api/cohorts/handoff-summary", headers=clinician_headers)
        assert handoff.status_code == 200
        assert "summary" in handoff.json()

        evaluation_run = client.post("/api/evaluation/runs?target_type=readmission&threshold=0.6", headers=analyst_headers)
        assert evaluation_run.status_code == 201
        run_id = evaluation_run.json()["id"]

        evaluation_run_detail = client.get(f"/api/evaluation/runs/{run_id}", headers=analyst_headers)
        assert evaluation_run_detail.status_code == 200

        evaluation_run_list = client.get("/api/evaluation/runs?limit=10", headers=analyst_headers)
        assert evaluation_run_list.status_code == 200
        assert len(evaluation_run_list.json()) >= 1

        training_run = client.post("/api/training/runs", headers=analyst_headers, json={"target_type": "readmission"})
        assert training_run.status_code == 201
        training_id = training_run.json()["id"]

        training_run_detail = client.get(f"/api/training/runs/{training_id}", headers=analyst_headers)
        assert training_run_detail.status_code == 200

        training_run_list = client.get("/api/training/runs?limit=10", headers=analyst_headers)
        assert training_run_list.status_code == 200
        assert len(training_run_list.json()) >= 1

        csv_report = client.get("/api/reports/cohort.csv", headers=clinician_headers)
        assert csv_report.status_code == 200
        assert "masked_identifier" in csv_report.text

        disclaimer = client.get("/api/disclaimer", headers=viewer_headers)
        assert disclaimer.status_code == 200
        assert "clinical decision support" in disclaimer.json()["message"].lower()

        seed_load = client.post("/api/demo/load-seed", headers=auth_headers("admin", "admin123"), json={"count": 3, "seed": 7})
        assert seed_load.status_code == 201
        assert seed_load.json()["created_count"] == 3

        audit_resp = client.get("/api/audit/logs?limit=20", headers=analyst_headers)
        assert audit_resp.status_code == 200
        assert len(audit_resp.json()) >= 1
