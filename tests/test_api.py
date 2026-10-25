from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from gameguard import api as api_module
from gameguard.api import app, scorer, session_dependency
from gameguard.db import Base


class StubScorer:
    version = "stub-v1"
    threshold = 0.5
    metadata = {"model_version": version, "threshold": threshold, "feature_names": []}

    def score_event(self, payload):
        return {
            "timestamp_ms": payload["timestamp_ms"],
            "session_label": payload.get("session_label", "unknown"),
            "anomaly_score": 0.9,
            "is_anomaly": True,
            "threshold": self.threshold,
            "model_version": self.version,
            "quality_status": "missing_features",
            "missing_features": ["temperature_c"],
            "evidence": [{"feature": "gpu_temperature_c", "value": None, "robust_deviation": 0.0}],
            "latency_ms": 0.1,
        }


def test_event_idempotency_feedback_and_metrics(monkeypatch):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)

    def test_session() -> Iterator[Session]:
        with Session(engine) as session:
            yield session

    app.dependency_overrides[session_dependency] = test_session
    app.dependency_overrides[scorer] = lambda: StubScorer()
    monkeypatch.setattr(
        api_module,
        "settings",
        SimpleNamespace(
            api_key="test-key", model_path=Path("artifacts/models/gameguard-if-v1/model.joblib")
        ),
    )
    payload = {
        "timestamp_ms": 1_700_000_000_000,
        "session_label": "api-fixture",
        "event_id": "retry-1",
    }
    try:
        with TestClient(app) as client:
            assert client.get("/health").status_code == 200
            assert client.post("/v1/events", json=payload).status_code == 401
            headers = {"X-API-Key": "test-key"}
            first = client.post("/v1/events", json=payload, headers=headers)
            second = client.post("/v1/events", json=payload, headers=headers)
            assert first.status_code == 200
            assert first.json()["duplicate"] is False
            assert second.json()["duplicate"] is True
            identifier = first.json()["event_id"]
            alerts = client.get("/v1/alerts", headers=headers).json()
            assert alerts["total"] == 1
            feedback = client.patch(
                f"/v1/alerts/{identifier}/feedback",
                headers=headers,
                json={"status": "false_positive", "note": "Reviewed fixture"},
            )
            assert feedback.status_code == 200
            assert feedback.json()["review_status"] == "false_positive"
            summary = client.get("/v1/metrics/summary", headers=headers).json()
            assert summary["events_total"] == 1
            assert summary["alerts_total"] == 1
            prometheus = client.get("/metrics", headers=headers)
            assert prometheus.status_code == 200
            assert "gameguard_events_total 1" in prometheus.text
            assert "gameguard_ingestion_throughput_events_per_second_last_minute" in prometheus.text
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_request_schema_rejects_ranges_and_extra_fields(monkeypatch):
    app.dependency_overrides[scorer] = lambda: StubScorer()
    monkeypatch.setattr(
        api_module,
        "settings",
        SimpleNamespace(
            api_key="", model_path=Path("artifacts/models/gameguard-if-v1/model.joblib")
        ),
    )
    try:
        with TestClient(app) as client:
            invalid_range = client.post(
                "/v1/score", json={"timestamp_ms": 1_700_000_000_000, "fan_speed_perc": 120}
            )
            extra = client.post(
                "/v1/score",
                json={"timestamp_ms": 1_700_000_000_000, "player_email": "x@example.test"},
            )
            assert invalid_range.status_code == 422
            assert extra.status_code == 422
    finally:
        app.dependency_overrides.clear()
