# Nova AI

Production-style monorepo for a healthcare risk prediction platform with explainable ML.

## Monorepo structure

- `backend/` FastAPI API, tiered ML scoring, clinician explanations, JWT RBAC
- `frontend/` React + Vite + Tailwind clinical dashboard
- `docs/` architecture notes
- `.github/workflows/ci.yml` CI for lint/test/build

## Quick start

```bash
make doctor
make setup
make dev
```

Services:

- Backend API: `http://localhost:8000`
- Frontend app: `http://localhost:5173`
- PostgreSQL: `localhost:5432`

## Local non-Docker development

Backend:

```bash
cp backend/.env.example backend/.env
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -e ".[dev]"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Frontend:

```bash
cp frontend/.env.example frontend/.env
cd frontend
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

## Seed demo data + baseline scoring

With backend running, you can load synthetic patients and score the cohort in one step:

```bash
make demo-bootstrap
```

Optional overrides:

```bash
API_BASE=http://localhost:8000 SEED_COUNT=75 SEED_VALUE=7 ./scripts/bootstrap_demo.sh
```

## Backend endpoints (Phase 1)

- `GET /health`
- `GET /ready`
- `POST /auth/login`
- `POST /api/patients`
- `GET /api/patients`
- `GET /api/patients/{id}`
- `GET /api/disclaimer`
- `POST /api/access/grants`
- `GET /api/access/grants`
- `GET /api/patients/{id}/ai-summary`
- `GET /api/patients/{id}/recommendations`
- `GET /api/patients/{id}/follow-up-questions`
- `GET /api/patients/{id}/note-summary`
- `GET /api/patients/{id}/timeline`
- `PATCH /api/patients/{id}/review-status`
- `POST /api/patients/{id}/observations`
- `GET /api/patients/{id}/observations`
- `POST /api/predict`
- `POST /api/predict/tiered`
- `POST /api/jobs/batch-score`
- `GET /api/jobs/batch-score/{job_id}`
- `GET /api/predictions/{patient_id}`
- `GET /api/explanations/{patient_id}`
- `GET /api/explanations/{patient_id}/history`
- `GET /api/triage/queue`
- `GET /api/triage/watchlist`
- `POST /api/patients/{id}/notes`
- `GET /api/patients/{id}/notes`
- `GET /api/metrics/summary`
- `GET /api/metrics/cohorts`
- `GET /api/cohorts/filter`
- `GET /api/evaluation/model-comparison`
- `POST /api/evaluation/runs`
- `GET /api/evaluation/runs`
- `GET /api/evaluation/runs/{run_id}`
- `POST /api/training/runs`
- `GET /api/training/runs`
- `GET /api/training/runs/{run_id}`
- `GET /api/model-registry`
- `POST /api/model-config/thresholds`
- `GET /api/model-config/changes`
- `GET /api/cohorts/handoff-summary`
- `GET /api/reports/cohort.csv`
- `POST /api/demo/load-seed`
- `GET /api/model-cards`
- `GET /api/audit/logs`

## Demo credentials

- `clinician` / `clinician123`
- `admin` / `admin123`
- `analyst` / `analyst123`
- `viewer` / `viewer123`

## Quality

```bash
make lint
make test
```

> Note: backend requires Python `3.11+`, and frontend requires Node `20+`.

## Demo prep

- Guided walkthrough: `docs/demo-script.md`
- Deployment/operations guide: `docs/deployment.md`
- One-command cohort bootstrap: `make demo-bootstrap`
