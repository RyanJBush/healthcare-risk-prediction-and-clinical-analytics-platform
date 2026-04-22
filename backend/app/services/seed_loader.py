from __future__ import annotations

import random

from app.models import Patient


def generate_seed_patients(count: int, seed: int) -> list[Patient]:
    rng = random.Random(seed)
    patients: list[Patient] = []
    for idx in range(count):
        age = rng.randint(24, 89)
        bmi = round(rng.uniform(18.5, 40.0), 1)
        systolic_bp = round(rng.uniform(98, 176), 1)
        cholesterol = round(rng.uniform(130, 295), 1)
        glucose = round(rng.uniform(70, 255), 1)
        smoker = rng.random() < 0.22
        has_outcome = rng.random() < 0.35
        patients.append(
            Patient(
                full_name=f"Synthetic Patient {idx + 1}",
                masked_identifier=f"DEMO-{seed}-{idx + 1:04d}",
                age=age,
                bmi=bmi,
                blood_pressure=systolic_bp,
                cholesterol=cholesterol,
                glucose=glucose,
                smoker=smoker,
                has_historical_outcome=has_outcome,
            )
        )
    return patients
