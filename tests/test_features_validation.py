import pytest

from gameguard.features import transform_row
from gameguard.validation import validate_frame


def test_feature_conversions_and_bitmask():
    features = transform_row(
        {
            "power_usage_mw": 260_000,
            "temperature_c": 60,
            "graphics_clock_mhz": 2_800,
            "memory_clock_mhz": 14_000,
            "pcie_rx_kbps": 4_500,
            "pcie_tx_kbps": 2_500,
            "pstate": 0,
            "throttle_reasons_bitmask": 0x44,
            "fan_speed_perc": 75,
            "memory_used_mb": 8_000,
            "memory_total_mb": 16_000,
        }
    )
    assert features["gpu_power_w"] == 260
    assert features["pcie_rx_mbps"] == 4.5
    assert features["vram_used_perc"] == 50
    assert features["throttle_reason_count"] == 2
    assert features["power_cap_active"] == 1
    assert features["thermal_throttle_active"] == 1


def test_schema_quality_reports_missing_and_duplicates(telemetry_frame):
    telemetry_frame.loc[0, "temperature_c"] = None
    telemetry_frame.loc[1, "timestamp_ms"] = telemetry_frame.loc[0, "timestamp_ms"]
    report = validate_frame(telemetry_frame)
    assert report.missing_values["temperature_c"] == 1
    assert report.duplicate_timestamps == 1


def test_schema_and_range_violations_are_rejected(telemetry_frame):
    with pytest.raises(ValueError, match="Missing required"):
        validate_frame(telemetry_frame.drop(columns=["pstate"]))
    telemetry_frame.loc[0, "fan_speed_perc"] = 120
    with pytest.raises(ValueError, match="Out-of-range"):
        validate_frame(telemetry_frame)
