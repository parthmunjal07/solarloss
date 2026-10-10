# Scientific schema change proposal — pending methodology handoff

**Status:** proposal only. The current JSON Schema remains `0.1.0`. Do not treat this document as an approved scientific definition or change the exporter from it alone.

The existing schema requires a numeric `metrics.energy_deficit`, even when no shading-energy estimate is available. The known science results include held-out healthy-output model metrics, while the final evaluation had no labelled shading episodes. Those results do not establish a shading detector, measured shading loss, or shading recovery. The backend must not relabel a healthy-placebo diagnostic to fill this numeric field.

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
