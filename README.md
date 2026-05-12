# Cerberus — Healthcare Risk Prediction and Clinical Intelligence Platform

Portfolio demo for synthetic healthcare risk scoring, interpretability, and clinical-style workflow design.

⚠️ **Not for clinical use.** All data used in this project is fully synthetic and contains no real patient health information (PHI). This is a portfolio demo and has not been clinically validated.

Cerberus is a recruiter-facing project that demonstrates how I design and ship a full-stack ML application with practical safeguards and transparent limitations. The focus is on clear risk workflows, explainable outputs, and honest documentation rather than clinical claims.

I am a **University of Maryland student studying Information Science and Electrical Engineering with a Business minor.**

## What this project demonstrates

- Builds a full-stack ML app with FastAPI, React, and PostgreSQL.
- Implements tiered risk scoring: heuristic first, then model escalation for uncertain cases.
- Returns SHAP-style feature attribution and plain-language reason codes for each prediction.
- Tracks model versions and training runs for traceability.
- Adds role-based access control (RBAC) and audit logging patterns.
- Includes fairness-slice and drift-monitoring demos on synthetic data.

## Tech stack

- **Backend:** Python, FastAPI, SQLAlchemy, JWT auth
- **ML:** scikit-learn (LogisticRegression, RandomForestClassifier), SHAP
- **Frontend:** React, Vite, Tailwind CSS, Recharts
- **Data:** PostgreSQL or SQLite (local)
- **Tooling:** Docker Compose, Makefile, pytest, ruff, mypy, GitHub Actions

## Architecture overview

High-level architecture and flow diagrams are documented in [`docs/architecture.md`](docs/architecture.md).

Risk pipeline: **Data → Feature Engineering → Model → Risk Score Output**

## How to run locally

```bash
git clone https://github.com/RyanJBush/Healthcare-risk-prediction-and-clinical-intelligence-platform.git
cd Healthcare-risk-prediction-and-clinical-intelligence-platform
make setup
make dev
```

Then open:
- Frontend: `http://localhost:5173`
- API docs: `http://localhost:8000/docs`

Optional demo bootstrap:

```bash
make demo-bootstrap
```

## Demo workflow

1. Start the stack with `make dev`.
2. Seed synthetic records with `make demo-bootstrap`.
3. Log in as `clinician / clinician123` and review dashboard + patient detail.
4. Open risk analysis and triage pages to inspect score behavior.
5. Run `python scripts/fairness_eval.py --n 500 --seed 42` for fairness slices.

## Screenshots / demo

These artifacts are **Portfolio Preview / UI Preview** materials from a local environment and synthetic data only. They are **not for clinical use** and are not evidence of diagnosis capability, treatment recommendations, HIPAA compliance, or medical-device readiness.

- Screenshot inventory and capture status: [`docs/screenshots/README.md`](docs/screenshots/README.md)
- Standalone portfolio preview page: [`docs/preview/index.html`](docs/preview/index.html)

## Limitations and future work

- Data is fully synthetic and does not represent real clinical populations.
- Model outputs are illustrative demo-scale results and not clinically validated.
- Local demo environment only; no public deployment is claimed.
- Future work: stronger calibration workflows, richer synthetic cohort generation, and deeper monitoring visualizations.

## Resume bullets

Project-specific resume bullets: [`docs/resume-bullets.md`](docs/resume-bullets.md)

## License

This project is licensed under the [MIT License](LICENSE).
