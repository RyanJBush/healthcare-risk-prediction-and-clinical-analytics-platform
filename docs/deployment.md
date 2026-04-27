# Nova AI Deployment & Demo Operations Guide

## Scope
This guide covers practical deployment and demo operations for the portfolio environment (synthetic data only).

## Runtime requirements
- Python 3.11+
- Node 20+
- Docker + Docker Compose (recommended)

Validate locally:

```bash
make doctor
```

## Local deployment options

### Option A: Docker Compose (recommended)

```bash
make dev
```

Services:
- API: `http://localhost:8000`
- Frontend: `http://localhost:5173`
- Postgres: `localhost:5432`

### Option B: Native local processes
Use `README.md` non-Docker instructions and env templates:
- `backend/.env.example`
- `frontend/.env.example`

## CI behavior
GitHub Actions runs:
- backend lint (`ruff`) and tests (`pytest`)
- frontend lint + production build
- frontend `dist/` upload as CI artifact (`frontend-dist`)

## Demo runbook
1. Start stack.
2. Seed + score synthetic cohort:
   ```bash
   make demo-bootstrap
   ```
3. Use walkthrough in `docs/demo-script.md`.

## Troubleshooting

### Backend tests fail with `httpx` missing
Install backend dev extras in Python 3.11 env:

```bash
cd backend
pip install -e ".[dev]"
```

### Backend import errors (`ModuleNotFoundError: app`)
Run tests from `backend/` directory and ensure editable install:

```bash
cd backend
pip install -e ".[dev]"
pytest -q
```

### Frontend build large chunk warning
Current Vite output may exceed 500KB chunk warning in CI. This is non-blocking for demo use; add route-level code-splitting in future hardening.

## Safety statement
Nova AI is a synthetic-data clinical decision support demonstration. Outputs are not diagnostic recommendations.
