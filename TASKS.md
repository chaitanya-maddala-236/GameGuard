# GameGuard build checklist

- [x] Inspect workspace, existing starter, runtime, Git configuration, Docker availability, and candidate data source.
- [x] Verify the candidate's current schema, license, provenance, limitations, and download availability.
- [x] Record project plan, assumptions, and implementation decisions.
- [x] Implement reproducible data validation and feature engineering.
- [x] Train and compare unsupervised detectors using temporal splits; save measured evaluation and model metadata.
- [x] Implement validated FastAPI ingestion/scoring, persistence, idempotency, feedback, health, and monitoring metrics.
- [x] Implement Streamlit dashboard against the live API.
- [x] Add synthetic anomaly-injection checks without treating injections as real labels.
- [x] Add API, database, and model tests; run lint and tests; smoke-check the dashboard and fix failures.
- [x] Add Docker Compose, health checks, GitHub Actions, Render Blueprint, and deployment/runbook docs.
- [x] Verify local API/dashboard startup, persistence, and monitoring; record Docker Engine unavailability honestly.
- [ ] Publish the repository to GitHub and deploy if account credentials and hosting authorization are available.
- [ ] Record final measured metrics, tested flows, URLs, known limitations, and any single external action still needed.
