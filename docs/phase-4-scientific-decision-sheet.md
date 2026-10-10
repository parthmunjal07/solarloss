# Phase 4 scientific decision sheet

**Status: pending Rachit's review.** This sheet records the proposed v0.2 field meanings; it does not record approval. The V3 source exports remain unchanged and marked `approval_status: proposed`.

## Decisions required for v0.2 review serving

1. **Power channels and residual sign.** `measured_power` is target inverter measured AC Pg in W; `raw_reference_power` is comparison inverter measured AC Pg in W; `expected_power` is calibrated healthy model-expected target AC Pg in W. Signed residual is expected minus measured. Expected power is not a second measurement.
2. **Energy deviations.** `signed_generation_deviation` preserves positive and negative residual energy. `positive_only_generation_deviation` clips negative endpoint residuals before integration. Neither is verified recoverable electricity, savings, or causal loss.
3. **Energy population.** The two energy calculations use the same valid source-record intervals and population. `valid_seconds`, `observed_labelled_seconds`, and `wall_span_seconds` remain distinct. A displayed coverage percentage must name its numerator, denominator field, and population; do not expose an unqualified percentage.
4. **Reference versus model.** Raw comparison-inverter Pg is an input to the frozen model and is not the target's model-expected output.
5. **Labels and detector output.** Source intervention label bounds and detector confirmation times have separate fields and provenance. Detector confirmation is not backdated to the label start.
6. **Provenance scope.** Raw Zenodo hashes were checked in the committed V2 run and were not rehashed by the V3 exporter. Committed V2 inputs were rehashed by that exporter. These are different verification claims.
7. **Uncertainty.** The `shading_01` 0.370142–0.394806 kWh range is an empirical matched-placebo model-error band for signed deviation. It is not a causal confidence interval for missing unshaded target generation.
8. **Research versus event status.** `decision.verdict` is an experiment/capability research gate (`GO`, `LIMIT`, or `REJECT`). `decision.event_review` is a separate event-level state. The V3 examples currently record event review as unavailable with a reason; no state is inferred from the research verdict.
9. **Zero-labelled comparison.** `healthy_stability` describes a source interval with zero Fault labels. It does not independently certify that the system was fault-free. The 2022-01-26 example was part of detector calibration, not an independent holdout.
10. **Technician checks.** Candidate checks are proposed, contextual prompts. They are not confirmed diagnoses, fault classifications, or repair recommendations. Any future approval must identify the approver, date, exact contract/protocol scope, and decision reference.
11. **Unavailable values.** `unavailable` means an in-scope quantity was not determined; `not_applicable` means it is outside the case scope. Both use `value: null` and a reason. Neither may be rendered as zero.
12. **Data gaps.** The 2,848,806-second gap stays a separate unavailability sidecar with its previous and next source timestamps, unavailable energy (`value: null`), and reason. It is not a shading or healthy review and creates no zero-production interval or fabricated samples.

## Exporter detail requests for a production UI

- In the shading series, 28 of 2,148 retained samples have `valid: false` and `expected_power: null`, while measured and raw-reference power remain present. The export has no per-sample missing-channel reason and no gap markers. Keep those values null and unbridged; do not infer why the model-expected value is unavailable. Rachit should decide whether a future exporter version will add field-level validity and reason codes.
- Electrical evidence currently records window-level comparison summaries, not observation timestamps or interval bounds per measurement. Keep it labeled as contextual summary evidence. Rachit should add explicit temporal support before any screen presents it as a timestamped technician trigger.

## Separate approval boundary

Rachit must approve or revise these field definitions before v0.2 production serving. Approval of these definitions alone does not approve detector generalisation, event-level decision gates, physical fault diagnosis, or maintenance guidance. Those require separate evidence and review.

**Recorded decision:** none in this repository. Signoff must identify the approved schema version and SHA256, protocol scope, decision reference, approver, and UTC date/time. Until that record exists, v0.2 remains offline-only and the production API remains v0.1-only.

## Bounded data-gap case proposal

If a data-gap case type is approved, preserve the current sidecar's bounded fields: case identity; `source_gap_utc.previous_observation` and `next_observation`; elapsed `gap_seconds`; an unavailable energy object with null value, kWh unit, and reason; unavailable event state with null state and reason; and source checksums. It has no power samples and must not be placed in the experiment listing until a separately versioned case schema and API behavior are approved.

Current source values (excerpt; the checksum provenance stays in the unchanged sidecar):

```json
{
  "case_record_version": "1.0.0",
  "status": "unavailable_for_proposed_v0_2_review",
  "review_id": "review_insufficient_data_gap_20211222_20220124",
  "experiment_identifier": "insufficient_data_gap_20211222_20220124",
  "source_case": "example_cases_v2.insufficient_data",
  "source_gap_utc": {
    "previous_observation": "2021-12-22T07:00:34Z",
    "next_observation": "2022-01-24T06:20:40Z"
  },
  "gap_seconds": 2848806.0,
  "energy_deviation": {
    "availability": "unavailable",
    "value": null,
    "unit": "kWh",
    "reason": "No supported aligned source intervals occur within the gap; no interpolation or energy integration is performed."
  },
  "event_review_state": {
    "availability": "unavailable",
    "state": null,
    "reason": "The v0.2 type enum has no data-gap/insufficient-data type; assigning one of its current types would imply unsupported semantics."
  }
}
```
