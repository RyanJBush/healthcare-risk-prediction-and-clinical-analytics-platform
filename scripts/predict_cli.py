"""Score a single synthetic patient from the command line.

Uses the same tiered risk engine that powers the FastAPI scoring endpoint, so
results match what the API would return for an identical input vector.

Example:
    python scripts/predict_cli.py --age 72 --bmi 31 --bp 158 --chol 245 \
        --glucose 180 --smoker 1
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.ml import predict_tiered  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Score a synthetic patient with the tiered risk engine.")
    parser.add_argument("--age", type=int, required=True)
    parser.add_argument("--bmi", type=float, required=True)
    parser.add_argument("--bp", type=float, required=True, dest="blood_pressure", help="systolic blood pressure")
    parser.add_argument("--chol", type=float, required=True, dest="cholesterol")
    parser.add_argument("--glucose", type=float, required=True)
    parser.add_argument("--smoker", type=int, choices=[0, 1], default=0)
    parser.add_argument("--json", action="store_true", help="emit raw JSON instead of a human-readable summary")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    patient = SimpleNamespace(
        age=args.age,
        bmi=args.bmi,
        blood_pressure=args.blood_pressure,
        cholesterol=args.cholesterol,
        glucose=args.glucose,
        smoker=bool(args.smoker),
    )
    results = predict_tiered(patient)

    if args.json:
        print(json.dumps([asdict(r) for r in results], indent=2))
        return 0

    print("Tiered risk scores (synthetic data — not for clinical use):")
    print("-" * 60)
    for r in results:
        print(f"  {r.target_type:>14}  score={r.risk_score:.2f}  "
              f"category={r.risk_category:<6}  confidence={r.confidence_score:.2f}")
        top = ", ".join(f"{f['feature']}({f['impact']:+.2f})" for f in r.top_factors)
        print(f"                 top factors: {top}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
