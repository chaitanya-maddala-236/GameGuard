"""Replay the public telemetry Parquet into a running GameGuard API."""

from __future__ import annotations

import argparse
import os
import time
from pathlib import Path

import pandas as pd
import requests

SOURCE_FIELDS = {
    "timestamp_ms",
    "session_label",
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
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path("data/raw/re4/train-00000.parquet"))
    parser.add_argument("--url", default=os.getenv("API_BASE_URL", "http://localhost:8000"))
    parser.add_argument("--rate", type=float, default=10, help="Events per second")
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()
    if args.rate <= 0 or args.limit < 1:
        parser.error("--rate must be positive and --limit must be at least one")
    frame = pd.read_parquet(args.data).head(args.limit)
    headers = {"X-API-Key": os.getenv("API_KEY", "")}
    delay = 1 / args.rate
    for row in frame.to_dict(orient="records"):
        payload = {
            key: None if pd.isna(value) else value.item() if hasattr(value, "item") else value
            for key, value in row.items()
            if key in SOURCE_FIELDS
        }
        response = requests.post(
            f"{args.url.rstrip('/')}/v1/events", headers=headers, json=payload, timeout=10
        )
        response.raise_for_status()
        result = response.json()
        print(
            f"{result['timestamp_ms']} score={result['anomaly_score']:.5f} flagged={result['is_anomaly']}"
        )
        time.sleep(delay)


if __name__ == "__main__":
    main()
