# Resume Bullets — Cerberus

ATS-friendly, one-line bullets. Pick 3–5 per role. **Every claim maps to code in this repo.** Use the [Honest framing notes](#honest-framing-notes) at the bottom before you paste anything onto a resume.

## ATS-friendly headline bullets (pick 5–8)

1. Built a healthcare risk-prediction portfolio platform in **Python (FastAPI)** and **React** that scores **synthetic** patient records across **three clinical risk targets** (readmission, deterioration, adverse event) with explainable, per-feature outputs.
2. Implemented a **tiered ML scoring pipeline** combining a fast weighted heuristic with **scikit-learn LogisticRegression and RandomForestClassifier** models, escalating to the full model only on low-confidence cases.
3. Integrated **SHAP-style feature attribution** so every risk score returns top contributing factors, reason codes, and a plain-language rationale for human-in-the-loop review.
4. Designed a **model registry with versioned training runs** (`/api/model-registry`, `/api/training/runs`) so every score is traceable to a specific model version, with persisted training and evaluation history.
5. Built a **drift-monitoring endpoint** (`/api/monitoring/drift`) comparing request-time prediction distributions against the training baseline as a foundation for production model observability.
6. Authored an **offline fairness slice evaluator** (`scripts/fairness_eval.py`) that reports positive-prediction-rate disparities across synthetic demographic groups, supported by a documented model card.
7. Designed a **FastAPI backend with JWT auth, four RBAC roles (Clinician / Admin / Analyst / Viewer), and request-level audit logging** across roughly **49 REST endpoints**, documented via OpenAPI/Swagger.
8. Set up **GitHub Actions CI** running ruff, mypy, pytest, and a frontend Vite production build on every push; one-command local stack via **Docker Compose** and a **Makefile**.

## Healthcare Analytics / Predictive Modeling

- Built a healthcare risk-prediction platform (FastAPI + scikit-learn) that scores **synthetic** patient records across three risk targets (readmission, deterioration, adverse event).
- Engineered a 6-feature input layer (age, BMI, systolic BP, cholesterol, glucose, smoker) plus derived composite signals and protective-factor cutoffs for tiered risk scoring on a synthetic cohort.
- Implemented a **tiered scoring pipeline** that runs a fast weighted heuristic first and escalates to the full ML model only when confidence is low.
- Trained **LogisticRegression** and **RandomForestClassifier** pipelines on a synthetic dataset and evaluated with ROC-AUC, PR-AUC, Brier score, F1, precision, and recall.
- Designed a **model registry** with versioned artifacts and persisted training-run history so every scored prediction is traceable to a model version.

## Explainable AI / Interpretability

- Integrated **SHAP** (`shap==0.46.0`) feature-attribution to return per-patient top-factor breakdowns alongside each risk score for clinician review.
- Generated **reason codes and plain-language rationale summaries** for every prediction to support human-in-the-loop review.
- Built **explanation-history endpoints** (`/api/explanations/{patient_id}/history`) so each scoring decision can be audited against the features that drove it.

## Fairness, Drift & Model Monitoring

- Implemented a **drift-detection endpoint** that compares request-time prediction distributions against a training baseline.
- Wrote a **fairness-evaluation CLI** (`scripts/fairness_eval.py`) that slices model output (positive-prediction rate, mean risk score, risk-category distribution, disparity ratio) by synthetic demographic group.
- Documented model limitations, intended use, and known biases in a **MODEL_CARD** modeled after Mitchell et al. (2019).

## Backend & API Engineering

- Designed a **FastAPI** backend with **JWT** auth, four **RBAC** roles (Clinician, Admin, Analyst, Viewer), and request-level **audit logging** persisted to PostgreSQL.
- Built ~49 REST endpoints for patients, observations, scoring (single + batch + tiered + compare), explanations, triage, model registry, training, evaluation, monitoring, audit, summaries, and reports, documented via OpenAPI/Swagger.
- Wrote a **pytest** suite spanning 11 test modules covering API routes, ML behavior, training, evaluation, security, seeding, model registry, summaries, risk models, and the CLI scripts.

## Frontend Engineering

- Built a clinical-style dashboard in **React 19 + Vite + Tailwind CSS + Recharts** (JavaScript) with Dashboard, Patients, Patient Detail, Triage, and Risk Analysis pages.
- Implemented JWT-aware API client (`frontend/src/api.js`) and role-aware navigation against the FastAPI backend.

## DevOps / Tooling

- Containerized the backend, frontend, and Postgres with **Docker Compose** for one-command local startup.
- Set up **GitHub Actions CI** running ruff lint, mypy type-checks, pytest, and a frontend Vite production build on every push and pull request.
- Authored a **Makefile** (`make setup`, `make dev`, `make test`, `make lint`, `make demo-bootstrap`) and a `bootstrap_demo.sh` script that logs in, loads the synthetic cohort, runs batch scoring, and prints summary metrics.

## One-line variants (mix and match)

- Healthcare risk-prediction portfolio platform: FastAPI + scikit-learn + SHAP, tiered scoring across 3 clinical targets on **synthetic** data.
- Built explainable patient-risk scoring with **SHAP top-factor attribution** and plain-language rationale for human-in-the-loop review.
- Implemented **fairness slice evaluation** and **drift monitoring** on a synthetic clinical cohort to demonstrate responsible-ML practices.
- Designed **RBAC + audit-logged FastAPI service** with a model registry and versioned training runs for traceable predictions.
- Authored **MODEL_CARD**, **SECURITY** policy, and explicit synthetic-data / non-clinical-use disclaimers to model responsible-AI documentation.

## Honest framing notes

- Always say **"synthetic data"** or **"synthetic patient records,"** never "patient data."
- Say **"portfolio project,"** **"demo,"** or **"exploration of,"** not **"production"** or **"deployed."**
- Say **"explored fairness slicing"** or **"implemented drift detection"**, not **"monitors a production model."**
- Never claim **clinical validation**, **regulatory approval**, **HIPAA readiness**, **medical-device status**, or **real-world use**.
- If asked about scale: this is a single-developer portfolio project with synthetic data and a local-only stack — be honest about it. The *patterns* are real; the metrics and the cohort are not.
