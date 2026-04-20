from collections import Counter

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.ml import predict_with_explanation
from app.models import Explanation, Patient, Prediction, User
from app.schemas import (
    ExplanationRead,
    LoginRequest,
    MetricsSummary,
    PatientCreate,
    PatientRead,
    PredictRequest,
    PredictionRead,
    Token,
)
from app.security import create_access_token, hash_password, require_roles, verify_password

app = FastAPI(title="Nova AI API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
    with Session(bind=engine) as db:
        if not db.query(User).first():
            db.add_all(
                [
                    User(username="admin", password_hash=hash_password("admin123"), role="admin"),
                    User(username="clinician", password_hash=hash_password("clinician123"), role="clinician"),
                ]
            )
            db.commit()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/auth/login", response_model=Token)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> Token:
    user = db.query(User).filter(User.username == payload.username).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return Token(access_token=create_access_token(user.username, user.role))


@app.post("/api/patients", response_model=PatientRead, status_code=status.HTTP_201_CREATED)
def create_patient(
    payload: PatientCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "clinician")),
) -> Patient:
    patient = Patient(**payload.model_dump())
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient


@app.get("/api/patients", response_model=list[PatientRead])
def list_patients(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "clinician")),
) -> list[Patient]:
    return db.query(Patient).order_by(Patient.created_at.desc()).all()


@app.get("/api/patients/{patient_id}", response_model=PatientRead)
def get_patient(
    patient_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "clinician")),
) -> Patient:
    patient = db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


@app.post("/api/predict", response_model=PredictionRead)
def create_prediction(
    payload: PredictRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "clinician")),
) -> Prediction:
    patient = db.get(Patient, payload.patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    score, category, top_factors = predict_with_explanation(patient)
    prediction = Prediction(patient_id=patient.id, risk_score=score, risk_category=category)
    db.add(prediction)
    db.flush()
    db.add(Explanation(patient_id=patient.id, prediction_id=prediction.id, top_factors=top_factors))
    db.commit()
    db.refresh(prediction)
    return prediction


@app.get("/api/predictions/{patient_id}", response_model=list[PredictionRead])
def get_predictions(
    patient_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "clinician")),
) -> list[Prediction]:
    return db.query(Prediction).filter(Prediction.patient_id == patient_id).order_by(Prediction.created_at.desc()).all()


@app.get("/api/explanations/{patient_id}", response_model=list[ExplanationRead])
def get_explanations(
    patient_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "clinician")),
) -> list[Explanation]:
    return db.query(Explanation).filter(Explanation.patient_id == patient_id).order_by(Explanation.created_at.desc()).all()


@app.get("/api/metrics/summary", response_model=MetricsSummary)
def metrics_summary(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "clinician")),
) -> MetricsSummary:
    total_patients = db.query(func.count(Patient.id)).scalar() or 0
    predictions = db.query(Prediction).all()
    total_predictions = len(predictions)
    average_risk_score = float(sum(p.risk_score for p in predictions) / total_predictions) if total_predictions else 0.0
    by_category = dict(Counter(p.risk_category for p in predictions))
    return MetricsSummary(
        total_patients=total_patients,
        total_predictions=total_predictions,
        average_risk_score=round(average_risk_score, 4),
        by_category=by_category,
    )
