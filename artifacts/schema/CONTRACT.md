# Review artifact contract v0.1.0

This is a provisional, versioned handoff between offline analysis and the review API. It follows the two-person build plan's `review_EXPERIMENT_ID.json` artifact convention. The backend accepts and serves only artifacts that validate against `review.schema.json`.

## Status and versioning

`schema_version` is `0.1.0`. Field names and measurement semantics are not frozen: the science owner must review them against the dataset and analysis before the Friday F1 contract gate. Changes that affect meaning require a schema version change and a coordinated pull request. `analysis_version` identifies the offline analysis implementation/configuration that produced the artifact. S3 bucket versioning preserves prior uploads; the API serves the current object for an experiment.

## Measurement semantics to review

- `series.measured_power` is the experimental system's observed output.
- `series.raw_reference_power` is the reference system's uncalibrated observed output.
- `series.expected_power` is the calibrated expected output derived from the reference system. It is not the raw reference measurement.
- All three series fields use the shared `series.power_unit`. Valid rows require all three values; invalid rows may contain `null`. Optional expected-output bounds must be provided as a pair.
- Timestamps are UTC RFC 3339 values. The analysis producer is responsible for documenting sampling, interval alignment, and the precise energy-integration convention in `calculation` and the scientific methodology.
- Ratio metrics carry explicit numerator and denominator values with units. Calibration error identifies held-out healthy data and its denominator. The backend displays these values and does not recalculate them.

The meaning and allowed values of experiment `type`, time-window ordering, sample ordering, units, exclusions, validity rules, interval construction, and the exact meaning of the baseline and uncertainty fields require scientific-worker confirmation before the contract is frozen.

## Required content

Artifacts include dataset provenance and checksums, experiment type and systems, label provenance, aligned time series, metrics, a simple-baseline comparison, uncertainty and its limitations, quality checks and exclusions, one of the three decision states, reasons, limitations, robustness findings, and placebo findings. A finding that uses a synthetic robustness test must set `synthetic: true` and describe it as synthetic in `detail`.

## Boundary

The artifact is the sole source of scientific conclusions. The API validates and presents its decision, reasons, metrics, uncertainty, and findings; it must not infer or replace them. Product artifacts must contain real analysis output. Synthetic values belong only in tests and must be visibly named as synthetic test fixtures.
