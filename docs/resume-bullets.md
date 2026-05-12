# Resume Bullets — Cerberus

ATS-friendly, one-line bullets. Pick 3–5 per role. All claims map to code in this repo.

## Healthcare Analytics / Predictive Modeling

- Built a healthcare risk-prediction platform (FastAPI + scikit-learn) that scores synthetic patient records across readmission, deterioration, and adverse-event targets.
- Engineered 15 clinical features (vitals, labs, condition flags, composite indices) for tiered risk scoring on a synthetic patient cohort.
- Implemented a tiered scoring pipeline that runs a fast heuristic first and escalates to a full ML model when confidence is low, reducing average latency on low-risk cases.
- Trained logistic regression and random-forest classifiers on synthetic data and evaluated with ROC-AUC, PR-AUC, Brier score, F1, precision, and recall.
- Designed a model registry with versioned artifacts and training-run history to make every scored prediction traceable to a model version.

## Explainable AI / Interpretability

- Integrated SHAP feature-attribution to return per-patient top-factor breakdowns alongside each risk score for clinician review.
- Generated reason codes and plain-language rationale summaries for every prediction to support human-in-the-loop review.
- Built explanation-history endpoints so each scoring decision can be audited against the features that drove it.

## Fairness, Drift, and Model Monitoring

- Implemented a drift-detection endpoint that compares live prediction distributions against a training baseline using summary statistics.
- Wrote a fairness-evaluation script that slices model performance (AUC, accuracy, positive-prediction rate) by demographic group to surface disparities on synthetic data.
- Documented model limitations, intended use, and known biases in a MODEL_CARD following Mitchell et al. (2019) structure.

## Backend & API Engineering

- Designed a FastAPI backend with JWT auth and four RBAC roles (Clinician, Admin, Analyst, Viewer) and request-level audit logging.
- Built REST endpoints for patients, scoring, explanations, triage queues, model registry, and monitoring, documented via OpenAPI/Swagger.
- Wrote a pytest suite covering API routes, scoring services, training, evaluation, security, and seeding for a synthetic patient dataset.

## DevOps / Tooling

- Containerized the backend and frontend with Docker Compose for one-command local setup of a multi-service stack.
- Set up GitHub Actions CI running ruff lint, mypy type-checks, pytest, and a frontend Vite build on every push.
- Authored a Makefile (`make setup`, `make dev`, `make test`, `make lint`, `make demo-bootstrap`) to standardize the developer workflow.

## One-line variants (mix and match)

- Healthcare risk-prediction platform: FastAPI + scikit-learn + SHAP, tiered scoring across 3 clinical targets on synthetic data.
- Built explainable patient-risk scoring with SHAP top-factor attribution and plain-language rationale for clinician review.
- Implemented fairness slice evaluation and drift monitoring on a synthetic clinical cohort to demonstrate responsible-ML practices.
- Designed RBAC + audit-logged FastAPI service with model registry and versioned training runs for traceable predictions.
- Authored MODEL_CARD, SECURITY policy, and explicit synthetic-data / non-clinical-use disclaimers to model responsible-AI documentation.

## Honest framing notes

- Always say "synthetic data" or "synthetic patient records," never "patient data."
- Say "portfolio project," "demo," or "exploration of," not "production" or "deployed."
- Say "explored fairness slicing" or "implemented drift detection," not "monitors a production model."
- Never claim clinical validation, regulatory approval, or real-world use.
