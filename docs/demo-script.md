# Nova AI Demo Script (Synthetic Data Only)

> **Safety disclaimer:** Nova AI outputs are clinical decision support signals for synthetic demo data only. They are not diagnostic recommendations.

## 1) Setup and launch

```bash
make doctor
make setup
make dev
```

If running non-Docker, see `README.md` for backend/frontend commands and `.env` setup.

## 2) Seed synthetic cohort

With backend running:

```bash
make demo-bootstrap
```

This logs in as admin, loads synthetic patients, runs batch scoring, and prints summary metrics.

## 3) Demo persona flow (8-10 minutes)

### Persona A: Triage Clinician
1. Login as `clinician / clinician123`.
2. Open **Triage**.
3. Switch between **Alert Queue** and **High-Risk Watchlist**.
4. Filter by target and review status.
5. Open a patient from the queue.

### Persona B: Clinical Reviewer
1. In **Patient Detail**, review latest predictions and explanation snapshot.
2. Add an observation and trigger recalculation.
3. Update review status.
4. Add a review note and inspect the unified timeline.

### Persona C: Analyst / Governance
1. Login as `analyst / analyst123`.
2. Open **Dashboard** and use cohort drill-down filters.
3. Open **Risk Analysis**:
   - review model comparison table,
   - inspect threshold simulation,
   - run a new evaluation,
   - inspect model cards and limitations.

## 4) Suggested narration points

- **Workflow readiness:** queue triage -> patient deep dive -> review action -> timeline traceability.
- **Explainability:** risk and protective factors are surfaced with provenance.
- **Trust controls:** visible disclaimer, model cards, and threshold/evaluation views.
- **Portfolio framing:** synthetic but production-style architecture and CI checks.

## 5) Demo reset

If needed, clear local DB artifacts and restart:

```bash
rm -f backend/nova.db backend/nova_test.db
make dev
```

Or reseed with different values:

```bash
API_BASE=http://localhost:8000 SEED_COUNT=75 SEED_VALUE=7 ./scripts/bootstrap_demo.sh
```
