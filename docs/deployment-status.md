# Deployment status

Last checked: 2026-10-26.

## Verified in this workspace

- Python 3.11 and 3.13 are installed.
- Docker CLI is installed, but its Docker Desktop Linux Engine is not running, so Compose build/start cannot currently be executed here.
- Git identity is configured. The isolated project is published as the private repository [chaitanya-maddala-236/GameGuard](https://github.com/chaitanya-maddala-236/GameGuard), branch `main`, initial source commit `d86e0c9`.
- GitHub Actions run [40226680721](https://github.com/chaitanya-maddala-236/GameGuard/actions/runs/40226680721) completed successfully, including Ruff format/lint, pytest, and `docker build` on GitHub's runner.
- GitHub authentication was verified for `@chaitanya-maddala-236` through the configured credential manager without printing credential material.
- No Render credentials or live service URLs have been verified. No cloud resource has been provisioned.
- `render.yaml` prepares a free-demo API, dashboard, and Postgres. Render documents free web services sleep after 15 idle minutes; free Postgres expires after 30 days. It must be upgraded before persistent use.
- Ruff format and lint pass. `pytest`: 6 passed. Alembic migration applied locally. Local API health/readiness, persistence/idempotency, metrics, Prometheus, and Streamlit health checks passed.
- A local synthetic load run of 80 requests at concurrency 5 completed with 80 successes, 0 errors, 5.97 requests/second, and p50/p95/p99 request latency of 529.616/2210.231/4163.597 ms. See `local-smoke-metrics.json`; alerts were generated from synthetic payloads and are not ground truth.

## Release checklist

- GitHub private repository, `main` branch, and CI Docker build: verified.
- Render API/dashboard/database: not provisioned.
- Production health/readiness, event persistence, feedback, dashboard smoke: pending because no Render service exists.
- Verified URLs: GitHub repository and passing Actions run above. No deployed app URLs exist.
- Remaining deployment action: connect the private GitHub repository to a Render account and apply the Blueprint's API, dashboard, and database resources. The Blueprint uses free demo plans; upgrade the database and web services before relying on persistent telemetry.
