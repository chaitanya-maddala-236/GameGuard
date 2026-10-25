# GameGuard project plan

## Objective

Deliver an end-to-end, local-first service that scores GPU/CPU game-session hardware telemetry for unusual operating conditions. Scores are investigation signals and do not establish cheating, fraud, hardware failure, or intent.

## Verified facts

- The source dataset `rmems/gaming-telemetry` is available on Hugging Face and has a Parquet split of 95,893 rows (about 2.61 MB), describing one 90-minute Resident Evil 4 Remake capture on one RTX 5080 workstation.
- The dataset card declares dual MIT / Apache-2.0 licensing, identifies a Rust NVML + hwmon/RAPL collector, and describes 19 columns including millisecond timestamps and hardware readings.
- `session_label` is constant (`re4`). There are no anomaly labels; the card says this capture has no thermal or hardware-slowdown events and only power-cap throttle samples. The project therefore uses unsupervised detection and does not claim real-world precision/recall.
- Python 3.11 and 3.13 are installed. Docker CLI exists, but the Docker Engine is not running. No GitHub remote is configured.
- Deployment credentials and a live provider configuration have not been verified. No cloud services have been provisioned.

## Assumptions and open items

- Use a dedicated `GameGuard/` repository in the workspace; sibling projects are unrelated.
- Use the named, documented Hugging Face corpus for measured model training and keep raw Parquet out of Git.
- Use SQLite for zero-setup local use, SQLAlchemy-compatible PostgreSQL for deployment, FastAPI for ingestion and scoring, and Streamlit/Plotly for the dashboard.
- Use Render Blueprint as the prepared deployment path. A cloud deployment still requires account access, a connected GitHub repository, and a persistent database/service choice; free Postgres expires after 30 days.
- Create a private GitHub repository if existing authentication permits; no visibility was specified, so private is the conservative default.

## Phases

1. **Inspect and plan:** inspect the workspace, dataset source, runtime, Git and deployment access. *(Complete.)*
2. **Data and model:** validate and document the source; engineer supported features; compare robust statistical, Isolation Forest, and Local Outlier Factor detectors with chronological splits; select threshold by an explicit validation alert budget; save measured reports and the model.
3. **Service:** implement event validation, scoring, idempotent persistence, review feedback, health/readiness, metrics, and monitoring.
4. **Dashboard:** provide a responsive API-backed control-room interface with usable empty/error states and honest model/data descriptions.
5. **Delivery:** add tests, CI, Docker Compose, a Render blueprint, deployment/runbook docs, and verify every available local path. Publish and deploy only where connected credentials and hosting access permit.
