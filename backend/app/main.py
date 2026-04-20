from collections import Counter
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import json
import uuid

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.ml import TARGET_CONFIGS, predict_tiered
from app.models import AuditLog, Explanation, ModelCard, Observation, Patient, Prediction, User
from app.schemas import (
    AuditLogRead,
    CohortMetrics,
    ExplanationRead,
    LoginRequest,
    MetricsSummary,
    ModelCardRead,
    ObservationCreate,
    ObservationRead,
    PatientCreate,
    PatientRead,
    PredictRequest,
    PredictionRead,
    ReviewStatusUpdate,
    TieredPredictionRead,
    Token,
    TriageQueueItem,
)
from app.security import create_access_token, hash_password, require_roles, verify_password


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    with Session(bind=engine) as db:
        if not db.query(User).first():
            db.add_all(
                [
                    User(username="admin", password_hash=hash_password("admin123"), role="admin"),
                    User(username="clinician", password_hash=hash_password("clinician123"), role="clinician"),
                    User(username="analyst", password_hash=hash_password("analyst123"), role="analyst"),
                    User(username="viewer", password_hash=hash_password("viewer123"), role="viewer"),
                ]
            )
        if not db.query(ModelCard).first():
            for target_type, config in TARGET_CONFIGS.items():
                db.add(
                    ModelCard(
                        model_name="Tiered Clinical Risk Engine",
                        model_version="tiered-v1",
                        target_type=target_type,
                        summary=f"Rule-calibrated {target_type} classifier with confidence scoring.",
                        intended_use="Clinical decision support triage, not autonomous diagnosis.",
                        limitations="Synthetic baseline calibration. Requires clinician judgment and context.",
                        threshold_config=json.dumps(config["thresholds"]),
                    )
                )
        db.commit()
    yield


app = FastAPI(title="Nova AI API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _mask_id() -> str:
    return f"PAT-{uuid.uuid4().hex[:8].upper()}"


def _audit(db: Session, action: str, resource_type: str, resource_id: str, actor: User | None, details: dict) -> None:
    db.add(
        AuditLog(
            user_id=actor.id if actor else None,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=json.dumps(details),
        )
    )


def _persist_tiered_predictions(db: Session, patient: Patient) -> list[Prediction]:
    persisted: list[Prediction] = []
    for result in predict_tiered(patient):
        prediction = Prediction(
            patient_id=patient.id,
            target_type=result.target_type,
            risk_score=result.risk_score,
            baseline_risk_score=result.baseline_risk_score,
            confidence_score=result.confidence_score,
            risk_category=result.risk_category,
            threshold_used=result.threshold_used,
            reason_codes=json.dumps(result.reason_codes),
            model_version="tiered-v1",
        )
        db.add(prediction)
        db.flush()
        db.add(
            Explanation(
                patient_id=patient.id,
                prediction_id=prediction.id,
                target_type=result.target_type,
                top_factors=json.dumps(result.top_factors),
                risk_factors=json.dumps(result.risk_factors),
                protective_factors=json.dumps(result.protective_factors),
                plain_summary=result.plain_summary,
                rationale_summary=result.rationale_summary,
                provenance=result.provenance,
            )
        )
        persisted.append(prediction)
    return persisted


def _latest_predictions_by_target(db: Session, target_type: str) -> dict[int, Prediction]:
    rows = (
        db.query(Prediction)
        .filter(Prediction.target_type == target_type)
        .order_by(Prediction.patient_id.asc(), Prediction.created_at.desc())
        .all()
    )
    latest: dict[int, Prediction] = {}
    for row in rows:
        latest.setdefault(row.patient_id, row)
    return latest

def _triage_priority_key(item: TriageQueueItem) -> tuple[bool, float, datetime]:
    """Sort high risk first, then by descending risk score, then oldest update first."""
    return (item.risk_category != "high", -item.risk_score, item.updated_at)


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
    actor: User = Depends(require_roles("admin", "clinician")),
) -> Patient:
    masked_identifier = payload.masked_identifier if payload.masked_identifier is not None else _mask_id()
    patient = Patient(**payload.model_dump(exclude_none=True), masked_identifier=masked_identifier)
    db.add(patient)
    _audit(db, "create_patient", "patient", str(patient.id), actor, {"masked_identifier": patient.masked_identifier})
    db.commit()
    db.refresh(patient)
    return patient


@app.get("/api/patients", response_model=list[PatientRead])
def list_patients(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "clinician", "analyst", "viewer")),
) -> list[Patient]:
    return db.query(Patient).order_by(Patient.created_at.desc()).all()


@app.get("/api/patients/{patient_id}", response_model=PatientRead)
def get_patient(
    patient_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "clinician", "analyst", "viewer")),
) -> Patient:
    patient = db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


@app.patch("/api/patients/{patient_id}/review-status", response_model=PatientRead)
def update_review_status(
    patient_id: int,
    payload: ReviewStatusUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles("admin", "clinician")),
) -> Patient:
    patient = db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    patient.review_status = payload.review_status
    patient.assigned_reviewer = payload.assigned_reviewer
    _audit(
        db,
        "update_review_status",
        "patient",
        str(patient_id),
        actor,
        {"review_status": payload.review_status, "assigned_reviewer": payload.assigned_reviewer},
    )
    db.commit()
    db.refresh(patient)
    return patient


@app.post("/api/patients/{patient_id}/observations", response_model=ObservationRead, status_code=status.HTTP_201_CREATED)
def create_observation(
    patient_id: int,
    payload: ObservationCreate,
    recalculate_risk: bool = Query(default=True),
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles("admin", "clinician")),
) -> Observation:
    patient = db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    values = payload.model_dump()
    missing = [
        key
        for key in ["heart_rate", "systolic_bp", "diastolic_bp", "oxygen_saturation", "creatinine", "glucose"]
        if values.get(key) is None
    ]

    observation = Observation(
        patient_id=patient_id,
        observed_at=payload.observed_at or datetime.now(timezone.utc),
        heart_rate=payload.heart_rate,
        systolic_bp=payload.systolic_bp,
        diastolic_bp=payload.diastolic_bp,
        oxygen_saturation=payload.oxygen_saturation,
        creatinine=payload.creatinine,
        glucose=payload.glucose,
        missingness_flags=json.dumps(missing),
        source=payload.source,
    )

    # Update baseline model inputs with latest observation values used by the risk engine.
    if payload.systolic_bp is not None:
        patient.blood_pressure = payload.systolic_bp
    if payload.glucose is not None:
        patient.glucose = payload.glucose

    db.add(observation)
    if recalculate_risk:
        _persist_tiered_predictions(db, patient)

    _audit(
        db,
        "create_observation",
        "observation",
        str(patient_id),
        actor,
        {"recalculate_risk": recalculate_risk, "source": payload.source},
    )
    db.commit()
    db.refresh(observation)
    return observation


@app.get("/api/patients/{patient_id}/observations", response_model=list[ObservationRead])
def list_observations(
    patient_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "clinician", "analyst", "viewer")),
) -> list[Observation]:
    return (
        db.query(Observation)
        .filter(Observation.patient_id == patient_id)
        .order_by(Observation.observed_at.desc(), Observation.created_at.desc())
        .all()
    )


@app.post("/api/predict", response_model=PredictionRead)
def create_prediction(
    payload: PredictRequest,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles("admin", "clinician")),
) -> Prediction:
    patient = db.get(Patient, payload.patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    predictions = _persist_tiered_predictions(db, patient)
    _audit(db, "run_tiered_prediction", "patient", str(patient.id), actor, {"targets": len(predictions)})
    db.commit()

    primary = next((item for item in predictions if item.target_type == "readmission"), predictions[0])
    db.refresh(primary)
    return primary


@app.post("/api/predict/tiered", response_model=TieredPredictionRead)
def create_tiered_prediction(
    payload: PredictRequest,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles("admin", "clinician")),
) -> TieredPredictionRead:
    patient = db.get(Patient, payload.patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    predictions = _persist_tiered_predictions(db, patient)
    _audit(db, "run_tiered_prediction", "patient", str(patient.id), actor, {"targets": len(predictions)})
    db.commit()
    for prediction in predictions:
        db.refresh(prediction)
    return TieredPredictionRead(patient_id=patient.id, predictions=predictions)


@app.get("/api/predictions/{patient_id}", response_model=list[PredictionRead])
def get_predictions(
    patient_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles("admin", "clinician", "analyst", "viewer")),
) -> list[Prediction]:
    predictions = db.query(Prediction).filter(Prediction.patient_id == patient_id).order_by(Prediction.created_at.desc()).all()
    _audit(db, "view_predictions", "patient", str(patient_id), actor, {"count": len(predictions)})
    db.commit()
    return predictions


@app.get("/api/explanations/{patient_id}", response_model=list[ExplanationRead])
def get_explanations(
    patient_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles("admin", "clinician", "analyst", "viewer")),
) -> list[Explanation]:
    explanations = db.query(Explanation).filter(Explanation.patient_id == patient_id).order_by(Explanation.created_at.desc()).all()
    _audit(db, "view_explanations", "patient", str(patient_id), actor, {"count": len(explanations)})
    db.commit()
    return explanations


@app.get("/api/triage/queue", response_model=list[TriageQueueItem])
def triage_queue(
    status_filter: str | None = Query(default=None, alias="status"),
    target_type: str = Query(default="readmission"),
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles("admin", "clinician", "analyst", "viewer")),
) -> list[TriageQueueItem]:
    latest = _latest_predictions_by_target(db, target_type)
    patients = db.query(Patient).order_by(Patient.created_at.desc()).all()

    queue: list[TriageQueueItem] = []
    for patient in patients:
        prediction = latest.get(patient.id)
        if not prediction:
            continue
        if status_filter and patient.review_status != status_filter:
            continue
        if prediction.risk_category not in {"medium", "high"}:
            continue
        queue.append(
            TriageQueueItem(
                patient_id=patient.id,
                masked_identifier=patient.masked_identifier,
                review_status=patient.review_status,
                assigned_reviewer=patient.assigned_reviewer,
                target_type=prediction.target_type,
                risk_score=prediction.risk_score,
                risk_category=prediction.risk_category,
                confidence_score=prediction.confidence_score,
                updated_at=prediction.created_at,
            )
        )

    queue.sort(key=_triage_priority_key, reverse=False)
    _audit(db, "view_triage_queue", "triage", target_type, actor, {"results": len(queue), "status": status_filter})
    db.commit()
    return queue


@app.get("/api/metrics/summary", response_model=MetricsSummary)
def metrics_summary(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "clinician", "analyst", "viewer")),
) -> MetricsSummary:
    total_patients = db.query(func.count(Patient.id)).scalar() or 0
    total_predictions = db.query(func.count(Prediction.id)).scalar() or 0

    latest_readmission = _latest_predictions_by_target(db, "readmission")
    latest_predictions = list(latest_readmission.values())

    average_risk_score = (
        float(sum(prediction.risk_score for prediction in latest_predictions) / len(latest_predictions)) if latest_predictions else 0.0
    )
    by_category = dict(Counter(prediction.risk_category for prediction in latest_predictions))

    high_risk_patients = sum(1 for prediction in latest_predictions if prediction.risk_category == "high")
    alerts_triggered = sum(1 for prediction in latest_predictions if prediction.risk_category in {"medium", "high"})
    monitored_cohort_size = (
        db.query(func.count(Patient.id)).filter(Patient.review_status == "monitored").scalar() or 0
    )

    outcome_patients = db.query(Patient).filter(Patient.has_historical_outcome.is_(True)).all()
    if outcome_patients:
        outcome_ids = {patient.id for patient in outcome_patients}
        true_positives = sum(
            1
            for patient_id in outcome_ids
            if patient_id in latest_readmission and latest_readmission[patient_id].risk_category in {"medium", "high"}
        )
        recall = true_positives / len(outcome_ids)
    else:
        recall = 0.0

    return MetricsSummary(
        total_patients=total_patients,
        total_predictions=total_predictions,
        average_risk_score=round(average_risk_score, 4),
        high_risk_patients=high_risk_patients,
        alerts_triggered=alerts_triggered,
        recall_at_threshold=round(float(recall), 4),
        monitored_cohort_size=monitored_cohort_size,
        by_category=by_category,
    )


@app.get("/api/metrics/cohorts", response_model=CohortMetrics)
def cohort_metrics(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "clinician", "analyst", "viewer")),
) -> CohortMetrics:
    patients = db.query(Patient).all()
    by_review_status = dict(Counter(patient.review_status for patient in patients))

    average_risk_by_target: dict[str, float] = {}
    for target_type in TARGET_CONFIGS:
        target_predictions = list(_latest_predictions_by_target(db, target_type).values())
        if target_predictions:
            average_risk_by_target[target_type] = round(
                float(sum(prediction.risk_score for prediction in target_predictions) / len(target_predictions)), 4
            )
        else:
            average_risk_by_target[target_type] = 0.0

    high_risk_watchlist_size = sum(
        1
        for prediction in _latest_predictions_by_target(db, "readmission").values()
        if prediction.risk_category == "high"
    )

    return CohortMetrics(
        by_review_status=by_review_status,
        average_risk_by_target=average_risk_by_target,
        high_risk_watchlist_size=high_risk_watchlist_size,
    )


@app.get("/api/model-cards", response_model=list[ModelCardRead])
def list_model_cards(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "clinician", "analyst", "viewer")),
) -> list[ModelCard]:
    return db.query(ModelCard).order_by(ModelCard.target_type.asc()).all()


@app.get("/api/audit/logs", response_model=list[AuditLogRead])
def list_audit_logs(
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "analyst")),
) -> list[AuditLog]:
    return db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).all()
