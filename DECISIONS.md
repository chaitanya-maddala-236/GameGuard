# GameGuard decisions

| Date | Decision | Reason |
| --- | --- | --- |
| 2026-10-26 | Create a dedicated GameGuard repository alongside the existing work. | The requested deliverable is the telemetry anomaly system; a separate retention project already occupies the PlayerPulse name. |
| 2026-10-26 | Use `rmems/gaming-telemetry` as the real measured corpus. | Verified current files, schema, provenance, dual license, size, and limitations. It contains hardware counters recorded during gameplay, not player actions. |
| 2026-10-26 | Model only hardware/session telemetry deviations. | This dataset cannot support player behavior or anti-cheat claims. |
| 2026-10-26 | Use chronological train/validation/test splits and no supervised classification metrics. | All rows are one continuous session and have no verified anomaly labels. |
| 2026-10-26 | Select an anomaly threshold by a 1% validation alert budget and report observed test alert volume. | Makes the tradeoff operational and avoids pretending the threshold optimizes precision or recall. |
| 2026-10-26 | Use SQLite locally and PostgreSQL when deployed. | Zero-service developer setup with persistent production database support. |
| 2026-10-26 | Prepare Render as the deployment blueprint. | It supports Docker, managed Postgres, and health checks; current free plans sleep and free Postgres expires after 30 days, so persistent use needs a paid plan. |
| 2026-10-26 | Keep a newly created GitHub repository private by default. | The user requested GitHub hosting but did not specify public visibility. |
