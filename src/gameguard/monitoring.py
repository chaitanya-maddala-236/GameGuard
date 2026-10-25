"""Descriptive operational metrics and feature-drift calculations."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd
import psutil
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from gameguard.db import TelemetryEvent
from gameguard.features import FEATURE_NAMES, transform_frame


def _psi(expected: list[int], observed: np.ndarray) -> float:
    expected_arr = np.asarray(expected, dtype=float)
    observed_arr = np.asarray(observed, dtype=float)
    if expected_arr.sum() == 0 or observed_arr.sum() == 0:
        return 0.0
    expected_pct = np.maximum(expected_arr / expected_arr.sum(), 1e-6)
    observed_pct = np.maximum(observed_arr / observed_arr.sum(), 1e-6)
    return float(np.sum((observed_pct - expected_pct) * np.log(observed_pct / expected_pct)))


def _drift_report(events: list[TelemetryEvent], scorer) -> dict[str, Any]:
    if len(events) < 50:
        return {
            "status": "insufficient_data",
            "sample_size": len(events),
            "features": {},
            "note": "At least 50 recent events are required before PSI is reported.",
        }
    frame = pd.DataFrame([item.payload for item in events])
    current = transform_frame(frame)
    expected = scorer.metadata["reference_distribution"]
    results = {}
    for name in FEATURE_NAMES:
        bins = expected[name]
        edges = np.asarray(bins["edges"], dtype=float)
        values = current[name].dropna().to_numpy(dtype=float)
        if len(edges) < 2 or len(values) == 0:
            continue
        clipped_edges = edges.copy()
        clipped_edges[0], clipped_edges[-1] = -np.inf, np.inf
        counts = np.histogram(values, bins=clipped_edges)[0]
        psi = _psi(bins["counts"], counts)
        results[name] = {"psi": psi, "drift_signal": psi >= 0.2}
    return {
        "status": "measured",
        "sample_size": len(events),
        "features": results,
        "drift_signal_count": sum(1 for value in results.values() if value["drift_signal"]),
        "note": "PSI indicates input-distribution change versus the training split; it is not model-performance degradation.",
    }


def metrics_summary(session: Session, scorer, error_count: int = 0) -> dict[str, Any]:
    now = datetime.now(UTC)
    since = now - timedelta(hours=24)
    minute_since = now - timedelta(minutes=1)
    recent = list(
        session.scalars(
            select(TelemetryEvent)
            .where(TelemetryEvent.created_at >= since)
            .order_by(TelemetryEvent.created_at.desc())
            .limit(5000)
        )
    )
    total = int(session.scalar(select(func.count()).select_from(TelemetryEvent)) or 0)
    minute_count = int(
        session.scalar(
            select(func.count())
            .select_from(TelemetryEvent)
            .where(TelemetryEvent.created_at >= minute_since)
        )
        or 0
    )
    all_alerts = int(
        session.scalar(
            select(func.count())
            .select_from(TelemetryEvent)
            .where(TelemetryEvent.is_anomaly.is_(True))
        )
        or 0
    )
    recent_count = len(recent)
    scores = np.asarray([event.anomaly_score for event in recent], dtype=float)
    latency = np.asarray([event.latency_ms for event in recent], dtype=float)
    quality = Counter(event.quality_status for event in recent)
    reviewed = Counter(event.review_status for event in recent)
    process = psutil.Process()
    return {
        "as_of_utc": now.isoformat(),
        "model_version": scorer.version,
        "events_total": total,
        "events_last_24h": recent_count,
        "events_last_minute": minute_count,
        "ingestion_throughput_events_per_second_last_minute": minute_count / 60,
        "alerts_total": all_alerts,
        "alerts_last_24h": sum(event.is_anomaly for event in recent),
        "alert_rate_last_24h": float(np.mean([event.is_anomaly for event in recent]))
        if recent
        else 0.0,
        "average_scoring_latency_ms_last_24h": float(np.mean(latency)) if len(latency) else None,
        "p95_scoring_latency_ms_last_24h": float(np.quantile(latency, 0.95))
        if len(latency)
        else None,
        "score_p50_last_24h": float(np.quantile(scores, 0.50)) if len(scores) else None,
        "score_p95_last_24h": float(np.quantile(scores, 0.95)) if len(scores) else None,
        "data_quality_last_24h": dict(quality),
        "review_status_last_24h": dict(reviewed),
        "ingestion_errors_since_start": error_count,
        "process_memory_rss_mb": process.memory_info().rss / (1024 * 1024),
        "process_cpu_percent": process.cpu_percent(interval=None),
        "process_thread_count": process.num_threads(),
        "last_scored_at_utc": recent[0].created_at.isoformat() if recent else None,
    }


def monitoring_report(session: Session, scorer, error_count: int = 0) -> dict[str, Any]:
    since = datetime.now(UTC) - timedelta(hours=24)
    recent = list(
        session.scalars(
            select(TelemetryEvent)
            .where(TelemetryEvent.created_at >= since)
            .order_by(TelemetryEvent.created_at.desc())
            .limit(5000)
        )
    )
    return {
        "summary": metrics_summary(session, scorer, error_count),
        "feature_drift": _drift_report(recent, scorer),
        "model_performance": {
            "ground_truth_labels_available": False,
            "precision_recall_f1_available": False,
            "feedback_counts": dict(Counter(event.review_status for event in recent)),
            "note": "Reviewer feedback is stored for future evaluation and does not trigger automatic retraining.",
        },
    }
