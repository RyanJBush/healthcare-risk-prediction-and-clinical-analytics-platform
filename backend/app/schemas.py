from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    username: str
    password: str


class PatientCreate(BaseModel):
    full_name: str = Field(min_length=2)
    age: int = Field(ge=0, le=120)
    bmi: float = Field(ge=5, le=80)
    blood_pressure: float = Field(ge=40, le=300)
    cholesterol: float = Field(ge=40, le=500)
    glucose: float = Field(ge=30, le=500)
    smoker: bool = False


class PatientRead(PatientCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


class PredictRequest(BaseModel):
    patient_id: int


class PredictionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: int
    risk_score: float
    risk_category: str
    model_version: str
    created_at: datetime


class ExplanationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: int
    prediction_id: int
    top_factors: str
    created_at: datetime


class MetricsSummary(BaseModel):
    total_patients: int
    total_predictions: int
    average_risk_score: float
    by_category: dict[str, int]
