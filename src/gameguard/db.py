"""SQLAlchemy persistence shared by local SQLite and PostgreSQL deployments."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from gameguard.config import settings


def _database_url(url: str) -> str:
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    if url.startswith("postgresql://") and "+psycopg" not in url:
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


engine_options = {"pool_pre_ping": True}
if _database_url(settings.database_url).startswith("sqlite"):
    engine_options["connect_args"] = {"check_same_thread": False}
engine = create_engine(_database_url(settings.database_url), **engine_options)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class TelemetryEvent(Base):
    __tablename__ = "telemetry_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[str] = mapped_column(String(64), unique=True)
    timestamp_ms: Mapped[int] = mapped_column(Integer, index=True)
    session_label: Mapped[str] = mapped_column(String(120), default="unknown")
    payload: Mapped[dict] = mapped_column(JSON)
    anomaly_score: Mapped[float] = mapped_column(Float)
    is_anomaly: Mapped[bool] = mapped_column(Boolean, index=True)
    model_version: Mapped[str] = mapped_column(String(80), index=True)
    quality_status: Mapped[str] = mapped_column(String(40), index=True)
    evidence: Mapped[list] = mapped_column(JSON)
    latency_ms: Mapped[float] = mapped_column(Float)
    review_status: Mapped[str] = mapped_column(String(40), default="unresolved", index=True)
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True
    )


def get_session():
    with SessionLocal() as session:
        yield session
