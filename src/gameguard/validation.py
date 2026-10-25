"""Schema and range validation for telemetry datasets and API events."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
import pandas as pd

REQUIRED_SOURCE_COLUMNS = {
    "timestamp_ms",
    "power_usage_mw",
    "temperature_c",
    "graphics_clock_mhz",
    "memory_clock_mhz",
    "pcie_rx_kbps",
    "pcie_tx_kbps",
    "pstate",
    "throttle_reasons_bitmask",
    "fan_speed_perc",
    "memory_used_mb",
    "memory_total_mb",
    "encoder_util_perc",
    "decoder_util_perc",
    "cpu_tctl_c",
    "cpu_ccd1_c",
    "cpu_ccd2_c",
    "cpu_package_power_w",
    "session_label",
}

RANGES: dict[str, tuple[float, float]] = {
    "power_usage_mw": (0, 2_000_000),
    "temperature_c": (-20, 150),
    "graphics_clock_mhz": (0, 10_000),
    "memory_clock_mhz": (0, 20_000),
    "pcie_rx_kbps": (0, 20_000_000),
    "pcie_tx_kbps": (0, 20_000_000),
    "pstate": (0, 15),
    "throttle_reasons_bitmask": (0, 2**64 - 1),
    "fan_speed_perc": (0, 100),
    "memory_used_mb": (0, 1_000_000),
    "memory_total_mb": (1, 1_000_000),
    "encoder_util_perc": (0, 100),
    "decoder_util_perc": (0, 100),
    "cpu_tctl_c": (-20, 150),
    "cpu_ccd1_c": (-20, 150),
    "cpu_ccd2_c": (-20, 150),
    "cpu_package_power_w": (0, 1_000),
}


@dataclass
class ValidationReport:
    rows: int
    missing_values: dict[str, int]
    duplicate_timestamps: int
    out_of_range: dict[str, int]
    unexpected_columns: list[str]
    monotonic_timestamps: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def validate_frame(frame: pd.DataFrame, *, strict_columns: bool = True) -> ValidationReport:
    missing_columns = REQUIRED_SOURCE_COLUMNS - set(frame.columns)
    if missing_columns:
        raise ValueError(f"Missing required source columns: {sorted(missing_columns)}")
    unexpected = sorted(set(frame.columns) - REQUIRED_SOURCE_COLUMNS)
    if strict_columns and unexpected:
        raise ValueError(f"Unexpected source columns: {unexpected}")
    missing_values = {
        column: int(frame[column].isna().sum())
        for column in sorted(REQUIRED_SOURCE_COLUMNS)
        if int(frame[column].isna().sum())
    }
    numeric = frame.dropna(subset=["timestamp_ms"])
    times = pd.to_numeric(numeric["timestamp_ms"], errors="coerce")
    if times.isna().any() or (~np.isfinite(times.to_numpy(dtype=float))).any():
        raise ValueError("timestamp_ms contains a non-finite or malformed value")
    out_of_range: dict[str, int] = {}
    for column, (low, high) in RANGES.items():
        values = pd.to_numeric(frame[column], errors="coerce")
        invalid = values.notna() & ((values < low) | (values > high) | ~np.isfinite(values))
        if invalid.any():
            out_of_range[column] = int(invalid.sum())
    if out_of_range:
        raise ValueError(f"Out-of-range values: {out_of_range}")
    duplicate_count = int(numeric["timestamp_ms"].duplicated().sum())
    return ValidationReport(
        rows=len(frame),
        missing_values=missing_values,
        duplicate_timestamps=duplicate_count,
        out_of_range=out_of_range,
        unexpected_columns=unexpected,
        monotonic_timestamps=bool(times.is_monotonic_increasing),
    )
