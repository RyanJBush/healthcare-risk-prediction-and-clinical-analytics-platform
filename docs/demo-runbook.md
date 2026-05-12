# Cerberus Demo Runbook

> **Not for clinical use.** All data is synthetic. This runbook drives a portfolio walkthrough of the local stack — it is not a clinical deployment procedure.

Use this when recording a demo video, presenting live, or walking a reviewer through the project. A full pass takes about **8–10 minutes**.

## 0. Prerequisites

- Docker + Docker Compose
- Python 3.11+
- Node.js 20+
- `make`, `curl`, `jq` (helpful for the API steps)

```bash
make doctor          # validates Python / Node / Docker versions
```

## 1. Bring the stack up (≈ 2 min)

```bash
make setup           # install backend + frontend deps
make dev             # docker compose up — db + backend + frontend
```

Wait for the backend to log `Uvicorn running on http://0.0.0.0:8000` and the frontend to log `Local: http://localhost:5173`.

Open in browser:
- Frontend dashboard: <http://localhost:5173>
- API Swagger:        <http://localhost:8000/docs>

## 2. Seed the synthetic cohort (≈ 30 s)

In a second terminal:

```bash
make demo-bootstrap
```

This:
1. Logs in as `admin / admin123` against `/auth/login`.
2. Loads 50 synthetic patients (`POST /api/demo/load-seed`).
3. Runs a batch scoring job for the readmission target (`POST /api/jobs/batch-score`).
4. Prints `GET /api/metrics/summary`.

You should see the summary metrics JSON in the terminal.

## 3. Frontend walkthrough (≈ 4 min)

Sign in at <http://localhost:5173> as `clinician / clinician123`.

### Persona A — Triage Clinician
1. **Dashboard** — point out KPI tiles and cohort breakdown.
2. **Triage** — switch between **Alert Queue** and **High-Risk Watchlist**, filter by target and review status.
3. Open a patient from the queue.

### Persona B — Clinical Reviewer
1. **Patient Detail** — show latest predictions and the SHAP-style explanation snapshot (top factors, reason codes, plain-language rationale).
2. Add an observation and trigger recalculation.
3. Update review status (`new` → `reviewed` / `escalated` / `monitored`).
4. Add a review note and show the unified timeline.

### Persona C — Analyst / Governance
1. Log out and sign in as `analyst / analyst123`.
2. **Dashboard** — use cohort drill-down filters.
3. **Risk Analysis**:
   - LogisticRegression vs RandomForest comparison table.
   - Threshold simulation.
   - Trigger an evaluation run.
   - Open model cards and review documented limitations.

> **Suggested screenshots** while doing this pass — see [`docs/screenshots/README.md`](screenshots/README.md) for filenames.

## 4. API walkthrough (≈ 2 min)

```bash
# Log in and capture a JWT
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"clinician","password":"clinician123"}' | jq -r .access_token)

# Score a single patient across all three targets
curl -s -X POST http://localhost:8000/api/predict/tiered \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"patient_id":1}' | jq

# Inspect the most recent SHAP-style explanation
curl -s http://localhost:8000/api/explanations/1 \
  -H "Authorization: Bearer $TOKEN" | jq

# Pull the drift summary
curl -s http://localhost:8000/api/monitoring/drift \
  -H "Authorization: Bearer $TOKEN" | jq

# List registered model versions
curl -s http://localhost:8000/api/model-registry \
  -H "Authorization: Bearer $TOKEN" | jq
```

The full surface is browsable at <http://localhost:8000/docs>.

## 5. CLI & offline scripts (≈ 1 min)

Score a synthetic patient without running the API:

```bash
python scripts/predict_cli.py --age 72 --bmi 31 --bp 158 --chol 245 --glucose 180 --smoker 1
```

Run the offline fairness slice report:

```bash
python scripts/fairness_eval.py --n 500 --seed 42
```

Both are useful talking points for explaining the design: the CLI proves the same scoring function the API uses can be exercised standalone, and the fairness script demonstrates that slice evaluation has been considered up front.

## 6. Talking points / narration

- **Workflow readiness** — queue triage → patient deep dive → review action → timeline traceability.
- **Explainability is first-class** — every score carries a top-factor breakdown and reason codes; reviewers can disagree with the model.
- **Trust controls visible in the UI** — non-clinical-use disclaimer, model cards, threshold and evaluation views.
- **Responsible-ML scaffolding** — drift endpoint, fairness slice script, model registry, audit log, all in this repo.
- **Honest framing** — synthetic-only data, no PHI, no clinical validation, not a medical device.

## 7. Reset

If you want to start clean:

```bash
rm -f backend/nova.db backend/nova_test.db
make dev
```

Or reseed with different values:

```bash
API_BASE=http://localhost:8000 SEED_COUNT=75 SEED_VALUE=7 ./scripts/bootstrap_demo.sh
```

## 8. Safety statement

Cerberus produces signals on **synthetic** patient data only. Outputs are **not** diagnostic recommendations and must not be used to inform real clinical decisions. The project is not a medical device, has not been clinically validated, and is not HIPAA-scoped.
