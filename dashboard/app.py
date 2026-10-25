"""Responsive Streamlit dashboard; all operational cards read from the API."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")
if not API_BASE.startswith(("http://", "https://")):
    API_BASE = f"https://{API_BASE}"
API_KEY = os.getenv("API_KEY", "")
HEADERS = {"X-API-Key": API_KEY} if API_KEY else {}
SOURCE_FIELDS = {
    "event_id",
    "timestamp_ms",
    "session_label",
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
}

st.set_page_config(page_title="GameGuard | Telemetry Operations", page_icon="🎮", layout="wide")
st.markdown(
    """<style>
    .stApp { background: #07111f; color: #e6edf5; }
    [data-testid="stSidebar"] { background: #0b1728; border-right: 1px solid #1d3146; }
    [data-testid="stMetric"] { background: #101f31; border: 1px solid #22364b; border-radius: 12px; padding: 14px 16px; }
    .gg-subtle { color: #9bb0c4; font-size: .92rem; }
    .gg-title { color: #f1f6fa; letter-spacing: -.03em; }
    div[data-testid="stAlert"] { border-radius: 10px; }
    </style>""",
    unsafe_allow_html=True,
)


def api(method: str, path: str, **kwargs):
    return requests.request(method, f"{API_BASE}{path}", headers=HEADERS, timeout=10, **kwargs)


def fetch(path: str, default=None):
    try:
        response = api("GET", path)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        st.error(f"API request failed: {exc}")
        return default


def load_events(*, flagged=None):
    query = "?page_size=200"
    if flagged is not None:
        query += f"&flagged={str(flagged).lower()}"
    result = fetch(f"/v1/events{query}", {"items": [], "total": 0})
    return result.get("items", []) if result else []


def timestamp_frame(rows):
    frame = pd.DataFrame(rows)
    if len(frame) and "timestamp_ms" in frame:
        frame["timestamp"] = pd.to_datetime(frame["timestamp_ms"], unit="ms", utc=True)
    return frame


def clean_records(frame: pd.DataFrame) -> list[dict]:
    records = []
    for row in frame.to_dict(orient="records"):
        clean = {}
        for key, value in row.items():
            if key not in SOURCE_FIELDS or pd.isna(value):
                continue
            clean[key] = value.item() if hasattr(value, "item") else value
        records.append(clean)
    return records


st.sidebar.markdown("# 🎮 GameGuard")
st.sidebar.caption("Game-session telemetry operations")
page = st.sidebar.radio(
    "Navigation",
    [
        "Overview",
        "Live Telemetry",
        "Anomaly Explorer",
        "Model Performance",
        "Data Quality",
        "Monitoring",
        "Model & Dataset",
    ],
)
health = fetch("/ready", {})
if health and health.get("status") == "ready":
    st.sidebar.success(f"API ready · {health.get('model_version', 'unknown model')}")
else:
    st.sidebar.warning("API is not ready")
st.sidebar.markdown(
    "<p class='gg-subtle'>Flags identify unusual measurements for review. They do not establish cheating or intent.</p>",
    unsafe_allow_html=True,
)


if page == "Overview":
    st.markdown("<h1 class='gg-title'>Telemetry overview</h1>", unsafe_allow_html=True)
    summary = fetch("/v1/metrics/summary", {})
    if summary:
        cols = st.columns(5)
        cols[0].metric("Events processed", f"{summary.get('events_total', 0):,}")
        cols[1].metric("Alerts · 24h", f"{summary.get('alerts_last_24h', 0):,}")
        cols[2].metric("Alert rate · 24h", f"{summary.get('alert_rate_last_24h', 0):.2%}")
        latency = summary.get("p95_scoring_latency_ms_last_24h")
        cols[3].metric("Score latency p95", "—" if latency is None else f"{latency:.2f} ms")
        cols[4].metric("Model", summary.get("model_version", "—"))
    rows = load_events()
    frame = timestamp_frame(rows)
    if frame.empty:
        st.info("No telemetry has been scored yet. Upload a dataset in Live Telemetry to begin.")
    else:
        a, b = st.columns([1.65, 1])
        with a:
            st.subheader("Recent anomaly scores")
            chart = px.scatter(
                frame.sort_values("timestamp"),
                x="timestamp",
                y="anomaly_score",
                color="is_anomaly",
                hover_data=["session_label", "model_version"],
                color_discrete_map={True: "#42d3c2", False: "#6f89a5"},
            )
            chart.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                yaxis_title="Anomaly score · not probability",
            )
            st.plotly_chart(chart, use_container_width=True)
        with b:
            st.subheader("Recent events")
            st.dataframe(
                frame[
                    ["timestamp", "anomaly_score", "is_anomaly", "quality_status", "review_status"]
                ].head(20),
                use_container_width=True,
                hide_index=True,
            )

elif page == "Live Telemetry":
    st.title("Live Telemetry")
    st.caption(
        "Replay source data or ingest telemetry exported from a compatible collector. No live game integration is included."
    )
    uploaded = st.file_uploader("Upload source-schema CSV or Parquet", type=["csv", "parquet"])
    if uploaded:
        try:
            raw = (
                pd.read_csv(uploaded)
                if uploaded.name.lower().endswith(".csv")
                else pd.read_parquet(uploaded)
            )
            missing = {"timestamp_ms"} - set(raw.columns)
            if missing:
                st.error(f"Required source columns are missing: {', '.join(sorted(missing))}")
            else:
                st.write(
                    f"Loaded {len(raw):,} rows. A batch accepts at most 200 events; up to 2,000 rows can be replayed per upload."
                )
                st.dataframe(raw.head(10), use_container_width=True)
                if len(raw) > 2000:
                    st.warning(
                        "Only the first 2,000 rows are allowed per upload. Upload another time range to continue."
                    )
                if st.button("Replay uploaded telemetry", type="primary", disabled=len(raw) == 0):
                    sample = raw.head(2000)
                    payload = clean_records(sample)
                    results = []
                    for offset in range(0, len(payload), 200):
                        response = api(
                            "POST",
                            "/v1/events/batch",
                            json={"events": payload[offset : offset + 200]},
                        )
                        response.raise_for_status()
                        results.extend(response.json()["results"])
                    st.success(
                        f"Scored {len(results):,} source rows. These are replayed measurements, not a live game feed."
                    )
                    st.dataframe(
                        pd.DataFrame(results).head(100), use_container_width=True, hide_index=True
                    )
        except (ValueError, requests.RequestException) as exc:
            st.error(f"Could not read or submit this file: {exc}")
    st.subheader("Latest persisted telemetry")
    recent = load_events()
    if recent:
        st.dataframe(timestamp_frame(recent).head(100), use_container_width=True, hide_index=True)
    else:
        st.info("The event store is empty.")

elif page == "Anomaly Explorer":
    st.title("Anomaly Explorer")
    st.caption(
        "Use flags as a starting point for human review. The score is not calibrated as a probability."
    )
    status = st.selectbox(
        "Review status", ["All", "unresolved", "likely_true_anomaly", "false_positive"]
    )
    path = "/v1/alerts?page_size=200" + ("" if status == "All" else f"&status={status}")
    data = fetch(path, {"items": [], "total": 0})
    alerts = data.get("items", []) if data else []
    if not alerts:
        st.info("No matching alerts are available.")
    else:
        frame = timestamp_frame(alerts)
        st.dataframe(
            frame[
                [
                    "event_id",
                    "timestamp",
                    "session_label",
                    "anomaly_score",
                    "threshold",
                    "quality_status",
                    "review_status",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )
        chosen = st.selectbox("Select an alert to review", [item["event_id"] for item in alerts])
        detail = next(item for item in alerts if item["event_id"] == chosen)
        st.json(
            {
                "payload": detail.get("payload"),
                "evidence": detail.get("evidence"),
                "score": detail.get("anomaly_score"),
                "model_version": detail.get("model_version"),
            }
        )
        with st.form("feedback"):
            decision = st.selectbox(
                "Review outcome", ["unresolved", "likely_true_anomaly", "false_positive"]
            )
            note = st.text_area("Investigation note", max_chars=500)
            save = st.form_submit_button("Save review")
        if save:
            try:
                response = api(
                    "PATCH",
                    f"/v1/alerts/{chosen}/feedback",
                    json={"status": decision, "note": note or None},
                )
                response.raise_for_status()
                st.success(
                    "Review saved for later model evaluation. It does not trigger retraining."
                )
            except requests.RequestException as exc:
                st.error(f"Could not save review: {exc}")

elif page == "Model Performance":
    st.title("Model Performance")
    report_path = Path("artifacts/models/gameguard-if-v1/metrics.json")
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
        st.warning(report["evaluation_note"])
        st.caption(
            f"Dataset: {report['dataset_id']} / {report['dataset_config']} · primary model: {report['primary_detector']}"
        )
        st.markdown("**Chronological validation split**")
        st.dataframe(pd.DataFrame(report["validation"]).T, use_container_width=True)
        st.markdown("**Later chronological test split**")
        st.dataframe(pd.DataFrame(report["test"]).T, use_container_width=True)
        injection = report["synthetic_injection_check"]
        st.markdown("**Synthetic feature-shift sanity check**")
        st.json(injection)
        st.caption(
            "Injected extreme values validate the scoring path only. They are not ground-truth anomalies or an estimate of detector recall."
        )
    except (OSError, KeyError, json.JSONDecodeError) as exc:
        st.error(f"Measured evaluation report is unavailable: {exc}")

elif page == "Data Quality":
    st.title("Data Quality")
    result = fetch("/v1/monitoring", {})
    if result:
        summary = result.get("summary", {})
        quality = summary.get("data_quality_last_24h", {})
        st.metric("Scored events · 24h", f"{summary.get('events_last_24h', 0):,}")
        st.json(
            {
                "quality_status_counts": quality,
                "dataset_validation": "See the training report and dataset card for measured source validation.",
            }
        )
        st.caption(
            "Null source readings are recorded as a data-quality signal and median-imputed for scoring. Range and schema violations are rejected at ingestion."
        )

elif page == "Monitoring":
    st.title("Monitoring")
    report = fetch("/v1/monitoring", {})
    if report:
        drift = report.get("feature_drift", {})
        st.subheader("Feature drift")
        st.caption(drift.get("note", ""))
        st.metric("Recent sample size", f"{drift.get('sample_size', 0):,}")
        st.metric("Features with PSI ≥ 0.2", drift.get("drift_signal_count", "—"))
        if drift.get("features"):
            drift_df = pd.DataFrame.from_dict(drift["features"], orient="index").sort_values(
                "psi", ascending=False
            )
            st.dataframe(drift_df, use_container_width=True)
        else:
            st.info(
                "Monitoring needs at least 50 recent events before reporting feature-distribution drift."
            )
        st.subheader("Service and model feedback")
        st.json(
            {"summary": report.get("summary"), "model_performance": report.get("model_performance")}
        )

else:
    st.title("Model & Dataset Information")
    model = fetch("/v1/model/info", {})
    if model:
        st.subheader("Active model")
        st.json(model)
    st.subheader("Dataset provenance")
    st.markdown(
        "[Hugging Face dataset card](https://huggingface.co/datasets/rmems/gaming-telemetry) · dual MIT / Apache-2.0 license · one RE4 capture on one RTX 5080 workstation."
    )
    st.markdown(
        "The data contains hardware telemetry collected during a game session, not player actions, input traces, or verified suspicious behavior. It has no anomaly labels and does not establish generalization across games or hardware."
    )
    st.markdown(
        "See `docs/dataset-card.md`, `docs/model-card.md`, and `docs/deployment.md` for the complete data dictionary, limitations, and operations guide."
    )
