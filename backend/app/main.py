from collections import Counter
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import csv
from io import StringIO
import json
import logging
import time
import uuid

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.ml import TARGET_CONFIGS, predict_tiered
from app.models import (
    AuditLog,
    BatchScoringJob,
    EvaluationRun,
    Explanation,
    ModelCard,
    ModelConfigChange,
    Observation,
    Patient,
    PatientAccessGrant,
    Prediction,
    User,
    TrainingRun,
)
from app.models import ReviewNote
from app.schemas import (
    AiPatientSummaryRead,
    AuditLogRead,
    BatchScoringJobRead,
    BatchScoringRequest,
    CohortMetrics,
    EvaluationRunRead,
    ExplanationRead,
    ExplanationHistoryItem,
    HandoffSummaryRead,
    LoginRequest,
    MetricsSummary,
    ModelComparisonRead,
    ModelConfigChangeRead,
    ModelCardRead,
    ObservationCreate,
    ObservationRead,
    PatientCreate,
    PatientAccessGrantCreate,
    PatientAccessGrantRead,
    PatientRead,
    PredictRequest,
    PredictionRead,
    CohortPatientRead,
    ReviewNoteCreate,
    ReviewNoteRead,
    ReviewStatusUpdate,
    TrainingRunRead,
    TrainingRunRequest,
    SeedLoadRequest,
    SeedLoadResult,
    ThresholdUpdateRequest,
    TieredPredictionRead,
    Token,
    TriageQueueItem,
    DisclaimerRead,
    RegistryModelRead,
    TimelineEventRead,
    FollowUpRecommendationRead,
    FollowUpQuestionsRead,
    NoteSummaryRead,
)
from app.security import create_access_token, hash_password, require_roles, verify_password
from app.services.evaluation import DEFAULT_THRESHOLD, evaluate_models
from app.services.model_registry import build_default_registry
from app.services.seed_loader import generate_seed_patients
from app.services.summaries import (
    build_follow_up_questions,
    build_follow_up_recommendations,
    build_handoff_summary,
    build_note_summary,
    build_patient_summary,
)
from app.services.training import run_offline_training


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
logger = logging.getLogger("nova-api")
logging.basicConfig(level=logging.INFO)
MODEL_REGISTRY = build_default_registry()
DISCLAIMER_VERSION = "clinical-cds-v1"


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


def _ensure_patient_access(db: Session, patient_id: int, actor: User) -> None:
    if actor.role in {"admin", "clinician"}:
        return
    grant = (
        db.query(PatientAccessGrant)
        .filter(
            PatientAccessGrant.user_id == actor.id,
            PatientAccessGrant.patient_id == patient_id,
            PatientAccessGrant.can_view.is_(True),
        )
        .first()
    )
    if not grant:
        raise HTTPException(status_code=403, detail="No patient-level access grant for this user")


def _persist_tiered_predictions(db: Session, patient: Patient) -> list[Prediction]:
    persisted: list[Prediction] = []
    for result in predict_tiered(patient):
        selected_model = MODEL_REGISTRY.resolve(result.target_type, "tiered-v1")
        prediction = Prediction(
            patient_id=patient.id,
            target_type=result.target_type,
            risk_score=result.risk_score,
            baseline_risk_score=result.baseline_risk_score,
            confidence_score=result.confidence_score,
            risk_category=result.risk_category,
            threshold_used=result.threshold_used,
            reason_codes=json.dumps(result.reason_codes),
            model_version=selected_model.version if selected_model else "tiered-v1",
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


@app.middleware("http")
async def request_tracing(request: Request, call_next):
    started = time.perf_counter()
    request_id = request.headers.get("x-request-id", uuid.uuid4().hex[:12])
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - started) * 1000, 2)
    response.headers["x-request-id"] = request_id
    logger.info(
        "request_completed method=%s path=%s status=%s duration_ms=%s request_id=%s",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
        request_id,
    )
    return response


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
def readiness(db: Session = Depends(get_db)) -> dict[str, str]:
    db.execute(text("SELECT 1"))
    return {"status": "ready"}


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
    db.flush()
    _audit(db, "create_patient", "patient", str(patient.id), actor, {"masked_identifier": patient.masked_identifier})
    db.commit()
    db.refresh(patient)
    return patient


@app.get("/api/patients", response_model=list[PatientRead])
def list_patients(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    sort: str = Query(default="created_at_desc"),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "clinician", "analyst", "viewer")),
) -> list[Patient]:
    query = db.query(Patient)
    if sort == "created_at_asc":
        query = query.order_by(Patient.created_at.asc())
    elif sort == "age_desc":
        query = query.order_by(Patient.age.desc())
    elif sort == "age_asc":
        query = query.order_by(Patient.age.asc())
    else:
        query = query.order_by(Patient.created_at.desc())
    return query.offset(offset).limit(limit).all()


@app.get("/api/patients/{patient_id}", response_model=PatientRead)
def get_patient(
    patient_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles("admin", "clinician", "analyst", "viewer")),
) -> Patient:
    _ensure_patient_access(db, patient_id, actor)
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
    actor: User = Depends(require_roles("admin", "clinician", "analyst", "viewer")),
) -> list[Observation]:
    _ensure_patient_access(db, patient_id, actor)
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


@app.post("/api/jobs/batch-score", response_model=BatchScoringJobRead, status_code=status.HTTP_201_CREATED)
def start_batch_scoring(
    payload: BatchScoringRequest,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles("admin", "clinician")),
) -> BatchScoringJob:
    query = db.query(Patient).order_by(Patient.created_at.desc())
    if payload.limit is not None:
        query = query.limit(payload.limit)
    patients = query.all()

    job = BatchScoringJob(
        requested_by_user_id=actor.id,
        status="running",
        patient_count=len(patients),
        scored_count=0,
        target_type=payload.target_type,
        model_version="tiered-v1",
        started_at=datetime.now(timezone.utc),
    )
    db.add(job)
    db.flush()

    for patient in patients:
        generated = _persist_tiered_predictions(db, patient)
        if payload.target_type != "all":
            for prediction in generated:
                if prediction.target_type != payload.target_type:
                    db.delete(prediction)
        job.scored_count += 1

    job.status = "completed"
    job.finished_at = datetime.now(timezone.utc)
    _audit(db, "run_batch_scoring", "batch_job", str(job.id), actor, {"patient_count": job.patient_count})
    db.commit()
    db.refresh(job)
    return job


@app.get("/api/jobs/batch-score/{job_id}", response_model=BatchScoringJobRead)
def get_batch_scoring_job(
    job_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "clinician", "analyst")),
) -> BatchScoringJob:
    job = db.get(BatchScoringJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Batch job not found")
    return job


@app.get("/api/predictions/{patient_id}", response_model=list[PredictionRead])
def get_predictions(
    patient_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles("admin", "clinician", "analyst", "viewer")),
) -> list[Prediction]:
    _ensure_patient_access(db, patient_id, actor)
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
    _ensure_patient_access(db, patient_id, actor)
    explanations = db.query(Explanation).filter(Explanation.patient_id == patient_id).order_by(Explanation.created_at.desc()).all()
    _audit(db, "view_explanations", "patient", str(patient_id), actor, {"count": len(explanations)})
    db.commit()
    return explanations


@app.get("/api/explanations/{patient_id}/history", response_model=list[ExplanationHistoryItem])
def get_explanation_history(
    patient_id: int,
    target_type: str = Query(default="readmission"),
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles("admin", "clinician", "analyst", "viewer")),
) -> list[ExplanationHistoryItem]:
    _ensure_patient_access(db, patient_id, actor)
    rows = (
        db.query(Explanation, Prediction)
        .join(Prediction, Explanation.prediction_id == Prediction.id)
        .filter(Explanation.patient_id == patient_id, Explanation.target_type == target_type)
        .order_by(Explanation.created_at.asc())
        .all()
    )

    history: list[ExplanationHistoryItem] = []
    previous_score: float | None = None
    for explanation, prediction in rows:
        delta = 0.0 if previous_score is None else round(float(prediction.risk_score - previous_score), 4)
        history.append(
            ExplanationHistoryItem(
                explanation_id=explanation.id,
                prediction_id=prediction.id,
                target_type=prediction.target_type,
                risk_score=prediction.risk_score,
                risk_delta_vs_previous=delta,
                plain_summary=explanation.plain_summary,
                rationale_summary=explanation.rationale_summary,
                created_at=explanation.created_at,
            )
        )
        previous_score = prediction.risk_score

    _audit(db, "view_explanation_history", "patient", str(patient_id), actor, {"target_type": target_type, "count": len(history)})
    db.commit()
    return list(reversed(history))


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


@app.get("/api/triage/watchlist", response_model=list[TriageQueueItem])
def high_risk_watchlist(
    target_type: str = Query(default="readmission"),
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles("admin", "clinician", "analyst", "viewer")),
) -> list[TriageQueueItem]:
    latest = _latest_predictions_by_target(db, target_type)
    patients = db.query(Patient).order_by(Patient.created_at.desc()).all()

    watchlist: list[TriageQueueItem] = []
    for patient in patients:
        prediction = latest.get(patient.id)
        if not prediction or prediction.risk_category != "high":
            continue
        watchlist.append(
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

    watchlist.sort(key=_triage_priority_key, reverse=False)
    _audit(db, "view_high_risk_watchlist", "triage", target_type, actor, {"results": len(watchlist)})
    db.commit()
    return watchlist


@app.get("/api/cohorts/filter", response_model=list[CohortPatientRead])
def filter_cohort(
    review_status: str | None = Query(default=None),
    risk_category: str | None = Query(default=None),
    target_type: str = Query(default="readmission"),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "clinician", "analyst", "viewer")),
) -> list[CohortPatientRead]:
    latest = _latest_predictions_by_target(db, target_type)
    patients = db.query(Patient).order_by(Patient.created_at.desc()).all()
    rows: list[CohortPatientRead] = []
    for patient in patients:
        prediction = latest.get(patient.id)
        if not prediction:
            continue
        if review_status and patient.review_status != review_status:
            continue
        if risk_category and prediction.risk_category != risk_category:
            continue
        rows.append(
            CohortPatientRead(
                patient_id=patient.id,
                masked_identifier=patient.masked_identifier,
                review_status=patient.review_status,
                risk_category=prediction.risk_category,
                risk_score=prediction.risk_score,
            )
        )
    return rows


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
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "analyst")),
) -> list[AuditLog]:
    return db.query(AuditLog).order_by(AuditLog.created_at.desc()).offset(offset).limit(limit).all()


@app.post("/api/patients/{patient_id}/notes", response_model=ReviewNoteRead, status_code=status.HTTP_201_CREATED)
def create_review_note(
    patient_id: int,
    payload: ReviewNoteCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles("admin", "clinician")),
) -> ReviewNote:
    patient = db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    note = ReviewNote(patient_id=patient_id, user_id=actor.id, **payload.model_dump())
    db.add(note)
    _audit(
        db,
        "create_review_note",
        "patient",
        str(patient_id),
        actor,
        {"state_from": payload.state_from, "state_to": payload.state_to},
    )
    db.commit()
    db.refresh(note)
    return note


@app.get("/api/patients/{patient_id}/notes", response_model=list[ReviewNoteRead])
def list_review_notes(
    patient_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles("admin", "clinician", "analyst", "viewer")),
) -> list[ReviewNote]:
    _ensure_patient_access(db, patient_id, actor)
    notes = (
        db.query(ReviewNote)
        .filter(ReviewNote.patient_id == patient_id)
        .order_by(ReviewNote.created_at.desc())
        .all()
    )
    _audit(db, "view_review_notes", "patient", str(patient_id), actor, {"count": len(notes)})
    db.commit()
    return notes


@app.get("/api/evaluation/model-comparison", response_model=ModelComparisonRead)
def model_comparison(
    target_type: str = Query(default="readmission"),
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles("admin", "analyst")),
) -> ModelComparisonRead:
    patients = db.query(Patient).order_by(Patient.created_at.asc()).all()
    result = evaluate_models(patients)
    _audit(db, "run_model_comparison", "evaluation", target_type, actor, {"models": len(result["models"])})
    db.commit()
    return ModelComparisonRead(target_type=target_type, **result)


@app.post("/api/evaluation/runs", response_model=EvaluationRunRead, status_code=status.HTTP_201_CREATED)
def create_evaluation_run(
    target_type: str = Query(default="readmission"),
    threshold: float = Query(default=DEFAULT_THRESHOLD, ge=0.1, le=0.95),
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles("admin", "analyst")),
) -> EvaluationRun:
    patients = db.query(Patient).order_by(Patient.created_at.asc()).all()
    result = evaluate_models(patients, threshold=threshold)
    run = EvaluationRun(
        requested_by_user_id=actor.id,
        target_type=target_type,
        threshold=threshold,
        status="completed",
        metrics_json=json.dumps(result, default=str),
    )
    db.add(run)
    db.flush()
    _audit(db, "create_evaluation_run", "evaluation_run", str(run.id), actor, {"threshold": threshold})
    db.commit()
    db.refresh(run)
    return run


@app.get("/api/evaluation/runs", response_model=list[EvaluationRunRead])
def list_evaluation_runs(
    limit: int = Query(default=20, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "analyst")),
) -> list[EvaluationRun]:
    return db.query(EvaluationRun).order_by(EvaluationRun.created_at.desc()).limit(limit).all()


@app.get("/api/evaluation/runs/{run_id}", response_model=EvaluationRunRead)
def get_evaluation_run(
    run_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "analyst")),
) -> EvaluationRun:
    run = db.get(EvaluationRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Evaluation run not found")
    return run


@app.post("/api/training/runs", response_model=TrainingRunRead, status_code=status.HTTP_201_CREATED)
def create_training_run(
    payload: TrainingRunRequest,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles("admin", "analyst")),
) -> TrainingRun:
    run = TrainingRun(
        requested_by_user_id=actor.id,
        target_type=payload.target_type,
        model_family="logistic_regression",
        status="running",
    )
    db.add(run)
    db.flush()
    patients = db.query(Patient).order_by(Patient.created_at.asc()).all()
    training_result = run_offline_training(patients=patients, target_type=payload.target_type, run_id=run.id)
    run.status = training_result["status"]
    run.artifact_path = training_result["artifact_path"]
    run.metrics_json = training_result["metrics_json"]
    _audit(db, "create_training_run", "training_run", str(run.id), actor, {"target_type": payload.target_type})
    db.commit()
    db.refresh(run)
    return run


@app.get("/api/training/runs", response_model=list[TrainingRunRead])
def list_training_runs(
    limit: int = Query(default=20, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "analyst")),
) -> list[TrainingRun]:
    return db.query(TrainingRun).order_by(TrainingRun.created_at.desc()).limit(limit).all()


@app.get("/api/training/runs/{run_id}", response_model=TrainingRunRead)
def get_training_run(
    run_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "analyst")),
) -> TrainingRun:
    run = db.get(TrainingRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Training run not found")
    return run


@app.get("/api/model-registry", response_model=list[RegistryModelRead])
def list_model_registry(
    _: User = Depends(require_roles("admin", "clinician", "analyst", "viewer")),
) -> list[RegistryModelRead]:
    return [RegistryModelRead(**item.__dict__) for item in MODEL_REGISTRY.list_all()]


@app.post("/api/model-config/thresholds", response_model=ModelConfigChangeRead, status_code=status.HTTP_201_CREATED)
def update_thresholds(
    payload: ThresholdUpdateRequest,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles("admin")),
) -> ModelConfigChange:
    if payload.high_threshold <= payload.medium_threshold:
        raise HTTPException(status_code=422, detail="high_threshold must be greater than medium_threshold")
    target_config = TARGET_CONFIGS[payload.target_type]
    previous = dict(target_config["thresholds"])
    updated = {"medium": payload.medium_threshold, "high": payload.high_threshold}
    target_config["thresholds"] = updated

    model_card = (
        db.query(ModelCard)
        .filter(ModelCard.target_type == payload.target_type, ModelCard.model_version == "tiered-v1")
        .first()
    )
    if model_card:
        model_card.threshold_config = json.dumps(updated)

    change = ModelConfigChange(
        target_type=payload.target_type,
        changed_by_user_id=actor.id,
        previous_thresholds=json.dumps(previous),
        new_thresholds=json.dumps(updated),
        rationale=payload.rationale,
    )
    db.add(change)
    _audit(
        db,
        "update_thresholds",
        "model_config",
        payload.target_type,
        actor,
        {"previous": previous, "updated": updated},
    )
    db.commit()
    db.refresh(change)
    return change


@app.get("/api/model-config/changes", response_model=list[ModelConfigChangeRead])
def list_model_config_changes(
    target_type: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "analyst")),
) -> list[ModelConfigChange]:
    query = db.query(ModelConfigChange)
    if target_type:
        query = query.filter(ModelConfigChange.target_type == target_type)
    return query.order_by(ModelConfigChange.created_at.desc()).limit(limit).all()


@app.post("/api/access/grants", response_model=PatientAccessGrantRead, status_code=status.HTTP_201_CREATED)
def create_patient_access_grant(
    payload: PatientAccessGrantCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles("admin")),
) -> PatientAccessGrant:
    user = db.get(User, payload.user_id)
    patient = db.get(Patient, payload.patient_id)
    if not user or not patient:
        raise HTTPException(status_code=404, detail="User or patient not found")

    existing = (
        db.query(PatientAccessGrant)
        .filter(PatientAccessGrant.user_id == payload.user_id, PatientAccessGrant.patient_id == payload.patient_id)
        .first()
    )
    if existing:
        existing.can_view = payload.can_view
        grant = existing
    else:
        grant = PatientAccessGrant(**payload.model_dump())
        db.add(grant)
    _audit(
        db,
        "upsert_patient_access_grant",
        "patient_access_grant",
        f"{payload.user_id}:{payload.patient_id}",
        actor,
        {"can_view": payload.can_view},
    )
    db.commit()
    db.refresh(grant)
    return grant


@app.get("/api/access/grants", response_model=list[PatientAccessGrantRead])
def list_patient_access_grants(
    user_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "analyst")),
) -> list[PatientAccessGrant]:
    query = db.query(PatientAccessGrant)
    if user_id is not None:
        query = query.filter(PatientAccessGrant.user_id == user_id)
    return query.order_by(PatientAccessGrant.created_at.desc()).all()


@app.get("/api/disclaimer", response_model=DisclaimerRead)
def get_disclaimer() -> DisclaimerRead:
    return DisclaimerRead(
        message=(
            "Nova AI outputs are clinical decision support signals and must be reviewed with full chart context. "
            "Do not use as sole basis for diagnosis or treatment."
        ),
        version=DISCLAIMER_VERSION,
    )


@app.get("/api/patients/{patient_id}/ai-summary", response_model=AiPatientSummaryRead)
def patient_ai_summary(
    patient_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles("admin", "clinician", "analyst", "viewer")),
) -> AiPatientSummaryRead:
    _ensure_patient_access(db, patient_id, actor)
    patient = db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    latest_prediction = (
        db.query(Prediction)
        .filter(Prediction.patient_id == patient_id, Prediction.target_type == "readmission")
        .order_by(Prediction.created_at.desc())
        .first()
    )
    latest_explanation = (
        db.query(Explanation)
        .filter(Explanation.patient_id == patient_id, Explanation.target_type == "readmission")
        .order_by(Explanation.created_at.desc())
        .first()
    )
    summary = build_patient_summary(patient, latest_prediction, latest_explanation)
    _audit(db, "generate_patient_ai_summary", "patient", str(patient_id), actor, {"has_prediction": latest_prediction is not None})
    db.commit()
    return AiPatientSummaryRead(**summary)


@app.get("/api/patients/{patient_id}/recommendations", response_model=FollowUpRecommendationRead)
def patient_follow_up_recommendations(
    patient_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles("admin", "clinician", "analyst", "viewer")),
) -> FollowUpRecommendationRead:
    _ensure_patient_access(db, patient_id, actor)
    latest_prediction = (
        db.query(Prediction)
        .filter(Prediction.patient_id == patient_id, Prediction.target_type == "readmission")
        .order_by(Prediction.created_at.desc())
        .first()
    )
    risk_category = latest_prediction.risk_category if latest_prediction else "unknown"
    return FollowUpRecommendationRead(**build_follow_up_recommendations(patient_id=patient_id, risk_category=risk_category))


@app.get("/api/patients/{patient_id}/follow-up-questions", response_model=FollowUpQuestionsRead)
def patient_follow_up_questions(
    patient_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles("admin", "clinician", "analyst", "viewer")),
) -> FollowUpQuestionsRead:
    _ensure_patient_access(db, patient_id, actor)
    latest_prediction = (
        db.query(Prediction)
        .filter(Prediction.patient_id == patient_id, Prediction.target_type == "readmission")
        .order_by(Prediction.created_at.desc())
        .first()
    )
    risk_category = latest_prediction.risk_category if latest_prediction else "unknown"
    return FollowUpQuestionsRead(**build_follow_up_questions(patient_id=patient_id, risk_category=risk_category))


@app.get("/api/patients/{patient_id}/note-summary", response_model=NoteSummaryRead)
def patient_note_summary(
    patient_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles("admin", "clinician", "analyst", "viewer")),
) -> NoteSummaryRead:
    _ensure_patient_access(db, patient_id, actor)
    notes = (
        db.query(ReviewNote.note_text)
        .filter(ReviewNote.patient_id == patient_id)
        .order_by(ReviewNote.created_at.desc())
        .limit(10)
        .all()
    )
    return NoteSummaryRead(**build_note_summary(patient_id=patient_id, notes=[row[0] for row in notes]))


@app.get("/api/patients/{patient_id}/timeline", response_model=list[TimelineEventRead])
def patient_timeline(
    patient_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles("admin", "clinician", "analyst", "viewer")),
) -> list[TimelineEventRead]:
    _ensure_patient_access(db, patient_id, actor)
    events: list[TimelineEventRead] = []

    predictions = db.query(Prediction).filter(Prediction.patient_id == patient_id).all()
    for prediction in predictions:
        events.append(
            TimelineEventRead(
                event_type="prediction",
                event_id=prediction.id,
                event_time=prediction.created_at,
                summary=f"{prediction.target_type} risk {prediction.risk_score:.2f} ({prediction.risk_category})",
            )
        )

    observations = db.query(Observation).filter(Observation.patient_id == patient_id).all()
    for observation in observations:
        events.append(
            TimelineEventRead(
                event_type="observation",
                event_id=observation.id,
                event_time=observation.observed_at,
                summary=f"HR {observation.heart_rate or '—'}, SBP {observation.systolic_bp or '—'}, glucose {observation.glucose or '—'}",
            )
        )

    notes = db.query(ReviewNote).filter(ReviewNote.patient_id == patient_id).all()
    for note in notes:
        events.append(
            TimelineEventRead(
                event_type="review_note",
                event_id=note.id,
                event_time=note.created_at,
                summary=note.note_text[:160],
            )
        )

    return sorted(events, key=lambda item: item.event_time, reverse=True)


@app.get("/api/cohorts/handoff-summary", response_model=HandoffSummaryRead)
def cohort_handoff_summary(
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles("admin", "clinician", "analyst")),
) -> HandoffSummaryRead:
    patients = db.query(Patient).order_by(Patient.created_at.desc()).all()
    latest = _latest_predictions_by_target(db, "readmission")
    prioritized = [
        patient.masked_identifier
        for patient in patients
        if patient.id in latest and latest[patient.id].risk_category == "high"
    ]
    summary = build_handoff_summary(
        masked_identifiers=prioritized,
        high_risk_count=len(prioritized),
        monitored_count=sum(1 for patient in patients if patient.review_status == "monitored"),
        escalated_count=sum(1 for patient in patients if patient.review_status == "escalated"),
        panel_size=len(patients),
    )
    _audit(db, "generate_handoff_summary", "cohort", "readmission", actor, {"panel_size": len(patients)})
    db.commit()
    return HandoffSummaryRead(**summary)


@app.post("/api/demo/load-seed", response_model=SeedLoadResult, status_code=status.HTTP_201_CREATED)
def load_seed_dataset(
    payload: SeedLoadRequest,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles("admin")),
) -> SeedLoadResult:
    generated = generate_seed_patients(payload.count, payload.seed)
    db.add_all(generated)
    db.flush()
    first_patient_id = generated[0].id if generated else None
    _audit(db, "load_seed_dataset", "patient_dataset", str(payload.seed), actor, {"count": payload.count})
    db.commit()
    return SeedLoadResult(created_count=len(generated), seed=payload.seed, first_patient_id=first_patient_id)


@app.get("/api/reports/cohort.csv")
def export_cohort_report_csv(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "clinician", "analyst")),
) -> Response:
    patients = db.query(Patient).order_by(Patient.created_at.desc()).all()
    latest = _latest_predictions_by_target(db, "readmission")
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["masked_identifier", "age", "review_status", "risk_score", "risk_category", "confidence_score"])
    for patient in patients:
        prediction = latest.get(patient.id)
        writer.writerow(
            [
                patient.masked_identifier,
                patient.age,
                patient.review_status,
                prediction.risk_score if prediction else "",
                prediction.risk_category if prediction else "",
                prediction.confidence_score if prediction else "",
            ]
        )
    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=cohort_report.csv"},
    )
