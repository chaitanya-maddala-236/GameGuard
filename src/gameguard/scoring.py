"""Load the trusted model artifact and score individual telemetry events."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from gameguard.features import transform_row


class ScoringService:
    def __init__(self, model_path: Path):
        artifact = joblib.load(model_path)
        self.estimator = artifact["estimator"]
        self.metadata = artifact["metadata"]
        self.threshold = float(self.metadata["threshold"])
        self.version = str(self.metadata["model_version"])
        reference = self.metadata["feature_reference"]
        self.medians = np.asarray(reference["medians"], dtype=float)
        self.scales = np.asarray(reference["scales"], dtype=float)
        self.feature_names = list(self.metadata["feature_names"])

    def score_event(self, event: dict[str, Any]) -> dict[str, Any]:
        started = time.perf_counter()
        features = transform_row(event)
        x = pd.DataFrame(
            [[features[name] for name in self.feature_names]], columns=self.feature_names
        )
        score = float(-self.estimator.decision_function(x)[0])
        expected_source = (
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
        )
        missing = [name for name in expected_source if event.get(name) is None]
        source_for_feature = {
            "gpu_power_w": "power_usage_mw",
            "gpu_temperature_c": "temperature_c",
            "graphics_clock_mhz": "graphics_clock_mhz",
            "memory_clock_mhz": "memory_clock_mhz",
            "pcie_rx_mbps": "pcie_rx_kbps",
            "pcie_tx_mbps": "pcie_tx_kbps",
            "pstate": "pstate",
            "throttle_reason_count": "throttle_reasons_bitmask",
            "power_cap_active": "throttle_reasons_bitmask",
            "thermal_throttle_active": "throttle_reasons_bitmask",
            "hardware_slowdown_active": "throttle_reasons_bitmask",
            "fan_speed_perc": "fan_speed_perc",
            "memory_used_mb": "memory_used_mb",
            "vram_used_perc": "memory_used_mb",
            "encoder_util_perc": "encoder_util_perc",
            "decoder_util_perc": "decoder_util_perc",
            "cpu_tctl_c": "cpu_tctl_c",
            "cpu_ccd1_c": "cpu_ccd1_c",
            "cpu_ccd2_c": "cpu_ccd2_c",
            "cpu_package_power_w": "cpu_package_power_w",
        }
        missing_model_features = {
            feature for feature, source in source_for_feature.items() if source in missing
        }
        if "memory_total_mb" in missing:
            missing_model_features.add("vram_used_perc")
        imputed_values = x.iloc[0].to_numpy(dtype=float)
        deviations = np.abs((imputed_values - self.medians) / self.scales)
        evidence = [
            {
                "feature": self.feature_names[i],
                "value": None
                if self.feature_names[i] in missing_model_features
                else float(imputed_values[i]),
                "robust_deviation": float(deviations[i]),
            }
            for i in np.argsort(deviations)[::-1][:5]
            if self.feature_names[i] not in missing_model_features
        ]
        latency_ms = (time.perf_counter() - started) * 1000
        return {
            "anomaly_score": score,
            "is_anomaly": score >= self.threshold,
            "threshold": self.threshold,
            "model_version": self.version,
            "timestamp_ms": int(event["timestamp_ms"]),
            "session_label": event.get("session_label", "unknown"),
            "quality_status": "missing_features" if missing else "valid",
            "missing_features": missing,
            "evidence": evidence,
            "latency_ms": latency_ms,
        }


def load_scorer(model_path: Path) -> ScoringService:
    if not model_path.is_file():
        raise FileNotFoundError(f"Model artifact is missing: {model_path}")
    return ScoringService(model_path)
