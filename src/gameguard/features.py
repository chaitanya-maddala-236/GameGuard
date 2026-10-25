"""Map the verified source schema to stable numeric scoring features."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

FEATURE_NAMES = [
    "gpu_power_w",
    "gpu_temperature_c",
    "graphics_clock_mhz",
    "memory_clock_mhz",
    "pcie_rx_mbps",
    "pcie_tx_mbps",
    "pstate",
    "throttle_reason_count",
    "power_cap_active",
    "thermal_throttle_active",
    "hardware_slowdown_active",
    "fan_speed_perc",
    "memory_used_mb",
    "vram_used_perc",
    "encoder_util_perc",
    "decoder_util_perc",
    "cpu_tctl_c",
    "cpu_ccd1_c",
    "cpu_ccd2_c",
    "cpu_package_power_w",
]


def _value(row: dict[str, Any] | pd.Series, key: str) -> Any:
    value = row.get(key)
    return None if pd.isna(value) else value


def transform_row(row: dict[str, Any] | pd.Series) -> dict[str, float]:
    """Convert one source event, preserving nulls for model median-imputation."""
    mask_value = _value(row, "throttle_reasons_bitmask")
    try:
        mask = int(mask_value or 0)
    except (TypeError, ValueError, OverflowError):
        mask = 0
    used = _value(row, "memory_used_mb")
    total = _value(row, "memory_total_mb")
    vram_pct = np.nan if used is None or total in (None, 0) else 100.0 * float(used) / float(total)
    features = {
        "gpu_power_w": None
        if _value(row, "power_usage_mw") is None
        else float(row["power_usage_mw"]) / 1000,
        "gpu_temperature_c": _value(row, "temperature_c"),
        "graphics_clock_mhz": _value(row, "graphics_clock_mhz"),
        "memory_clock_mhz": _value(row, "memory_clock_mhz"),
        "pcie_rx_mbps": None
        if _value(row, "pcie_rx_kbps") is None
        else float(row["pcie_rx_kbps"]) / 1000,
        "pcie_tx_mbps": None
        if _value(row, "pcie_tx_kbps") is None
        else float(row["pcie_tx_kbps"]) / 1000,
        "pstate": _value(row, "pstate"),
        "throttle_reason_count": mask.bit_count(),
        "power_cap_active": int(bool(mask & 0x4)),
        "thermal_throttle_active": int(bool(mask & (0x20 | 0x40))),
        "hardware_slowdown_active": int(bool(mask & 0x80)),
        "fan_speed_perc": _value(row, "fan_speed_perc"),
        "memory_used_mb": used,
        "vram_used_perc": vram_pct,
        "encoder_util_perc": _value(row, "encoder_util_perc"),
        "decoder_util_perc": _value(row, "decoder_util_perc"),
        "cpu_tctl_c": _value(row, "cpu_tctl_c"),
        "cpu_ccd1_c": _value(row, "cpu_ccd1_c"),
        "cpu_ccd2_c": _value(row, "cpu_ccd2_c"),
        "cpu_package_power_w": _value(row, "cpu_package_power_w"),
    }
    return {name: np.nan if value is None else float(value) for name, value in features.items()}


def transform_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Transform a dataframe without using labels, absolute timestamps, or IDs."""
    rows = [transform_row(row) for row in frame.to_dict(orient="records")]
    return pd.DataFrame(rows, columns=FEATURE_NAMES, index=frame.index).astype(float)
