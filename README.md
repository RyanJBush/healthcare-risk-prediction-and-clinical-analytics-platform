# Healthcare Risk Prediction & Clinical Analytics Platform

> ⚠️ **Disclaimer:** This project uses synthetic data for educational and portfolio purposes only. It is **not** intended for clinical decision-making, diagnosis, or treatment.

## Executive Summary
This repository is a recruiter-ready, end-to-end healthcare analytics portfolio project that combines machine learning, backend APIs, and a frontend application for risk scoring workflows. It demonstrates how to build a clinical-analytics-style platform with synthetic patient records, model evaluation tooling, explainability outputs, and role-based application flows. The implementation emphasizes transparent limitations, reproducible local development, and practical data science + software engineering integration.

## Healthcare Analytics Problem This Project Solves
Healthcare teams often need a structured way to identify higher-risk patient profiles and prioritize review queues, while also understanding why a model generated a score. This project demonstrates a synthetic risk prediction workflow that supports:
- Multi-target risk scoring (readmission, deterioration, adverse event)
- Triage-oriented categorization (low/medium/high)
- Model comparison and threshold exploration for analytics review
- Explainability-oriented outputs to make model behavior easier to inspect

## Key Features
- FastAPI backend with authenticated API workflows and role-aware access patterns
- Synthetic patient and observation data generation for reproducible demos
- Tiered risk scoring pipeline with baseline logic and model-driven scoring paths
- ML model training endpoints and persisted training run metadata
- Evaluation endpoints for ROC-AUC, PR-AUC, precision/recall/F1, confusion matrix, and calibration outputs
- Drift-monitoring-style and fairness-slice analysis utilities (demo/educational use)
- React frontend pages for dashboard, triage, patient detail, and risk analysis
- Audit logging and model registry/model card concepts

## Tech Stack
- **Programming & ML:** Python, NumPy, scikit-learn, SHAP
- **Backend:** FastAPI, SQLAlchemy, JWT-based auth
- **Frontend:** React (Vite), Tailwind CSS, Recharts
- **Data Layer:** PostgreSQL (Docker Compose) and SQLite (local/test scenarios)
- **Tooling:** pytest, ruff, mypy, Makefile, Docker Compose

## Risk Prediction / Analytics Workflow
1. Seed synthetic patients via demo tooling/API.
2. Create or ingest patient observations in the backend.
3. Run tiered risk scoring for configured target types.
4. Persist prediction outputs, risk categories, and explanation artifacts.
5. Review triage views and patient-level detail in the frontend.
6. Run evaluation/model comparison workflows with configurable thresholds.
7. Inspect calibration, monitoring, and summary analytics endpoints.

## Data Processing and Model Overview
- The project builds tabular feature vectors from synthetic patient attributes (e.g., age, BMI, blood pressure, cholesterol, glucose, smoker flag) plus derived risk-oriented features.
- Implemented model paths include logistic regression and random forest (with optional XGBoost when available) for comparative evaluation workflows.
- The training/evaluation code includes time-aware splitting, threshold sweeps, cost-style scoring, and common classification metrics.
- Explainability support includes feature importance snapshots and SHAP-integrated interpretation flows.
- All data in this repository is synthetic and intended for experimentation, not clinical validation.

## Architecture Overview
- **Frontend:** React app with pages for login, dashboard, patients, patient detail, triage, and risk analysis.
- **Backend API:** FastAPI application exposing endpoints for auth, patients, predictions, explanations, training, evaluation, monitoring, and summaries.
- **ML Services:** Feature engineering, offline training, model evaluation, risk model comparison, and calibration utilities.
- **Persistence:** SQLAlchemy models for users, patients, predictions, explanations, training/evaluation runs, audit logs, and related workflow entities.

For a deeper architecture walkthrough, see [`docs/architecture.md`](docs/architecture.md).

## Setup and Installation
```bash
git clone https://github.com/RyanJBush/Healthcare-risk-prediction-and-clinical-intelligence-platform.git
cd Healthcare-risk-prediction-and-clinical-intelligence-platform
make setup
make dev
```

Then access:
- Frontend: `http://localhost:5173`
- API docs: `http://localhost:8000/docs`

Useful demo commands:
```bash
make demo-bootstrap
make demo-train-small
make demo-fairness
make demo-predict
```

## Example Use Cases
- Demonstrating a healthcare-oriented ML project in data science or analytics interviews
- Showcasing model evaluation literacy (discrimination, calibration, thresholding)
- Presenting a full-stack ML product workflow (API + UI + persistence)
- Discussing responsible synthetic-data prototyping and model limitations
- Highlighting collaboration-ready engineering practices (testing, linting, reproducible scripts)

## Skills Demonstrated
- Healthcare analytics framing with risk-stratification-style workflows
- End-to-end machine learning pipeline development for tabular data
- Feature engineering and model interpretability patterns
- Model evaluation and monitoring-oriented analysis
- API design and backend service architecture with Python/FastAPI
- Frontend data visualization and analyst-friendly UI patterns
- Secure application basics (token auth, role-based access patterns)
- Software engineering quality practices (tests, linting, modular services)

## Resume-Ready Project Description
Built a **Healthcare Risk Prediction & Clinical Analytics Platform** using **Python, FastAPI, scikit-learn, SQLAlchemy, React, and PostgreSQL** to simulate risk-stratification workflows on synthetic patient data. Implemented feature engineering, tiered prediction logic, model training/evaluation services, explainability outputs, drift/fairness analysis utilities, and role-aware API/frontend experiences to demonstrate production-style machine learning and software engineering capabilities.

## Future Improvements
- Expand synthetic cohort generation realism and scenario diversity
- Add stronger experiment tracking and artifact/version governance
- Deepen model monitoring with richer longitudinal drift diagnostics
- Improve interpretability UX and clinician-facing explanation layouts
- Add CI quality gates for additional statistical and data validation checks
- Harden packaging/deployment ergonomics for easier local onboarding

## License
MIT License: [`LICENSE`](LICENSE)
