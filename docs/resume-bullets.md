# Resume Bullets — Cerberus

- Built a healthcare ML portfolio demo with FastAPI, React, and PostgreSQL to score synthetic patient records across readmission, deterioration, and adverse-event targets.
- Implemented a tiered scoring workflow that runs a lightweight heuristic first and escalates low-confidence cases to scikit-learn models.
- Integrated SHAP-style explainability to return top feature contributions and reason codes with each risk score.
- Designed model-registry and training-run endpoints to track model versions and scoring provenance.
- Developed JWT + RBAC authorization for Clinician, Admin, Analyst, and Viewer roles in a multi-user API workflow.
- Added request-level audit logging for patient access and scoring actions to support traceable demo operations.
- Authored a fairness-slice CLI on synthetic cohorts to compare positive prediction rates and risk distributions by group.
- Created a drift-monitoring endpoint that compares incoming prediction distributions with training-time baselines.
- Containerized backend, frontend, and database services with Docker Compose and Make targets for local demo setup.
- Documented responsible-ML limitations in a model card with explicit synthetic-data and not-for-clinical-use framing.
