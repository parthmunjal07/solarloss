# Scientific schema change proposal — pending methodology handoff

**Status:** proposal only. The production API still accepts schema `0.1.0`. Do not treat this document or the proposed `0.2.0` schema as an approved scientific definition or change a production exporter from it alone.

The original v0.1 review contract required numeric `metrics.energy_deficit`, even when no shading-energy estimate was available. The later v2 research package now documents 23 retrospective shading episodes and separate signed and positive-only deviations. The results remain limited to one installation: the primary detector's healthy false-alarm rate exceeds its frozen gate, energy is not a true counterfactual, and no diagnosis or recovery claim is established. The backend must not relabel a healthy-placebo diagnostic or positive-only residual as recovered energy.

The science owner and backend owner should settle these topics together before a schema version change:

1. **Unavailable shading energy:** represent a not-estimated result without a fabricated number, with a reason and an explicit status.
2. **Metric identity and meaning:** distinguish healthy-model diagnostics, placebo metrics, measured shading loss, and recovery estimates with a reviewed metric type and definition.
3. **Units and denominators:** specify power/energy units, interval integration, time basis, numerator, denominator, and whether a reported fraction is duration- or count-based.
4. **Model provenance:** retain model version, training configuration, calibration data/population, and relevant fit/evaluation settings.
5. **Data quality:** retain exclusion reasons, missing-data treatment, validity rules, and any exclusions that affect the result.
6. **Downsampling:** record whether samples were downsampled, the method, target or retained counts, and the source population.
7. **Evaluation population:** identify the population used for each metric, plus independent episode counts and the number of labelled shading episodes.
8. **Decision provenance:** record the rule/version, inputs, and review provenance that support the producer's final decision.

The method handoff must resolve these meanings before choosing field names, enums, requiredness, nullability, or numeric thresholds. Until then, schema v0.1.0 remains provisional. Any accepted artifact is displayed as producer-supplied evidence; API validation does not turn a number into a scientific conclusion.

## Phase 3 implementation boundary

The proposed schema's JSON content is copied to `artifacts/schema/review.schema.v0.2.0.proposed.json` for local validation and report previews. Its source remains `analysis/contracts/review.schema.v0.2.0.proposed.json`; platform-specific line-ending conversion does not change its JSON content. The production API uses only v0.1.0; no v0.2 endpoint, storage path, exporter, or deployment has been enabled. The package marks the v0.2 schema asset as proposed and non-serving.

The v0.2 local validator adds mechanical checks where the draft is explicit: version dispatch, internal identity, unique metric IDs, metric units, estimated/unavailable null rules, finite values, positive-only energy bounds, coverage ordering, paired uncertainty bounds, UTC timestamps, provenance digests, and proposed candidate status. It does not calculate metrics, select thresholds, diagnose faults, or certify an artifact's science. These local checks are implementation guardrails, not an approval of the scientific contract.

Open draft questions include the authority and evidence represented by `approval_status=owner_approved`; typed structure for electrical observations and candidate evidence; exact checksum field formats; the relationship between metric ratios and their declared populations; and the complete provenance required for a reproducible event artifact. The research owner must resolve these definitions before a production schema or exporter is approved.
