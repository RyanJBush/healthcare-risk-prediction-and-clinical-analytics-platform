# Nova AI

Production-style monorepo for a healthcare risk prediction platform with explainable ML.

## Monorepo structure

- `backend/` FastAPI API, ML scoring, SHAP explainability, JWT RBAC
- `frontend/` React + Vite + Tailwind clinical dashboard
- `docs/` architecture notes
- `.github/workflows/ci.yml` CI for lint/test/build

## Quick start

```bash
make setup
make dev
```

Services:

- Backend API: `http://localhost:8000`
- Frontend app: `http://localhost:5173`
- PostgreSQL: `localhost:5432`

## Backend MVP endpoints

- `GET /health`
- `POST /auth/login`
- `POST /api/patients`
- `GET /api/patients`
- `GET /api/patients/{id}`
- `POST /api/predict`
- `GET /api/predictions/{patient_id}`
- `GET /api/explanations/{patient_id}`
- `GET /api/metrics/summary`

## Demo credentials

- `clinician` / `clinician123`
- `admin` / `admin123`

## Quality

```bash
make lint
make test
```
