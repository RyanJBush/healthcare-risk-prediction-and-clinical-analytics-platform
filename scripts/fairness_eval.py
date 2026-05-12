"""Fairness slice evaluation for the tiered risk model on synthetic data.

Generates a synthetic patient cohort with an artificial demographic attribute
(`group_a` / `group_b`) and reports per-slice positive-prediction rate,
mean risk score, and risk-category distribution. Useful for demonstrating
that fairness slicing has been considered, not for clinical claims.

Run:
    python scripts/fairness_eval.py --n 500 --seed 42

The script is deliberately self-contained (no DB required) and uses the same
`predict_tiered` function the API uses, so slices reflect the live model.
"""
from __future__ import annotations

import argparse
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path
from types import SimpleNamespace

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.ml import predict_tiered  # noqa: E402


def _synthetic_patient(rng: random.Random, group: str) -> SimpleNamespace:
    # Group_a is intentionally given a shifted glucose distribution so the
    # report demonstrates a measurable slice gap. This is synthetic and
    # has no real-world demographic meaning.
    glucose_shift = 20 if group == "group_a" else 0
    return SimpleNamespace(
        age=rng.randint(25, 85),
        bmi=round(rng.uniform(18, 40), 1),
        blood_pressure=round(rng.uniform(100, 175), 1),
        cholesterol=round(rng.uniform(140, 280), 1),
        glucose=round(rng.uniform(80, 200) + glucose_shift, 1),
        smoker=rng.random() < 0.25,
    )


def _build_cohort(n: int, seed: int) -> list[tuple[str, SimpleNamespace]]:
    rng = random.Random(seed)
    cohort: list[tuple[str, SimpleNamespace]] = []
    for _ in range(n):
        group = rng.choice(["group_a", "group_b"])
        cohort.append((group, _synthetic_patient(rng, group)))
    return cohort


def _summarize_slice(records: list[dict]) -> dict:
    if not records:
        return {"n": 0}
    n = len(records)
    mean_score = sum(r["risk_score"] for r in records) / n
    positive_rate = sum(1 for r in records if r["risk_category"] in ("medium", "high")) / n
    high_rate = sum(1 for r in records if r["risk_category"] == "high") / n
    categories = Counter(r["risk_category"] for r in records)
    return {
        "n": n,
        "mean_risk_score": round(mean_score, 3),
        "positive_rate_medium_or_high": round(positive_rate, 3),
        "high_rate": round(high_rate, 3),
        "category_counts": dict(categories),
    }


def evaluate(n: int, seed: int, target: str = "readmission") -> dict:
    cohort = _build_cohort(n, seed)
    by_group: dict[str, list[dict]] = defaultdict(list)
    for group, patient in cohort:
        for result in predict_tiered(patient):
            if result.target_type != target:
                continue
            by_group[group].append({
                "risk_score": result.risk_score,
                "risk_category": result.risk_category,
            })

    slices = {g: _summarize_slice(records) for g, records in by_group.items()}

    # Disparity metrics (group_a relative to group_b on positive-rate)
    a = slices.get("group_a", {})
    b = slices.get("group_b", {})
    disparity = None
    if a.get("n") and b.get("n"):
        pr_a = a["positive_rate_medium_or_high"]
        pr_b = b["positive_rate_medium_or_high"]
        disparity = {
            "positive_rate_difference": round(pr_a - pr_b, 3),
            "positive_rate_ratio": round((pr_a / pr_b) if pr_b else float("inf"), 3),
            "high_rate_difference": round(a["high_rate"] - b["high_rate"], 3),
        }

    return {
        "target": target,
        "n_total": n,
        "seed": seed,
        "slices": slices,
        "disparity_group_a_vs_group_b": disparity,
        "note": "Synthetic cohort; group_a has a shifted glucose distribution by design.",
    }


def _print_report(report: dict) -> None:
    print("Fairness slice evaluation (synthetic data — illustrative only)")
    print("=" * 64)
    print(f"target: {report['target']}   n: {report['n_total']}   seed: {report['seed']}")
    print()
    for group, summary in report["slices"].items():
        print(f"[{group}]")
        for k, v in summary.items():
            print(f"  {k}: {v}")
        print()
    if report["disparity_group_a_vs_group_b"]:
        print("disparity (group_a vs group_b):")
        for k, v in report["disparity_group_a_vs_group_b"].items():
            print(f"  {k}: {v}")
        print()
    print("note:", report["note"])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, default=500, help="synthetic cohort size")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--target", default="readmission",
                        choices=["readmission", "deterioration", "adverse_event"])
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    report = evaluate(args.n, args.seed, args.target)
    if args.json:
        import json
        print(json.dumps(report, indent=2))
    else:
        _print_report(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
