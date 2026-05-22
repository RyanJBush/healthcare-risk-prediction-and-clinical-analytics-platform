# Cerberus — Synthetic Healthcare Risk Prediction Portfolio

> ⚠️ **Disclaimer:** Cerberus uses **synthetic data only** and contains **no PHI**. It is a student portfolio demo and is **not for clinical use**.

Cerberus is an educational ML + software engineering project that simulates a healthcare-inspired risk workflow. The project demonstrates end-to-end pipeline design, interpretable model outputs, and transparent limitations in a responsible portfolio format.

I am a **University of Maryland student studying Information Science and Electrical Engineering with a Business minor.**

## Project goal (high level)

Cerberus estimates general risk categories (for example, readmission-style or deterioration-style targets) from synthetic patient-like features. The objective is to demonstrate:

- feature engineering for tabular ML,
- baseline model training and comparison,
- explainability outputs (top contributing factors), and
- full-stack product thinking around review workflows.

This is an educational approximation of a risk-scoring pipeline, not a diagnostic or treatment tool.

## What this demonstrates

- Full-stack architecture: FastAPI backend + React frontend + SQL persistence.
- Tiered scoring pattern: quick heuristic path and model-based path.
- Explainability outputs with SHAP-style top factors and reason codes.
- Training run tracking and model-version registry concepts.
- Fairness-slice and drift-monitoring style analysis on synthetic cohorts.
- Role-aware workflows (RBAC, audit-style logs) in a demo environment.

## Live Demo

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Open-2ea44f?style=for-the-badge)](https://healthcare-risk.onrender.com)

## Tech Stack

| Layer | Technologies |
| --- | --- |
| Backend | Python, FastAPI, SQLAlchemy, JWT auth |
| Machine Learning | scikit-learn (LogisticRegression, RandomForestClassifier), SHAP |
| Frontend | React, Vite, Tailwind CSS, Recharts |
| Data | PostgreSQL (Docker) or SQLite (local tests) |
| Developer Tooling | Makefile, Docker Compose, pytest, ruff, mypy |

## Architecture

See [`docs/architecture.md`](docs/architecture.md) for architecture notes.

Pipeline summary: **Features → Model → Risk Score**

## Local run instructions

```bash
git clone https://github.com/RyanJBush/Healthcare-risk-prediction-and-clinical-intelligence-platform.git
cd Healthcare-risk-prediction-and-clinical-intelligence-platform
make setup
make dev
```

Then open:
- UI: `http://localhost:5173`
- API docs: `http://localhost:8000/docs`

## Synthetic data + model commands

Use these commands for a quick local demo loop:

```bash
# Seed synthetic records and run batch scoring
make demo-bootstrap

# Run a small offline fairness slice on synthetic data
make demo-fairness

# Trigger a small training run via API (defaults: readmission, 20 seeded rows)
make demo-train-small
```

You can also score one synthetic profile directly:

```bash
make demo-predict
```

## Demo workflow

1. Start services with `make dev`.
2. Seed synthetic cohort with `make demo-bootstrap`.
3. Optionally run `make demo-train-small` to create a small training run.
4. Sign in (`clinician / clinician123`) and review Dashboard, Triage, and Patient Detail.
5. Open Risk Analysis to compare model behavior and thresholds.

Detailed walkthrough: [`docs/demo-runbook.md`](docs/demo-runbook.md)

## Screenshots and portfolio materials

- Screenshot inventory + capture checklist: [`docs/screenshots/README.md`](docs/screenshots/README.md)
- Standalone portfolio page: [`docs/preview/index.html`](docs/preview/index.html)

All preview artifacts are from local, synthetic demo flows and are **not for clinical use**.


## Model Explainability

Cerberus includes SHAP-based explainability so each prediction can be decomposed into feature-level contributions. The SHAP waterfall plot starts from a baseline risk expectation and then shows how each feature pushes an individual prediction up or down, with larger bars indicating stronger contribution magnitude. Positive contributions move the patient toward higher modeled risk, while negative contributions move the patient toward lower modeled risk.

![SHAP Waterfall Plot Placeholder](docs/images/shap-waterfall.png)

## Risk Scoring Logic

Patient risk scoring follows a transparent sequence:

1. **Feature Inputs:** Synthetic patient attributes are assembled and normalized.
2. **ML Model Inference:** The trained classifier produces a risk probability score.
3. **SHAP Explanation:** Feature contributions are generated for interpretability and review.
4. **Risk Tier Mapping:** The continuous score is translated into **Low / Medium / High** operational tiers.

## Compliance & Ethics

> **Note:** This platform is built for educational and portfolio use with **synthetic and de-identified data only**. It is **not a clinical decision support tool** and must not be used for diagnosis, treatment, or real patient care decisions.

## Production Considerations

- HIPAA-adjacent architecture and compliance-oriented controls are documented in [`docs/hipaa-design-notes.md`](docs/hipaa-design-notes.md).

## Limitations and future work

- Synthetic records are simplified and do not reflect real populations.
- Metrics are demonstration-only and not clinically validated.
- No real-world deployment claims are made.
- Future work: calibration diagnostics, stronger synthetic cohort generation, and expanded monitoring UX.

## Resume bullets

Resume-ready project bullets: [`docs/resume-bullets.md`](docs/resume-bullets.md)

## License

MIT License: [`LICENSE`](LICENSE)
