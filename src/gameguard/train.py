"""Reproducible unsupervised training and evaluation for GameGuard."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from datetime import UTC, datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.impute import SimpleImputer
from sklearn.neighbors import LocalOutlierFactor
from sklearn.pipeline import Pipeline

from gameguard.features import FEATURE_NAMES, transform_frame
from gameguard.validation import validate_frame

DATASET_ID = "rmems/gaming-telemetry"
DATASET_CONFIG = "re4"
MODEL_VERSION = "gameguard-if-v1"
SEED = 2026
ALERT_BUDGET = 0.01


def read_data(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(
            f"Dataset not found at {path}. Run `python scripts/download_data.py` first."
        )
    frame = pd.read_parquet(path)
    report = validate_frame(frame)
    if report.duplicate_timestamps:
        raise ValueError(f"Dataset contains {report.duplicate_timestamps} duplicate timestamps")
    return frame.sort_values("timestamp_ms", kind="stable").reset_index(drop=True)


def robust_threshold_scores(
    features: np.ndarray, medians: np.ndarray, scales: np.ndarray
) -> np.ndarray:
    return np.max(np.abs((features - medians) / scales), axis=1)


def evaluate_scores(scores: np.ndarray, threshold: float, *, block_count: int = 5) -> dict:
    flags = scores >= threshold
    blocks = [
        float(flags[start:end].mean())
        for start, end in (
            (len(flags) * i // block_count, len(flags) * (i + 1) // block_count)
            for i in range(block_count)
        )
        if end > start
    ]
    return {
        "rows": int(len(scores)),
        "threshold": float(threshold),
        "alert_count": int(flags.sum()),
        "alert_rate": float(flags.mean()) if len(flags) else 0.0,
        "score_p50": float(np.quantile(scores, 0.50)),
        "score_p95": float(np.quantile(scores, 0.95)),
        "score_p99": float(np.quantile(scores, 0.99)),
        "alert_rate_by_test_time_block": blocks,
        "alert_rate_block_range": float(max(blocks) - min(blocks)) if blocks else 0.0,
    }


def score(estimator, features: pd.DataFrame | np.ndarray) -> np.ndarray:
    return -np.asarray(estimator.decision_function(features), dtype=float)


def _reference_distribution(features: pd.DataFrame) -> dict:
    result = {}
    for name in FEATURE_NAMES:
        values = features[name].to_numpy(dtype=float)
        finite = values[np.isfinite(values)]
        edges = (
            np.unique(np.quantile(finite, np.linspace(0, 1, 11))) if len(finite) else np.asarray([])
        )
        if len(edges) < 2:
            center = float(edges[0]) if len(edges) else 0.0
            edges = np.asarray([center - 0.5, center + 0.5])
        edges = edges.tolist()
        result[name] = {
            "edges": edges,
            "counts": [int(x) for x in np.histogram(finite, bins=edges)[0]],
        }
    return result


def _synthetic_injection_report(estimator, test_features: pd.DataFrame, threshold: float) -> dict:
    count = min(128, len(test_features))
    control = test_features.iloc[:count].copy()
    injected = control.copy()
    injected["gpu_temperature_c"] = 120
    injected["gpu_power_w"] = 1_000_000
    injected["fan_speed_perc"] = 0
    injected["cpu_tctl_c"] = 130
    control_scores = score(estimator, control)
    injected_scores = score(estimator, injected)
    return {
        "kind": "synthetic_feature_shift_sanity_check",
        "rows": int(count),
        "median_control_score": float(np.median(control_scores)),
        "median_injected_score": float(np.median(injected_scores)),
        "injected_above_threshold_rate": float(np.mean(injected_scores >= threshold)),
        "injected_score_exceeds_control_rate": float(np.mean(injected_scores > control_scores)),
        "interpretation": "Artificial extreme values exercise scoring only; they are not real anomalies or labels.",
    }


def train(dataset_path: Path, output_dir: Path) -> dict:
    started = time.perf_counter()
    raw = read_data(dataset_path)
    report = validate_frame(raw)
    features = transform_frame(raw)
    n = len(raw)
    train_end = int(n * 0.70)
    validation_end = int(n * 0.85)
    train_x = features.iloc[:train_end]
    validation_x = features.iloc[train_end:validation_end]
    test_x = features.iloc[validation_end:]
    if min(len(train_x), len(validation_x), len(test_x)) < 20:
        raise ValueError("At least 20 rows are required in each chronological data split.")

    imputer = SimpleImputer(strategy="median", keep_empty_features=True)
    train_values = imputer.fit_transform(train_x)
    validation_values = imputer.transform(validation_x)
    test_values = imputer.transform(test_x)
    medians = np.median(train_values, axis=0)
    deviations = np.median(np.abs(train_values - medians), axis=0) * 1.4826
    scales = np.where(deviations > 1e-9, deviations, np.maximum(np.std(train_values, axis=0), 1.0))
    baseline_validation = robust_threshold_scores(validation_values, medians, scales)
    baseline_test = robust_threshold_scores(test_values, medians, scales)
    baseline_threshold = float(np.quantile(baseline_validation, 1 - ALERT_BUDGET))

    isolation = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median", keep_empty_features=True)),
            (
                "detector",
                IsolationForest(
                    n_estimators=200,
                    max_samples="auto",
                    contamination="auto",
                    random_state=SEED,
                    n_jobs=-1,
                ),
            ),
        ]
    )
    isolation.fit(train_x)
    isolation_val = score(isolation, validation_x)
    isolation_test = score(isolation, test_x)
    isolation_threshold = float(np.quantile(isolation_val, 1 - ALERT_BUDGET))

    rng = np.random.default_rng(SEED)
    lof_rows = min(5_000, len(train_x))
    lof_indices = np.sort(rng.choice(len(train_x), size=lof_rows, replace=False))
    lof = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median", keep_empty_features=True)),
            ("detector", LocalOutlierFactor(n_neighbors=min(35, lof_rows - 1), novelty=True)),
        ]
    )
    lof.fit(train_x.iloc[lof_indices])
    lof_val = score(lof, validation_x)
    lof_test = score(lof, test_x)
    lof_threshold = float(np.quantile(lof_val, 1 - ALERT_BUDGET))

    validation_start = int(raw.iloc[train_end]["timestamp_ms"])
    validation_stop = int(raw.iloc[validation_end - 1]["timestamp_ms"])
    test_start = int(raw.iloc[validation_end]["timestamp_ms"])
    test_stop = int(raw.iloc[-1]["timestamp_ms"])
    dataset_hash = hashlib.sha256(dataset_path.read_bytes()).hexdigest()
    metadata = {
        "model_version": MODEL_VERSION,
        "created_at_utc": datetime.now(UTC).isoformat(),
        "dataset": DATASET_ID,
        "dataset_config": DATASET_CONFIG,
        "dataset_sha256": dataset_hash,
        "source_rows": n,
        "feature_names": FEATURE_NAMES,
        "detector": "Isolation Forest",
        "threshold": isolation_threshold,
        "threshold_rule": "99th percentile of chronological validation anomaly scores (1% alert budget)",
        "alert_budget": ALERT_BUDGET,
        "random_seed": SEED,
        "split": {
            "method": "chronological, sorted by timestamp_ms",
            "train_rows": int(len(train_x)),
            "validation_rows": int(len(validation_x)),
            "test_rows": int(len(test_x)),
            "train_end_timestamp_ms": int(raw.iloc[train_end - 1]["timestamp_ms"]),
            "validation_start_timestamp_ms": validation_start,
            "validation_end_timestamp_ms": validation_stop,
            "test_start_timestamp_ms": test_start,
            "test_end_timestamp_ms": test_stop,
        },
        "source_validation": report.to_dict(),
        "feature_reference": {
            "medians": medians.tolist(),
            "scales": scales.tolist(),
        },
        "reference_distribution": _reference_distribution(train_x),
        "feature_evidence": "Top absolute robust deviations from the training median; descriptive, not causal attributions.",
        "anomaly_score_semantics": "Higher means more unusual under this fitted detector; it is not a probability.",
    }
    metrics = {
        "dataset_id": DATASET_ID,
        "dataset_config": DATASET_CONFIG,
        "dataset_sha256": dataset_hash,
        "labels_available": False,
        "supervised_metrics_reported": False,
        "evaluation_note": "No verified anomaly labels; alert rates and score stability are descriptive, not precision/recall.",
        "primary_detector": "Isolation Forest",
        "threshold_selection": metadata["threshold_rule"],
        "validation": {
            "statistical_thresholds": evaluate_scores(baseline_validation, baseline_threshold),
            "isolation_forest": evaluate_scores(isolation_val, isolation_threshold),
            "local_outlier_factor": evaluate_scores(lof_val, lof_threshold),
        },
        "test": {
            "statistical_thresholds": evaluate_scores(baseline_test, baseline_threshold),
            "isolation_forest": evaluate_scores(isolation_test, isolation_threshold),
            "local_outlier_factor": evaluate_scores(lof_test, lof_threshold),
        },
        "synthetic_injection_check": _synthetic_injection_report(
            isolation, test_x, isolation_threshold
        ),
        "model_fit_seconds": None,
        "dataset_validation": report.to_dict(),
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    model_path = output_dir / "model.joblib"
    joblib.dump({"estimator": isolation, "metadata": metadata}, model_path, compress=3)
    elapsed = time.perf_counter() - started
    metrics["model_fit_seconds"] = round(elapsed, 3)
    metrics["train_rows_per_second_including_evaluation"] = round(n / elapsed, 2)
    (output_dir / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    (output_dir / "model-info.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return {"metrics": metrics, "metadata": metadata, "model_path": str(model_path)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path("data/raw/re4/train-00000.parquet"))
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/models/gameguard-if-v1"))
    args = parser.parse_args()
    result = train(args.data, args.output_dir)
    print(json.dumps({"model_path": result["model_path"], "metrics": result["metrics"]}, indent=2))


if __name__ == "__main__":
    main()
