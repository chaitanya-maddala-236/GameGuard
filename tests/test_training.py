import json

from gameguard.train import train


def test_training_compares_unlabeled_detectors_and_writes_artifacts(tmp_path, telemetry_frame):
    source = tmp_path / "fixture.parquet"
    telemetry_frame.to_parquet(source)
    output = tmp_path / "trained"
    result = train(source, output)
    metrics = json.loads((output / "metrics.json").read_text(encoding="utf-8"))
    assert (output / "model.joblib").is_file()
    assert metrics["labels_available"] is False
    assert metrics["supervised_metrics_reported"] is False
    assert set(metrics["test"]) == {
        "statistical_thresholds",
        "isolation_forest",
        "local_outlier_factor",
    }
    assert metrics["test"]["isolation_forest"]["rows"] == 36
    assert "precision" not in metrics["test"]["isolation_forest"]
    assert "recall" not in metrics["test"]["isolation_forest"]
    assert result["metadata"]["feature_names"]
