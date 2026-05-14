from __future__ import annotations

from collections import defaultdict

import numpy as np
from lifelines import KaplanMeierFitter

from app.models import Patient, Prediction


class SurvivalAnalysisService:
    """Build Kaplan-Meier survival curves by risk tier."""

    def build_curves(
        self,
        patients: list[Patient],
        latest_predictions: dict[int, Prediction],
    ) -> dict[str, list[dict[str, float | str]]]:
        grouped_durations: dict[str, list[float]] = defaultdict(list)
        grouped_events: dict[str, list[int]] = defaultdict(list)

        for patient in patients:
            prediction = latest_predictions.get(patient.id)
            if not prediction:
                continue
            tier = self._normalize_tier(prediction.risk_category)
            if tier is None:
                continue

            grouped_durations[tier].append(float(patient.age))
            grouped_events[tier].append(1 if patient.has_historical_outcome else 0)

        curves: dict[str, list[dict[str, float | str]]] = {}
        for tier in ("Low", "Medium", "High"):
            durations = grouped_durations.get(tier, [])
            events = grouped_events.get(tier, [])
            if len(durations) < 2 or len(set(events)) == 1:
                curves[tier] = []
                continue

            fitter = KaplanMeierFitter()
            fitter.fit(np.asarray(durations), event_observed=np.asarray(events), label=tier)
            survival_df = fitter.survival_function_.reset_index()
            ci_df = fitter.confidence_interval_.reset_index()

            rows: list[dict[str, float | str]] = []
            for idx, row in survival_df.iterrows():
                rows.append(
                    {
                        "time": float(row["timeline"]),
                        "survival_probability": float(row[tier]),
                        "ci_lower": float(ci_df.iloc[idx, 1]),
                        "ci_upper": float(ci_df.iloc[idx, 2]),
                        "tier": tier,
                    }
                )
            curves[tier] = rows

        return curves

    @staticmethod
    def _normalize_tier(risk_category: str | None) -> str | None:
        mapping = {"low": "Low", "medium": "Medium", "high": "High"}
        if not risk_category:
            return None
        return mapping.get(risk_category.lower())
