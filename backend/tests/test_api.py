from fastapi.testclient import TestClient

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


def test_patient_prediction_flow() -> None:
    headers = auth_headers()
    with TestClient(app) as client:
        create_resp = client.post(
            "/api/patients",
            headers=headers,
            json={
                "full_name": "Jane Doe",
                "age": 59,
                "bmi": 31.2,
                "blood_pressure": 142,
                "cholesterol": 220,
                "glucose": 128,
                "smoker": True,
            },
        )
        assert create_resp.status_code == 201
        patient_id = create_resp.json()["id"]

        predict_resp = client.post("/api/predict", headers=headers, json={"patient_id": patient_id})
        assert predict_resp.status_code == 200
        assert predict_resp.json()["risk_category"] in {"low", "medium", "high"}

        preds_resp = client.get(f"/api/predictions/{patient_id}", headers=headers)
        assert preds_resp.status_code == 200
        assert len(preds_resp.json()) >= 1

        expl_resp = client.get(f"/api/explanations/{patient_id}", headers=headers)
        assert expl_resp.status_code == 200
        assert len(expl_resp.json()) >= 1

        metrics_resp = client.get("/api/metrics/summary", headers=headers)
        assert metrics_resp.status_code == 200
        body = metrics_resp.json()
        assert body["total_patients"] >= 1
        assert body["total_predictions"] >= 1
