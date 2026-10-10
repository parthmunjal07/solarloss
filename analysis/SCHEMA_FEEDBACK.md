# Review contract feedback: v0.1.0

Reviewed against the provisional schema and contract on `rachit/backend-api`
(`artifacts/schema/review.schema.json`, `$id` `urn:solarloss:review:0.1.0`)
on 2026-10-09. This note is in the analysis track; it does not change
`backend/`, `web/`, or the backend branch.

The copied schema snapshot was semantically verified against branch commit
`e09535060767a276ba90e809abf5d81764fcbdcd` (schema blob
`f4483abfe38de96a4e1b80ae90ed7e593f720b21`).

## Semantics that fit the current schema

- `measured_power`: inverter 1 `Pg`, the shading-experiment output, in W.
- `raw_reference_power`: inverter 2 `Pg`, the contemporaneous uncalibrated
  control output, in W.
- `expected_power`: a prediction of inverter 1 `Pg` fitted only on documented
  healthy training observations. It is not inverter 2 power and does not use
  `Fault` as a predictor.
- `series.timestamp_basis`: UTC. Source rows carry a `+04:00` offset; convert
  them to UTC for JSON RFC 3339 timestamps while retaining the source timezone
  and offset in provenance.
- `power_unit`: `W`. Energy fields use `kWh`; ratios use `1` (dimensionless).
- `experiment.label_provenance`: `Fault` in the target electrical file, with
  its meanings taken from the Zenodo metadata image and cited publication.
- `decision.state`: keep the three stated values. The artifact should identify
  its predeclared rule set through `rules_version` and give human-readable
  evidence reasons and exclusions.

## Requested changes before v0.1 is frozen

1. **Signed versus positive-only energy.** `metrics.energy_deficit` does not
   define whether it is signed net deviation or positive-only curtailed energy.
   Both are scientifically required and can differ materially. Add separately
   named, unit-bearing fields (for example, `signed_energy_deviation` and
   `positive_only_shortfall`) with their integration convention.
2. **Calibration and model comparison.** `calibration_error` permits only one
   statistic. The requested evaluation needs held-out healthy MAE, normalized
   MAE with an explicit denominator, and signed calibration bias. The baseline
   comparison also needs a way to identify the compared metric and the selected
   model (including a weather model when justified). Add structured metric
   entries instead of placing these values only in free-text findings.
3. **Uncertainty meaning.** The schema has an interval but does not say what
   quantity it bounds or how independent units are formed. For this study the
   proposed interval is an exploratory 95% cluster bootstrap interval for
   positive-only shortfall, resampling separated intervention episodes, not
   5-second rows. Please make the estimate/estimand explicit and allow the
   interval to be null when there are too few independent episodes.
4. **Coverage and exclusions.** A single `coverage` ratio needs a defined
   numerator and denominator (here: valid elapsed daylight seconds divided by
   documented evaluated daylight seconds). It should be possible to distinguish
   unavailable/misaligned reference records, weather exclusions, and fault
   label gaps. Current free-text exclusions are sufficient for display but not
   machine filtering.
5. **Compact series contract.** The producer can emit a bounded 5-minute
   series, with invalid samples retained at gaps and interval edges. Please
   define a maximum sample count or clarify the backend request/body limit so
   `series.samples` cannot accidentally become a full raw export.
6. **No estimable event.** The schema requires numeric `energy_deficit`, at
   least one `total_interval_count`, and at least one sample. It cannot encode
   an experimental effect that is not estimable because the held-out period
   contains no eligible shading episode. Please permit a null effect metric
   with a structured `not_estimable` reason and zero eligible intervals. For
   this dataset, the compatibility artifact is explicitly typed as a held-out
   healthy placebo and reports a measured placebo residual integral; it does
   not populate that field with a fabricated shading estimate.

## Provisional mapping until the contract changes

The analysis will validate against the checked-in v0.1.0 snapshot. To preserve
that schema's strict `additionalProperties: false`, the single `energy_deficit`
will represent positive-only shortfall and its `calculation` will state that
explicitly. Signed deviation, normalized error, calibration bias, reference
stability, and threshold details will be reported in the standalone model and
quality artifacts; they cannot all be represented as queryable numeric fields
in a v0.1 review artifact. The uncertainty interval will be null with an
explicit reason if fewer than two independent shading episodes are evaluable.
When no post-training shading episode is evaluable, the schema-compatible
review artifact is a held-out healthy placebo diagnostic, clearly typed as such;
the experimental shortfall remains unavailable and the decision is
`insufficient_evidence`.

This mapping is a compatibility fallback, not a recommendation to freeze the
current field semantics unchanged.
