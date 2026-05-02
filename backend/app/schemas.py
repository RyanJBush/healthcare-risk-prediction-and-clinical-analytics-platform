from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ReviewStatus = Literal["new", "reviewed", "escalated", "monitored"]
TargetType = Literal["readmission", "deterioration", "adverse_event"]


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    username: str
    password: str


class PatientCreate(BaseModel):
    full_name: str = Field(min_length=2)
    masked_identifier: str | None = Field(default=None, min_length=4, max_length=32)
    age: int = Field(ge=0, le=120)
    bmi: float = Field(ge=5, le=80)
    blood_pressure: float = Field(ge=40, le=300)
    cholesterol: float = Field(ge=40, le=500)
    glucose: float = Field(ge=30, le=500)
    smoker: bool = False
    has_historical_outcome: bool = False


class PatientRead(PatientCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    review_status: ReviewStatus
    assigned_reviewer: str | None = None
    created_at: datetime


class PredictRequest(BaseModel):
    patient_id: int


class PredictionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: int
    target_type: TargetType
    risk_score: float
    baseline_risk_score: float
    confidence_score: float
    risk_category: str
    threshold_used: float
    reason_codes: str
    model_version: str
    created_at: datetime


class ExplanationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: int
    prediction_id: int
    target_type: TargetType
    top_factors: str
    risk_factors: str
    protective_factors: str
    plain_summary: str
    rationale_summary: str
    provenance: str
    created_at: datetime


class TieredPredictionRead(BaseModel):
    patient_id: int
    predictions: list[PredictionRead]


class ModelRiskPredictionRead(BaseModel):
    model_name: str
    risk_score: float
    risk_category: str


class PatientRiskModelComparisonRead(BaseModel):
    patient_id: int
    target_type: TargetType
    models: list[ModelRiskPredictionRead]


class ReviewStatusUpdate(BaseModel):
    review_status: ReviewStatus
    assigned_reviewer: str | None = Field(default=None, max_length=64)


class TriageQueueItem(BaseModel):
    patient_id: int
    masked_identifier: str
    review_status: ReviewStatus
    assigned_reviewer: str | None = None
    target_type: TargetType
    risk_score: float
    risk_category: str
    confidence_score: float
    updated_at: datetime


class ObservationCreate(BaseModel):
    observed_at: datetime | None = None
    heart_rate: float | None = Field(default=None, ge=20, le=260)
    systolic_bp: float | None = Field(default=None, ge=40, le=300)
    diastolic_bp: float | None = Field(default=None, ge=20, le=200)
    oxygen_saturation: float | None = Field(default=None, ge=40, le=100)
    creatinine: float | None = Field(default=None, ge=0.1, le=20)
    glucose: float | None = Field(default=None, ge=30, le=500)
    source: str = Field(default="ehr", max_length=32)


class ObservationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: int
    observed_at: datetime
    heart_rate: float | None = None
    systolic_bp: float | None = None
    diastolic_bp: float | None = None
    oxygen_saturation: float | None = None
    creatinine: float | None = None
    glucose: float | None = None
    missingness_flags: str
    source: str
    created_at: datetime


class MetricsSummary(BaseModel):
    total_patients: int
    total_predictions: int
    average_risk_score: float
    high_risk_patients: int
    alerts_triggered: int
    recall_at_threshold: float
    monitored_cohort_size: int
    by_category: dict[str, int]


class CohortMetrics(BaseModel):
    by_review_status: dict[str, int]
    average_risk_by_target: dict[str, float]
    high_risk_watchlist_size: int


class ModelCardRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    model_name: str
    model_version: str
    target_type: str
    summary: str
    intended_use: str
    limitations: str
    threshold_config: str
    created_at: datetime


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int | None = None
    action: str
    resource_type: str
    resource_id: str
    details: str
    created_at: datetime


class ReviewNoteCreate(BaseModel):
    note_text: str = Field(min_length=5, max_length=4000)
    recommendation: str | None = Field(default=None, max_length=2000)
    state_from: ReviewStatus | None = None
    state_to: ReviewStatus | None = None


class ReviewNoteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: int
    user_id: int | None = None
    note_text: str
    recommendation: str | None = None
    state_from: ReviewStatus | None = None
    state_to: ReviewStatus | None = None
    created_at: datetime


class ExplanationHistoryItem(BaseModel):
    explanation_id: int
    prediction_id: int
    target_type: TargetType
    risk_score: float
    risk_delta_vs_previous: float
    plain_summary: str
    rationale_summary: str
    created_at: datetime


class ModelEvaluationItem(BaseModel):
    model_name: str
    sample_size: int
    positive_rate: float
    roc_auc: float
    pr_auc: float
    precision: float
    recall: float
    f1: float
    brier: float
    false_negative_count: int
    false_positive_count: int
    threshold: float
    cost_score: float


class ModelComparisonRead(BaseModel):
    target_type: TargetType
    split: str
    evaluated_at: datetime
    models: list[ModelEvaluationItem]
    subgroup_outcomes: dict[str, float] = {}
    threshold_sweep: list[dict[str, float | int]] = []


class ThresholdUpdateRequest(BaseModel):
    target_type: TargetType
    medium_threshold: float = Field(ge=0.05, le=0.95)
    high_threshold: float = Field(ge=0.1, le=0.99)
    rationale: str = Field(min_length=8, max_length=2000)


class ModelConfigChangeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    target_type: str
    changed_by_user_id: int | None = None
    previous_thresholds: str
    new_thresholds: str
    rationale: str
    created_at: datetime


class AiPatientSummaryRead(BaseModel):
    patient_id: int
    generated_at: datetime
    summary: str
    top_risk_drivers: list[str]
    protective_factors: list[str]
    follow_up_questions: list[str]


class HandoffSummaryRead(BaseModel):
    generated_at: datetime
    panel_size: int
    high_risk_count: int
    monitored_count: int
    escalated_count: int
    summary: str
    priority_patients: list[str]


class BatchScoringJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    requested_by_user_id: int | None = None
    status: str
    patient_count: int
    scored_count: int
    target_type: str
    model_version: str
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime


class BatchScoringRequest(BaseModel):
    target_type: TargetType | Literal["all"] = "all"
    limit: int | None = Field(default=None, ge=1, le=1000)


class SeedLoadRequest(BaseModel):
    count: int = Field(default=50, ge=1, le=500)
    seed: int = Field(default=42, ge=0)


class SeedLoadResult(BaseModel):
    created_count: int
    seed: int
    first_patient_id: int | None = None


class EvaluationRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    requested_by_user_id: int | None = None
    target_type: str
    threshold: float
    status: str
    metrics_json: str
    created_at: datetime


class PatientAccessGrantCreate(BaseModel):
    user_id: int
    patient_id: int
    can_view: bool = True


class PatientAccessGrantRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    patient_id: int
    can_view: bool
    created_at: datetime


class DisclaimerRead(BaseModel):
    message: str
    version: str


class TrainingRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    requested_by_user_id: int | None = None
    target_type: str
    model_family: str
    artifact_path: str
    metrics_json: str
    status: str
    created_at: datetime


class TrainingRunRequest(BaseModel):
    target_type: TargetType = "readmission"


class RegistryModelRead(BaseModel):
    name: str
    version: str
    target_type: str
    family: str
    description: str


class TimelineEventRead(BaseModel):
    event_type: str
    event_id: int
    event_time: datetime
    summary: str


class FollowUpRecommendationRead(BaseModel):
    patient_id: int
    generated_at: datetime
    risk_category: str
    recommendations: list[str]


class CohortPatientRead(BaseModel):
    patient_id: int
    masked_identifier: str
    review_status: str
    risk_category: str
    risk_score: float


class NoteSummaryRead(BaseModel):
    patient_id: int
    generated_at: datetime
    note_count: int
    summary: str


class FollowUpQuestionsRead(BaseModel):
    patient_id: int
    generated_at: datetime
    questions: list[str]
