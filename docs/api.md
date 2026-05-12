# API Reference

FastAPI auto-generates interactive docs at `http://localhost:8000/docs` (Swagger UI) and `http://localhost:8000/redoc` once the backend is running. This document is a curated summary of the most relevant endpoints for portfolio review.

> All examples use synthetic data. Nothing in this API is intended for clinical decision-making.

## Authentication

All non-public endpoints require a JWT bearer token. Obtain one with the seeded demo credentials:

```bash
curl -X POST http://localhost:8000/api/auth/login \
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

| Role | Read patients | Score / Explain | Manage models | Admin / audit |
|---|---|---|---|---|
| Viewer | yes | no | no | no |
| Analyst | yes | yes | no | no |
| Clinician | yes | yes | no | no |
| Admin | yes | yes | yes | yes |

## Endpoint groups

### Patients
- `GET /api/patients` — list patients (paginated)
- `GET /api/patients/{id}` — patient detail with most recent risk scores
- `POST /api/patients` — create a synthetic patient record (Analyst/Admin)

### Scoring
- `POST /api/scoring/{patient_id}` — score a single patient across all targets
- `POST /api/scoring/batch` — score a batch of patient IDs
- Returns: `risk_score`, `risk_category` (low/medium/high), `confidence_score`, `top_factors`, `reason_codes`, `plain_summary`

### Explanations
- `GET /api/explanations/{patient_id}` — most recent SHAP-style top-factor breakdown
- `GET /api/explanations/{patient_id}/history` — historical explanations

### Triage
- `GET /api/triage/queue` — prioritized review queue
- `POST /api/triage/{patient_id}/status` — update review status (`new`, `reviewed`, `escalated`, `monitored`)

### Model registry
- `GET /api/models` — list registered model versions
- `GET /api/models/{id}` — model card and training metadata
- `POST /api/models/train` — kick off a training run on the synthetic dataset (Admin)

### Monitoring
- `GET /api/monitoring/drift` — distribution-shift summary vs training baseline
- `GET /api/monitoring/audit` — recent audit-log entries (Admin)

## Sample scoring response

```json
{
  "patient_id": "P-0007",
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
```

## CLI alternative

If you want to score patients without running the API, see `scripts/predict_cli.py`:

```bash
python scripts/predict_cli.py --age 72 --bmi 31 --bp 158 --chol 245 --glucose 180 --smoker 1
```

## Notes & limitations

- All endpoints currently operate on the seeded synthetic cohort.
- Drift detection compares against the training-time baseline; with no real production traffic the drift values are illustrative.
- The fairness-slicing tool (`scripts/fairness_eval.py`) is offline and not exposed as an endpoint.
