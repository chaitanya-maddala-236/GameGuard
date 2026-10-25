"""Measure observed API latency and throughput using clearly synthetic requests."""

from __future__ import annotations

import argparse
import os
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=os.getenv("API_BASE_URL", "http://localhost:8000"))
    parser.add_argument("--requests", type=int, default=100)
    parser.add_argument("--concurrency", type=int, default=5)
    args = parser.parse_args()
    if args.requests < 1 or args.concurrency < 1:
        parser.error("--requests and --concurrency must be positive")
    headers = {"X-API-Key": os.getenv("API_KEY", "")}
    latencies: list[float] = []
    errors: list[str] = []

    def send(index: int):
        payload = {
            "event_id": f"synthetic-load-test-{time.time_ns()}-{index}",
            "timestamp_ms": 1_800_000_000_000 + index,
            "session_label": "synthetic-load-test",
            "power_usage_mw": 255_000 + (index % 9) * 1000,
            "temperature_c": 60 + index % 7,
            "graphics_clock_mhz": 2_600,
            "memory_clock_mhz": 14_000,
            "pcie_rx_kbps": 12_000 + (index * 73) % 2_000,
            "pcie_tx_kbps": 9_000 + (index * 53) % 1_000,
            "pstate": index % 3,
            "throttle_reasons_bitmask": 0,
            "fan_speed_perc": 75,
            "memory_used_mb": 12_500,
            "memory_total_mb": 16_000,
            "encoder_util_perc": 0,
            "decoder_util_perc": 0,
            "cpu_tctl_c": 74.0,
            "cpu_ccd1_c": 66.0,
            "cpu_ccd2_c": 61.0,
            "cpu_package_power_w": 145.0,
        }
        started = time.perf_counter()
        try:
            response = requests.post(
                f"{args.url.rstrip('/')}/v1/events", headers=headers, json=payload, timeout=10
            )
            response.raise_for_status()
            return (time.perf_counter() - started) * 1000, None
        except requests.RequestException as exc:
            return (time.perf_counter() - started) * 1000, str(exc)

    wall_started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        futures = [pool.submit(send, index) for index in range(args.requests)]
        for future in as_completed(futures):
            elapsed, error = future.result()
            latencies.append(elapsed)
            if error:
                errors.append(error)
    wall_seconds = time.perf_counter() - wall_started
    ordered = sorted(latencies)

    def percentile(value: float) -> float:
        return ordered[min(len(ordered) - 1, int((len(ordered) - 1) * value))]

    print(
        {
            "request_source": "synthetic_load_test",
            "requests": args.requests,
            "concurrency": args.concurrency,
            "successful": len(latencies) - len(errors),
            "errors": len(errors),
            "wall_seconds": round(wall_seconds, 3),
            "throughput_events_per_second": round((len(latencies) - len(errors)) / wall_seconds, 2),
            "latency_ms_p50": round(statistics.median(latencies), 3),
            "latency_ms_p95": round(percentile(0.95), 3),
            "latency_ms_p99": round(percentile(0.99), 3),
            "first_error": errors[0] if errors else None,
        }
    )


if __name__ == "__main__":
    main()
