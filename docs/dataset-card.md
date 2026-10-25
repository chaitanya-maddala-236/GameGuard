# Dataset card: `rmems/gaming-telemetry`

## Source and rights

- Dataset: [Hugging Face `rmems/gaming-telemetry`](https://huggingface.co/datasets/rmems/gaming-telemetry), configuration `re4`, split `train`.
- File: `re4/train-00000.parquet`; public download URL used by `scripts/download_data.py`.
- License declared on the dataset page: dual licensed MIT or Apache-2.0. See the dataset card for attribution and the original collector/provenance.
- Downloaded file size observed in this workspace: 2,607,671 bytes. Training records its SHA-256 in `artifacts/models/gameguard-if-v1/model-info.json` and `metrics.json`.
- Provenance as described by the dataset card: Rust collector, NVIDIA NVML plus Linux hwmon/RAPL, gathered during a Resident Evil 4 Remake session at maximum settings; source card says 48 raw Parquet batches were concatenated and sorted by timestamp. Raw data are excluded from Git.

## Suitability and limitations

The current split has 95,893 rows over about 90.1 minutes at a mean observed cadence of about 56.4 ms. It is one capture session, one RTX 5080 workstation, and a single game title. The source card reports no thermal or hardware-slowdown throttle events; the only nonzero throttle bitmask is the software power-cap bit. There are no anomaly labels or known incident examples.

It is genuine hardware telemetry collected during gameplay, but it does not describe player actions, gameplay outcomes, or cheating. It is useful for exercising a near-real-time hardware-telemetry anomaly pipeline. It cannot establish cross-game, cross-hardware, or real-world anomaly performance. Null readings are missing, not zero.

## Source schema and data dictionary

| Source column | Type | Meaning / unit |
| --- | --- | --- |
| `timestamp_ms` | int64 | Unix wall-clock timestamp in milliseconds |
| `power_usage_mw` | uint32 | GPU board power in milliwatts |
| `temperature_c` | uint32 | GPU core temperature in Celsius |
| `graphics_clock_mhz` | uint32 | GPU graphics clock in MHz |
| `memory_clock_mhz` | uint32 | GPU memory clock in MHz |
| `pcie_rx_kbps` | uint32 | PCIe receive rate in kilobits per second |
| `pcie_tx_kbps` | uint32 | PCIe transmit rate in kilobits per second |
| `pstate` | uint32 | NVML performance state, P0 = 0 |
| `throttle_reasons_bitmask` | uint64 | NVML clock-throttle reason bitmask; selected bits are decoded for power cap and thermal/hardware slowdown signals |
| `fan_speed_perc` | uint32 | GPU fan duty in percent |
| `memory_used_mb` | uint64 | GPU memory used in MB |
| `memory_total_mb` | uint64 | GPU memory capacity in MB |
| `encoder_util_perc` | uint32 | NVENC utilization in percent |
| `decoder_util_perc` | uint32 | NVDEC utilization in percent |
| `cpu_tctl_c` | float32 | CPU control temperature in Celsius |
| `cpu_ccd1_c` | float32 | CPU CCD 1 temperature in Celsius |
| `cpu_ccd2_c` | float32 | CPU CCD 2 temperature in Celsius |
| `cpu_package_power_w` | float32 | CPU package power in watts |
| `session_label` | string | Session configuration label, constant `re4` in this split |

## Validation and derived features

Training validates required columns, finite timestamps, duplicates, source reading ranges, and chronological order. Optional numeric sensor readings can be null; the scoring pipeline median-imputes them and records a data-quality status. Schema changes and invalid ranges fail the training/ingestion path.

The model uses 20 features derived only from the documented readings: GPU power in watts (source milliwatts converted to watts), GPU temperature, graphics and memory clocks, PCIe RX/TX in MB/s, P-state, number of active throttle bits, explicit power-cap/thermal/hardware-slowdown bit flags, fan duty, memory used, VRAM percent, encoder/decoder utilization, three CPU temperatures, and CPU package power. Absolute timestamp and session label are excluded from model features.

## Reproduction

```powershell
python scripts/download_data.py
python -m gameguard.train --data data/raw/re4/train-00000.parquet --output-dir artifacts/models/gameguard-if-v1
```

The deterministic training seed is stored in model metadata. Raw Parquet stays under the ignored `data/raw/` directory and is not distributed by this repository.
