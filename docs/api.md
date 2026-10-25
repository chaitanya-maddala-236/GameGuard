# API reference

FastAPI publishes OpenAPI at `/docs`. When `API_KEY` is set, all `/v1/*` and `/metrics` routes require `X-API-Key`. `/health`, `/ready`, and `/docs` remain accessible for health checks and inspection. Rate limiting is process-local at 120 `/v1/*` requests per client address per minute.

| Method | Endpoint | Description |
| --- | --- | --- |
| GET | `/health` | Process liveness |
| GET | `/ready` | Model and database readiness |
| GET | `/v1/model/info` | Model version, threshold rule, schema, and limitations |
| POST | `/v1/score` | Score without persistence |
| POST | `/v1/events` | Score and idempotently persist one event |
| POST | `/v1/events/batch` | Score 1–200 events per request |
| GET | `/v1/events` | Paginated event history; filter by `flagged` or `min_score` |
| GET | `/v1/alerts` | Paginated flagged event list; filter by reviewer `status` |
| PATCH | `/v1/alerts/{event_id}/feedback` | Set `likely_true_anomaly`, `false_positive`, or `unresolved`, with optional note |
| GET | `/v1/metrics/summary` | Persisted throughput, alert rate, score distribution, quality, feedback, and latency |
| GET | `/v1/monitoring` | Operational summary and recent-feature PSI |
| GET | `/metrics` | Minimal Prometheus text metrics |

The input follows the 19-column source schema; `timestamp_ms` is required and sensor fields may be null. Extra fields are rejected. Batch event IDs are generated from canonical event content when omitted; callers can supply stable `event_id` values for retry-safe idempotency. Responses include an anomaly score, threshold, flag, model version, quality status, timing, and top feature deviations. The score is not a probability.

Example:

```powershell
$headers = @{ 'Content-Type' = 'application/json' }
if ($env:API_KEY) { $headers['X-API-Key'] = $env:API_KEY }
Invoke-RestMethod -Method Post -Uri http://localhost:8000/v1/score -Headers $headers -Body '{"timestamp_ms":1775992159648,"session_label":"re4","power_usage_mw":260546,"temperature_c":60,"graphics_clock_mhz":2805,"memory_clock_mhz":15001,"pcie_rx_kbps":1053938,"pcie_tx_kbps":104576,"pstate":0,"throttle_reasons_bitmask":0,"fan_speed_perc":74,"memory_used_mb":13427,"memory_total_mb":16303,"encoder_util_perc":0,"decoder_util_perc":0,"cpu_tctl_c":77.125,"cpu_ccd1_c":67.875,"cpu_ccd2_c":48.625,"cpu_package_power_w":152.898438}'
```

The example values illustrate the source format; use the exact schema for production events and never paste sensitive information into logs or public issues.
