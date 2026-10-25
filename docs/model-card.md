# Model card: GameGuard Isolation Forest

## Intended use

Flag unusual GPU/CPU system measurements in game-session telemetry for an operator to investigate. The model is not a cheating detector, fraud detector, hardware diagnostic, player-risk score, or probability estimator. A high score is a deviation signal and does not establish cause or intent.

## Training data and method

The model was trained on the `re4` split of `rmems/gaming-telemetry`, a single roughly 90-minute RE4 Remake capture from one RTX 5080 system. There are no trusted anomaly labels. The data are sorted by timestamp and split into 70% training, 15% validation, and 15% later test rows. A median imputer and 200-tree Isolation Forest are fitted on the earliest split. A simple robust-deviation threshold and Local Outlier Factor are comparison detectors. LOF fits a seeded sample of up to 5,000 training rows to bound memory use.

The production threshold is the validation 99th percentile (a target 1% alert budget). This is a rate-control choice and is not optimized for precision, recall, or the best incident outcome. The saved evaluation report contains observed validation/test alert rates, score quantiles, time-block rate variation, and an artificial extreme-value wiring check. No accuracy, F1, precision, recall, or PR-AUC is reported.

## Explainability

For each event the service returns the top finite feature deviations from the training medians, scaled by robust training dispersion. These are supporting measurements, not causal attributions to the Isolation Forest. Scores are detector-relative and not calibrated probabilities.

## Known limitations

- Single game, session, GPU, machine, and operator; no external validation or labeled incident examples.
- Normal variation outside this capture may generate alerts. The historical validation threshold may not control future alert volume after drift.
- Dataset card says there are no thermal or hardware-slowdown incidents in this capture. The model is therefore not validated for those scenarios.
- Data drift PSI is not model-performance degradation. Reviewer feedback is collected but is not automatically used for retraining.
- Synthetic feature injection checks scoring behavior, not real anomaly recall.

## Reproducibility

Run `python -m gameguard.train`. The artifact and metrics JSON include the dataset SHA-256, model version, threshold rule, seed, features, data checks, chronological split boundaries, and observed measurements.
