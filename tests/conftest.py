from __future__ import annotations

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def telemetry_frame():
    rng = np.random.default_rng(42)
    rows = []
    for i in range(240):
        rows.append(
            {
                "timestamp_ms": 1_700_000_000_000 + i * 56,
                "power_usage_mw": int(250_000 + rng.normal(0, 20_000)),
                "temperature_c": int(58 + rng.normal(0, 2)),
                "graphics_clock_mhz": int(2_700 + rng.normal(0, 80)),
                "memory_clock_mhz": int(14_000 + rng.normal(0, 50)),
                "pcie_rx_kbps": int(20_000 + rng.lognormal(8, 1)),
                "pcie_tx_kbps": int(15_000 + rng.lognormal(7.5, 1)),
                "pstate": int(i % 3),
                "throttle_reasons_bitmask": int(4 if i % 11 == 0 else 0),
                "fan_speed_perc": int(72 + rng.normal(0, 2)),
                "memory_used_mb": int(12_000 + rng.normal(0, 400)),
                "memory_total_mb": 16_000,
                "encoder_util_perc": int(i % 2),
                "decoder_util_perc": 0,
                "cpu_tctl_c": float(70 + rng.normal(0, 3)),
                "cpu_ccd1_c": float(65 + rng.normal(0, 3)),
                "cpu_ccd2_c": float(60 + rng.normal(0, 3)),
                "cpu_package_power_w": float(140 + rng.normal(0, 15)),
                "session_label": "fixture",
            }
        )
    return pd.DataFrame(rows)
