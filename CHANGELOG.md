# Changelog

## [1.0.0] - 2026-05

### Added
- README enhancements covering live demo badge, SHAP explainability details, risk scoring logic, compliance/ethics notice, and a structured tech stack table.
- `docs/images/.gitkeep` to establish a dedicated documentation image directory for future screenshots.
- GitHub Actions workflow (`.github/workflows/ci.yml`) for Python 3.11 CI with Ruff linting and pytest smoke testing.
- Minimal smoke test at `tests/test_smoke.py` for CI validation.

## [0.2.0] - 2026-05-14

### Added
- HIPAA-adjacent design notes with de-identification, audit logging, encryption, and RBAC guidance.
- Survival analytics service with Kaplan-Meier curves and `/analytics/survival-curves` API.
- Calibration curve analytics endpoint `/analytics/calibration-curve` and frontend visualization.
- GitHub Actions CI workflow for backend tests and frontend build.

### Changed
- Added `lifelines` dependency in backend requirements and pyproject metadata.
