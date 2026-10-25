"""FastAPI ingestion, scoring, review, health, and monitoring service."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import desc, func, select, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from gameguard import __version__
from gameguard.config import settings
from gameguard.db import SessionLocal, TelemetryEvent
from gameguard.monitoring import metrics_summary, monitoring_report
from gameguard.schemas import BatchInput, FeedbackInput, TelemetryInput
from gameguard.scoring import load_scorer

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("gameguard.api")
REQUESTS: dict[str, deque[float]] = defaultdict(deque)
ERRORS = 0


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.scorer = load_scorer(settings.model_path)
    app.state.started_at = datetime.now(UTC)
    yield


app = FastAPI(
    title="GameGuard Telemetry API",
    version=__version__,
    description=(
        "Scores hardware telemetry deviations. Scores are not probabilities and flags are "
        "review signals, not evidence of cheating or intent."
    ),
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.allowed_origins),
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Content-Type", "X-API-Key"],
)


def scorer(request: Request):
    return request.app.state.scorer


def session_dependency():
    with SessionLocal() as session:
        yield session


def require_api_key(x_api_key: str = Header(default="")) -> None:
    if settings.api_key and not hmac.compare_digest(x_api_key, settings.api_key):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


@app.middleware("http")
async def bounded_requests(request: Request, call_next):
    global ERRORS
    if request.url.path.startswith("/v1/"):
        now = time.monotonic()
        bucket = REQUESTS[request.client.host if request.client else "unknown"]
        while bucket and now - bucket[0] > 60:
            bucket.popleft()
        if len(bucket) >= 120:
            return Response(
                content='{"detail":"Rate limit exceeded"}',
                status_code=429,
                media_type="application/json",
            )
        bucket.append(now)
    try:
        response = await call_next(request)
        if request.url.path.startswith("/v1/") and response.status_code >= 400:
            ERRORS += 1
        return response
    except Exception:
        ERRORS += 1
        logger.exception("Unhandled API error")
        raise


def _payload(event: TelemetryInput) -> dict:
    return event.model_dump(exclude_none=True, exclude={"event_id"})


def _event_id(event: TelemetryInput) -> str:
    source = event.event_id or json.dumps(_payload(event), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def _public_record(record: TelemetryEvent) -> dict:
    return {
        "event_id": record.event_id,
        "timestamp_ms": record.timestamp_ms,
        "session_label": record.session_label,
        "payload": record.payload,
        "anomaly_score": record.anomaly_score,
        "is_anomaly": record.is_anomaly,
        "threshold": None,
        "model_version": record.model_version,
        "quality_status": record.quality_status,
        "evidence": record.evidence,
        "latency_ms": record.latency_ms,
        "review_status": record.review_status,
        "review_note": record.review_note,
        "created_at_utc": record.created_at.isoformat() if record.created_at else None,
    }


def _score_persist(event: TelemetryInput, active_scorer, db: Session) -> tuple[dict, bool]:
    identifier = _event_id(event)
    existing = db.scalar(select(TelemetryEvent).where(TelemetryEvent.event_id == identifier))
    if existing:
        result = _public_record(existing)
        result["duplicate"] = True
        return result, True
    payload = _payload(event)
    result = active_scorer.score_event(payload)
    record = TelemetryEvent(
        event_id=identifier,
        timestamp_ms=result["timestamp_ms"],
        session_label=result["session_label"],
        payload=payload,
        anomaly_score=result["anomaly_score"],
        is_anomaly=result["is_anomaly"],
        model_version=result["model_version"],
        quality_status=result["quality_status"],
        evidence=result["evidence"],
        latency_ms=result["latency_ms"],
    )
    db.add(record)
    try:
        db.commit()
        db.refresh(record)
    except IntegrityError:
        db.rollback()
        existing = db.scalar(select(TelemetryEvent).where(TelemetryEvent.event_id == identifier))
        if existing:
            result = _public_record(existing)
            result["duplicate"] = True
            return result, True
        raise
    response = _public_record(record)
    response["threshold"] = active_scorer.threshold
    response["missing_features"] = result["missing_features"]
    response["duplicate"] = False
    return response, False


@app.get("/health")
def health():
    return {"status": "ok", "service": "gameguard-api", "version": __version__}


@app.get("/ready")
def ready(active_scorer=Depends(scorer), db: Session = Depends(session_dependency)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ready", "model_version": active_scorer.version, "database": "connected"}
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="Database unavailable") from exc


@app.get("/v1/model/info", dependencies=[Depends(require_api_key)])
def model_info(active_scorer=Depends(scorer)):
    metadata = active_scorer.metadata
    return {
        key: metadata[key]
        for key in (
            "model_version",
            "created_at_utc",
            "dataset",
            "dataset_config",
            "dataset_sha256",
            "source_rows",
            "feature_names",
            "detector",
            "threshold",
            "threshold_rule",
            "alert_budget",
            "split",
            "anomaly_score_semantics",
            "feature_evidence",
        )
    }


@app.post("/v1/score", dependencies=[Depends(require_api_key)])
def score_only(event: TelemetryInput, active_scorer=Depends(scorer)):
    return active_scorer.score_event(_payload(event))


@app.post("/v1/events", dependencies=[Depends(require_api_key)])
def ingest_event(
    event: TelemetryInput,
    active_scorer=Depends(scorer),
    db: Session = Depends(session_dependency),
):
    try:
        result, _ = _score_persist(event, active_scorer, db)
        return result
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Event persistence failed")
        raise HTTPException(status_code=503, detail="Event persistence unavailable") from exc


@app.post("/v1/events/batch", dependencies=[Depends(require_api_key)])
def ingest_batch(
    batch: BatchInput,
    active_scorer=Depends(scorer),
    db: Session = Depends(session_dependency),
):
    results = []
    duplicates = 0
    for event in batch.events:
        try:
            result, duplicate = _score_persist(event, active_scorer, db)
            results.append(result)
            duplicates += int(duplicate)
        except SQLAlchemyError as exc:
            db.rollback()
            logger.exception("Batch record persistence failed")
            raise HTTPException(status_code=503, detail="Batch persistence unavailable") from exc
    return {"accepted": len(results), "duplicates": duplicates, "results": results}


@app.get("/v1/events", dependencies=[Depends(require_api_key)])
def list_events(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    flagged: bool | None = None,
    min_score: float | None = None,
    db: Session = Depends(session_dependency),
):
    query = select(TelemetryEvent)
    count_query = select(func.count()).select_from(TelemetryEvent)
    if flagged is not None:
        query = query.where(TelemetryEvent.is_anomaly.is_(flagged))
        count_query = count_query.where(TelemetryEvent.is_anomaly.is_(flagged))
    if min_score is not None:
        query = query.where(TelemetryEvent.anomaly_score >= min_score)
        count_query = count_query.where(TelemetryEvent.anomaly_score >= min_score)
    total = int(db.scalar(count_query) or 0)
    records = list(
        db.scalars(
            query.order_by(desc(TelemetryEvent.timestamp_ms))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    return {
        "items": [_public_record(item) for item in records],
        "page": page,
        "page_size": page_size,
        "total": total,
    }


@app.get("/v1/alerts", dependencies=[Depends(require_api_key)])
def list_alerts(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    status: str | None = Query(
        default=None, pattern="^(likely_true_anomaly|false_positive|unresolved)$"
    ),
    db: Session = Depends(session_dependency),
):
    query = select(TelemetryEvent).where(TelemetryEvent.is_anomaly.is_(True))
    if status:
        query = query.where(TelemetryEvent.review_status == status)
    count_query = (
        select(func.count()).select_from(TelemetryEvent).where(TelemetryEvent.is_anomaly.is_(True))
    )
    if status:
        count_query = count_query.where(TelemetryEvent.review_status == status)
    total_count = int(db.scalar(count_query) or 0)
    records = list(
        db.scalars(
            query.order_by(desc(TelemetryEvent.timestamp_ms))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    return {
        "items": [_public_record(item) for item in records],
        "page": page,
        "page_size": page_size,
        "total": total_count,
    }


@app.patch("/v1/alerts/{event_id}/feedback", dependencies=[Depends(require_api_key)])
def review_alert(
    event_id: str,
    feedback: FeedbackInput,
    db: Session = Depends(session_dependency),
):
    record = db.scalar(select(TelemetryEvent).where(TelemetryEvent.event_id == event_id))
    if record is None or not record.is_anomaly:
        raise HTTPException(status_code=404, detail="Alert not found")
    record.review_status = feedback.status
    record.review_note = feedback.note
    db.commit()
    db.refresh(record)
    return _public_record(record)


@app.get("/v1/metrics/summary", dependencies=[Depends(require_api_key)])
def summary(db: Session = Depends(session_dependency), active_scorer=Depends(scorer)):
    return metrics_summary(db, active_scorer, ERRORS)


@app.get("/v1/monitoring", dependencies=[Depends(require_api_key)])
def monitoring(db: Session = Depends(session_dependency), active_scorer=Depends(scorer)):
    return monitoring_report(db, active_scorer, ERRORS)


@app.get("/metrics", dependencies=[Depends(require_api_key)])
def prometheus_metrics(db: Session = Depends(session_dependency), active_scorer=Depends(scorer)):
    data = metrics_summary(db, active_scorer, ERRORS)
    content = (
        "\n".join(
            [
                "# HELP gameguard_events_total Total telemetry events persisted",
                "# TYPE gameguard_events_total counter",
                f"gameguard_events_total {data['events_total']}",
                "# HELP gameguard_alerts_total Total flagged events persisted",
                "# TYPE gameguard_alerts_total counter",
                f"gameguard_alerts_total {data['alerts_total']}",
                "# HELP gameguard_ingestion_throughput_events_per_second_last_minute Average persisted events per second over the last minute",
                "# TYPE gameguard_ingestion_throughput_events_per_second_last_minute gauge",
                "gameguard_ingestion_throughput_events_per_second_last_minute "
                f"{data['ingestion_throughput_events_per_second_last_minute']}",
                "# HELP gameguard_ingestion_errors_since_start_total API request and persistence errors since process start",
                "# TYPE gameguard_ingestion_errors_since_start_total counter",
                f"gameguard_ingestion_errors_since_start_total {data['ingestion_errors_since_start']}",
                "# HELP gameguard_process_memory_rss_mb Resident process memory in MiB",
                "# TYPE gameguard_process_memory_rss_mb gauge",
                f"gameguard_process_memory_rss_mb {data['process_memory_rss_mb']}",
                "# HELP gameguard_process_cpu_percent Process CPU usage percentage",
                "# TYPE gameguard_process_cpu_percent gauge",
                f"gameguard_process_cpu_percent {data['process_cpu_percent']}",
                "# HELP gameguard_scoring_latency_ms_p95 P95 scoring latency over the last 24 hours",
                "# TYPE gameguard_scoring_latency_ms_p95 gauge",
                f"gameguard_scoring_latency_ms_p95 {data['p95_scoring_latency_ms_last_24h'] or 0}",
            ]
        )
        + "\n"
    )
    return Response(content=content, media_type="text/plain; version=0.0.4")
