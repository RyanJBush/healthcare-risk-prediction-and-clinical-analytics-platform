"""Smoke tests for the CLI and fairness-eval scripts.

These tests exercise the scripts as imported modules so we don't shell out
from pytest.
"""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))


def test_predict_cli_returns_three_targets():
    from app.ml import predict_tiered

    patient = SimpleNamespace(
        age=72, bmi=31, blood_pressure=158, cholesterol=245, glucose=180, smoker=True,
    )
    results = predict_tiered(patient)
    targets = {r.target_type for r in results}
    assert targets == {"readmission", "deterioration", "adverse_event"}
    for r in results:
        assert 0.0 <= r.risk_score <= 1.0
        assert r.risk_category in {"low", "medium", "high"}
        assert len(r.top_factors) == 3


def test_fairness_eval_produces_slice_summary():
    import fairness_eval

    report = fairness_eval.evaluate(n=120, seed=7, target="readmission")
    assert report["n_total"] == 120
    assert set(report["slices"].keys()) == {"group_a", "group_b"}
    for summary in report["slices"].values():
        assert summary["n"] > 0
        assert 0.0 <= summary["mean_risk_score"] <= 1.0
        assert 0.0 <= summary["positive_rate_medium_or_high"] <= 1.0
    assert report["disparity_group_a_vs_group_b"] is not None
