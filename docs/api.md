# Cerberus API Reference (Portfolio Demo)

FastAPI auto-generates interactive docs at `http://localhost:8000/docs` (Swagger UI) and `http://localhost:8000/redoc` once the backend is running. This document is a curated summary of the most relevant endpoints for portfolio review.

> All examples use **synthetic data**. Nothing in this API is intended for clinical decision-making. Cerberus is not a medical device, has not been clinically validated, and is not HIPAA-scoped.

The backend exposes roughly **49 REST endpoints**. The groups below cover the ones most useful for portfolio review; see live Swagger for the full list.

## Authentication

JWT bearer auth. Obtain a token from the seeded demo credentials:

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"clinician","password":"clinician123"}'
```

Response:
```json
{ "access_token": "eyJhbGciOi...", "token_type": "bearer" }
```

Use the token in subsequent calls:
```bash
curl http://localhost:8000/api/patients \
  -H "Authorization: Bearer $TOKEN"
```

## Roles (RBAC)

Four roles, enforced per-route by `security.require_roles(...)`.

| Role | Read patients | Run scoring / explain | Train / manage models | Admin / audit |
|---|---|---|---|---|
| Viewer | yes | no | no | no |
| Analyst | yes | partial (comparison only) | no | no |
| Clinician | yes | yes | no | no |
| Admin | yes | yes | yes | yes |

## Endpoint groups

### Auth
- `POST /auth/login` — exchange username + password for a JWT.

### Health
- `GET /health` — liveness probe.
- `GET /ready` — readiness probe.

### Patients
- `GET /api/patients` — list patients.
- `GET /api/patients/{id}` — patient detail.
- `POST /api/patients` — create a synthetic patient record.
- `PATCH /api/patients/{id}/review-status` — update review status.
- `POST /api/patients/{id}/observations` — add an observation (triggers rescoring).
- `GET /api/patients/{id}/observations` — observation history.

### Scoring
- `POST /api/predict` — score a single patient (returns the primary `readmission` prediction).
- `POST /api/predict/tiered` — score a patient across all three targets (`readmission`, `deterioration`, `adverse_event`) with tiered inference.
- `GET /api/predict/compare/{patient_id}` — compare LogisticRegression vs RandomForest predictions for a patient.
- `POST /api/jobs/batch-score` — kick off a batch scoring job.
- `GET /api/jobs/batch-score/{job_id}` — batch job status.
- `GET /api/predictions/{patient_id}` — prediction history.

### Explanations
- `GET /api/explanations/{patient_id}` — most recent SHAP-style top-factor breakdown.
- `GET /api/explanations/{patient_id}/history` — historical explanations.

### Triage
- `GET /api/triage/queue` — prioritized review queue.
- `GET /api/triage/watchlist` — high-risk watchlist.

### Model registry, training & evaluation
- `GET /api/model-registry` — list registered model versions.
- `POST /api/training/runs` — train a model on the synthetic dataset (Admin).
- `GET /api/training/runs` — list training runs.
- `GET /api/training/runs/{id}` — training run detail.
- `GET /api/evaluation/model-comparison` — current LogReg vs RandomForest comparison.
- `POST /api/evaluation/runs` — run an evaluation and persist the result.
- `GET /api/evaluation/runs` / `GET /api/evaluation/runs/{id}` — evaluation history.
- `GET /api/model-cards` — registered model cards.
- `POST /api/model-config/thresholds` — update risk thresholds (Admin).
- `GET /api/model-config/changes` — threshold-change history.

### Monitoring
- `GET /api/monitoring/drift` — distribution-shift summary vs the training baseline.
- `GET /api/monitoring/predictions` — recent prediction log entries.

### Audit & access
- `GET /api/audit/logs` — recent audit-log entries (Admin).
- `POST /api/access/grants` — grant patient access (Admin).
- `GET /api/access/grants` — list current grants.

### Cohorts, summaries & reports
- `GET /api/cohorts/filter` — filtered cohort view.
- `GET /api/cohorts/handoff-summary` — shift-handoff summary.
- `GET /api/metrics/summary` — aggregate metrics.
- `GET /api/metrics/cohorts` — cohort-level metrics.
- `GET /api/patients/{id}/ai-summary` — patient narrative summary.
- `GET /api/patients/{id}/recommendations` — follow-up recommendations.
- `GET /api/patients/{id}/follow-up-questions` — follow-up questions.
- `GET /api/patients/{id}/note-summary` — review-note summary.
- `GET /api/patients/{id}/timeline` — unified timeline.
- `GET /api/reports/cohort.csv` — cohort CSV export.
- `POST /api/demo/load-seed` — load the synthetic seed dataset.
- `GET /api/disclaimer` — current safety disclaimer.

### Review notes
- `POST /api/patients/{id}/notes` — add a review note.
- `GET /api/patients/{id}/notes` — note history.

## Sample tiered scoring response

```json
{
  "patient_id": 7,
  "predictions": [
    {
      "target_type": "readmission",
      "risk_score": 0.78,
      "risk_category": "high",
      "confidence_score": 0.84,
      "top_factors": [
        {"feature": "glucose", "impact": 0.41},
        {"feature": "age", "impact": 0.33},
        {"feature": "blood_pressure", "impact": 0.24}
      ],
      "reason_codes": ["GLUCOSE_ELEVATED", "AGE_ELEVATED", "BLOOD_PRESSURE_ELEVATED"],
      "plain_summary": "30-day readmission risk is high (score 0.78, confidence 0.84) with strongest signal from Glucose."
    }
  ]
}
```

## CLI alternative

To score a patient without running the API:

```bash
python scripts/predict_cli.py --age 72 --bmi 31 --bp 158 --chol 245 --glucose 180 --smoker 1
```

## Notes & limitations

- All endpoints operate on the seeded synthetic cohort. There is no real-patient data anywhere in the API.
- Drift detection compares against the training-time baseline; with no real production traffic the drift values are illustrative.
- The fairness-slicing tool (`scripts/fairness_eval.py`) is offline and not exposed as an endpoint.
- Demo passwords and the demo `SECRET_KEY` in `docker-compose.yml` are placeholders for local use only.
