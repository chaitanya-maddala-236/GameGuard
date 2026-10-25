# Deployment status

Last checked: 2026-10-26.

## Verified in this workspace

- Python 3.11 and 3.13 are installed.
- Docker CLI is installed, but its Docker Desktop Linux Engine is not running, so Compose build/start cannot currently be executed here.
- Git identity is configured. The isolated `GameGuard` Git repository is initialized on `main`; GitHub remote/push is pending.
- GitHub authentication was verified for `@chaitanya-maddala-236` through the configured credential manager without printing credential material.
- No Render credentials or live service URLs have been verified. No cloud resource has been provisioned.
- `render.yaml` prepares a free-demo API, dashboard, and Postgres. Render documents free web services sleep after 15 idle minutes; free Postgres expires after 30 days. It must be upgraded before persistent use.
- Ruff format and lint pass. `pytest`: 6 passed. Alembic migration applied locally. Local API health/readiness, persistence/idempotency, metrics, Prometheus, and Streamlit health checks passed.
- A local synthetic load run of 80 requests at concurrency 5 completed with 80 successes, 0 errors, 5.97 requests/second, and p50/p95/p99 request latency of 529.616/2210.231/4163.597 ms. See `local-smoke-metrics.json`; alerts were generated from synthetic payloads and are not ground truth.

## Release checklist

- GitHub remote, commit, and CI run: pending.
- Render API/dashboard/database: not provisioned.
- Production health/readiness, event persistence, feedback, dashboard smoke: pending because no Render service exists.
- Verified URLs: none.
- Remaining deployment action if no Render account connection is available: connect the GitHub repository as a Render Blueprint and apply the proposed API, dashboard, and database resources; then upgrade the free database/service for persistent use.
