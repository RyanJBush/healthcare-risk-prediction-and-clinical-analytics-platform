from app import ml


def test_risk_category_threshold_branches() -> None:
    assert ml._risk_category(0.8, 0.5, 0.7) == "high"  # noqa: SLF001
    assert ml._risk_category(0.6, 0.5, 0.7) == "medium"  # noqa: SLF001
    assert ml._risk_category(0.4, 0.5, 0.7) == "low"  # noqa: SLF001


def test_build_rationale_handles_missing_reason_codes() -> None:
    assert ml._build_rationale("readmission", []) == "No dominant driver identified for readmission."  # noqa: SLF001
