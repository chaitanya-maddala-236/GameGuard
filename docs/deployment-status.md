# Deployment status and metrics

Checked 2026-10-26 (Asia/Kolkata). This is a free demo deployment.

## GitHub and CI

- Public repository: [chaitanya-maddala-236/GameGuard](https://github.com/chaitanya-maddala-236/GameGuard), `main` branch.
- Latest verified application revision: `4947d71` (`Format deployment CORS configuration`).
- CI for that revision: [GitHub Actions run 40228979779](https://github.com/chaitanya-maddala-236/GameGuard/actions/runs/40228979779) succeeded. It runs Ruff format/lint, pytest, and a Docker image build.

## Live services

| Component | URL | Provider state |
| --- | --- | --- |
| Dashboard | [gameguard-dashboard-x69x.onrender.com](https://gameguard-dashboard-x69x.onrender.com/) | Render Free web service, live and auto-deployed from `main` |
| API | [gameguard-api-x69x.onrender.com](https://gameguard-api-x69x.onrender.com/) | Render Free web service, live and auto-deployed from `main` |
| API readiness | [`/ready`](https://gameguard-api-x69x.onrender.com/ready) | `ready`, model `gameguard-if-v1`, database `connected` |
| API health | [`/health`](https://gameguard-api-x69x.onrender.com/health) | Liveness endpoint |

Both services belong to the `gameguard-neon` Render Blueprint. They use public HTTPS service URLs because Render's free web-service plan does not support private service networking. Render may spin down free services after inactivity; the first request can take 50 seconds or longer.

## Database

- A dedicated Neon project named `gameguard` is connected to the Render API; it is separate from other Neon projects.
- The API uses the pooled Neon connection for database `neondb`. `/ready` confirmed the database connection after the latest API deploy.
- The connection string is stored as Render's `DATABASE_URL` secret. It is not stored in this repository.
- The observed Neon plan is Free. Free-tier limits can change; this deployment is not configured as a production data store.

## Live operational metrics

No telemetry has been submitted to the live service. The live database is empty, so the dashboard correctly reports:

| Metric | Live value |
| --- | ---: |
| Events processed | 0 |
| Alerts in the last 24 hours | 0 |
| Alert rate in the last 24 hours | 0.00% |
| Live score latency p95 | Not available (no scored events) |

These empty values are distinct from the offline model evaluation and local synthetic-load results below.

## Offline model evaluation

The evaluation uses the single-session `rmems/gaming-telemetry` RE4 dataset. It has no trusted anomaly labels, so these alert rates are descriptive, not precision, recall, or accuracy.

| Detector | Validation alert rate (14,384 rows) | Later-time test alert rate (14,384 rows) | Test alert-rate range across five time blocks |
| --- | ---: | ---: | ---: |
| Isolation Forest (primary) | 1.001% | 5.026% | 18.67 percentage points |
| Robust statistical thresholds | 1.168% | 3.824% | 19.05 percentage points |
| Local Outlier Factor | 1.001% | 1.550% | 7.72 percentage points |

The Isolation Forest threshold was chosen to target a 1% alert budget on chronological validation data; the higher test rate and time-block variation show why this must be evaluated on representative labeled data before operational use. Training plus evaluation took 12.37 seconds on the training machine. See the full [model metrics JSON](../artifacts/models/gameguard-if-v1/metrics.json) and [model card](model-card.md).

## Local synthetic load and smoke metrics

One local loopback run used SQLite and 80 synthetic requests to `POST /v1/events`, at concurrency 5. All 80 succeeded, with 0 errors, 5.97 requests/second, and request-latency p50/p95/p99 of 529.616/2,210.231/4,163.597 ms. Model-scoring latency p95 in that run was 272.769 ms. This is one local run, not a cloud benchmark or production-capacity estimate. Alerts came from synthetic payloads with no ground truth. See [local smoke metrics](local-smoke-metrics.json).

## Known limits

- The dataset has no verified anomaly labels, covers one roughly 90-minute game session and one RTX 5080 machine, and cannot establish performance on other games or hardware.
- Render services use the Free plan and can sleep after inactivity. Neon is on its Free plan. Check current provider limits before relying on this setup.
- No live telemetry, event-persistence, or reviewer-feedback write-path check has been run against the deployed database. These metrics remain zero until an explicitly approved event is ingested.
- Do not use these scores as proof of cheating or as the sole basis for player penalties.
