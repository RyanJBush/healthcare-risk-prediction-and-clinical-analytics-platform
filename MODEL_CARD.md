# Model Card — Nova AI Clinical Risk Prediction

> Following the [Model Cards for Model Reporting](https://arxiv.org/abs/1810.03993) framework (Mitchell et al., 2019)

---

## Model Details

| Field | Value |
|---|---|
| **Model type** | Gradient Boosted Trees (XGBoost / scikit-learn ensemble) |
| **Task** | Multi-label clinical risk classification |
| **Version** | 1.0.0 |
| **Author** | Ryan Bush |
| **Contact** | ryanjbush@gmail.com |
| **Last updated** | 2026 |

---

## Intended Use

**Primary use:** Demonstration of ML-based clinical risk stratification in a portfolio context.

**Intended users:** Technical reviewers, recruiters, and developers exploring healthcare ML architectures.

**Out-of-scope uses:**
- Clinical decision support in real patient care settings
- Any use involving real patient data
- Regulatory submission or FDA-cleared use

---

## Training Data

- **Source:** Fully synthetic patient data generated programmatically — no real patient records, PHI, or PII
- **Size:** Configurable via seed scripts (default: 10,000 synthetic encounters)
- **Features:** Demographics, vitals, lab values, diagnosis codes (ICD-10 synthetic), medication history, comorbidity scores
- **Label generation:** Rule-based synthetic risk labels derived from clinical heuristics (not real outcomes)

---

## Evaluation

| Metric | Value (synthetic holdout) |
|---|---|
| AUC-ROC | ≥ 0.85 (synthetic data) |
| Precision | Reported per-label in evaluation notebook |
| Recall | Reported per-label in evaluation notebook |
| F1 | Reported per-label in evaluation notebook |

> ⚠️ These metrics are measured on **synthetic data only** and should not be interpreted as real clinical performance.

---

## Explainability

- **SHAP values** are computed for every prediction, providing per-feature contribution scores
- **Feature importance** rankings are available globally and per-patient
- **Natural language explanations** are generated for clinical summaries using the LLM integration layer

---

## Known Limitations & Biases

- **Synthetic data bias:** The model is trained on synthetic data generated from heuristic rules. Real clinical populations exhibit far more complex, correlated, and unexpected patterns.
- **No real validation:** This model has not been validated against real clinical outcomes, EHR data, or any clinical benchmark dataset.
- **Label noise:** Synthetic risk labels are imperfect proxies for real clinical risk; they are useful for architectural demonstration only.
- **Distribution shift:** Any deployment on real data would require full retraining, validation, and clinical review.
- **Demographic fairness:** Bias analysis has not been performed. Real clinical ML requires fairness audits across age, sex, race, and socioeconomic dimensions before any deployment.

---

## Ethical Considerations

- This model is **not suitable for clinical use** in its current form
- Healthcare ML carries significant ethical responsibility — false negatives in risk prediction can result in patient harm
- Real deployment would require IRB review, clinical validation, regulatory review (FDA SaMD pathway), and ongoing monitoring
- The project intentionally demonstrates explainability tooling (SHAP) as a step toward auditable, trustworthy clinical AI

---

## Caveats

This model card describes a **portfolio demonstration project**. All performance numbers are on synthetic data. Do not use this model in any clinical, research, or production context without full retraining, validation, and appropriate regulatory review.
