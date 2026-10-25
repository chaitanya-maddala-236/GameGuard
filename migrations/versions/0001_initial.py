"""Initial persisted telemetry and reviewer feedback schema."""

import sqlalchemy as sa
from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "telemetry_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_id", sa.String(length=64), nullable=False),
        sa.Column("timestamp_ms", sa.Integer(), nullable=False),
        sa.Column("session_label", sa.String(length=120), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("anomaly_score", sa.Float(), nullable=False),
        sa.Column("is_anomaly", sa.Boolean(), nullable=False),
        sa.Column("model_version", sa.String(length=80), nullable=False),
        sa.Column("quality_status", sa.String(length=40), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("latency_ms", sa.Float(), nullable=False),
        sa.Column(
            "review_status", sa.String(length=40), nullable=False, server_default="unresolved"
        ),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("event_id", name="uq_telemetry_events_event_id"),
    )
    op.create_index("ix_telemetry_events_timestamp_ms", "telemetry_events", ["timestamp_ms"])
    op.create_index("ix_telemetry_events_is_anomaly", "telemetry_events", ["is_anomaly"])
    op.create_index("ix_telemetry_events_model_version", "telemetry_events", ["model_version"])
    op.create_index("ix_telemetry_events_quality_status", "telemetry_events", ["quality_status"])
    op.create_index("ix_telemetry_events_review_status", "telemetry_events", ["review_status"])
    op.create_index("ix_telemetry_events_created_at", "telemetry_events", ["created_at"])


def downgrade() -> None:
    op.drop_table("telemetry_events")
