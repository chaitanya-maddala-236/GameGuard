"""Strict, bounded request and response models for the telemetry API."""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class TelemetryInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: Annotated[str | None, Field(max_length=128)] = None
    timestamp_ms: Annotated[int, Field(gt=0, le=9_999_999_999_999)]
    session_label: Annotated[str, Field(max_length=120)] = "unknown"
    power_usage_mw: Annotated[float | None, Field(ge=0, le=2_000_000)] = None
    temperature_c: Annotated[float | None, Field(ge=-20, le=150)] = None
    graphics_clock_mhz: Annotated[float | None, Field(ge=0, le=10_000)] = None
    memory_clock_mhz: Annotated[float | None, Field(ge=0, le=20_000)] = None
    pcie_rx_kbps: Annotated[float | None, Field(ge=0, le=20_000_000)] = None
    pcie_tx_kbps: Annotated[float | None, Field(ge=0, le=20_000_000)] = None
    pstate: Annotated[int | None, Field(ge=0, le=15)] = None
    throttle_reasons_bitmask: Annotated[int | None, Field(ge=0, le=18_446_744_073_709_551_615)] = (
        None
    )
    fan_speed_perc: Annotated[float | None, Field(ge=0, le=100)] = None
    memory_used_mb: Annotated[float | None, Field(ge=0, le=1_000_000)] = None
    memory_total_mb: Annotated[float | None, Field(gt=0, le=1_000_000)] = None
    encoder_util_perc: Annotated[float | None, Field(ge=0, le=100)] = None
    decoder_util_perc: Annotated[float | None, Field(ge=0, le=100)] = None
    cpu_tctl_c: Annotated[float | None, Field(ge=-20, le=150)] = None
    cpu_ccd1_c: Annotated[float | None, Field(ge=-20, le=150)] = None
    cpu_ccd2_c: Annotated[float | None, Field(ge=-20, le=150)] = None
    cpu_package_power_w: Annotated[float | None, Field(ge=0, le=1_000)] = None


class BatchInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    events: Annotated[list[TelemetryInput], Field(min_length=1, max_length=200)]


class FeedbackInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Annotated[str, Field(pattern="^(likely_true_anomaly|false_positive|unresolved)$")]
    note: Annotated[str | None, Field(max_length=500)] = None
