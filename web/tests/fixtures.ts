import type { ReviewV1, DecisionState } from "../src/lib/schemas";
// SAMPLE: invented unit-test values. This module is blocked from production imports.
export function fixture(state: DecisionState = "supported_change"): ReviewV1 {
  const quantity = { value: 10, unit: "intervals" };
  return {
    schema_version: "0.1.0",
    review_id: "review_sample",
    analysis_version: "SAMPLE-test",
    produced_at: "2026-10-09T00:00:00Z",
    dataset: {
      name: "SAMPLE synthetic dataset",
      source: "https://example.invalid/sample",
      version: "SAMPLE",
      checksums: [
        { algorithm: "SAMPLE", digest: "SAMPLE", scope: "Unit tests only" },
      ],
    },
    experiment: {
      identifier: "sample",
      type: "SAMPLE synthetic experiment",
      experimental_system: {
        identifier: "SAMPLE target",
        description: "Synthetic target",
      },
      reference_system: {
        identifier: "SAMPLE reference",
        description: "Synthetic control",
      },
      time_window: {
        start: "2026-10-09T10:00:00Z",
        end: "2026-10-09T11:00:00Z",
      },
      label_provenance: {
        label: "SAMPLE test experiment",
        method: "Invented for unit tests",
        source: "SAMPLE",
      },
    },
    series: {
      timestamp_basis: "UTC",
      power_unit: "W",
      samples: [
        {
          timestamp: "2026-10-09T10:00:00Z",
          measured_power: 400,
          expected_power: 450,
          raw_reference_power: 500,
          valid: true,
        },
        {
          timestamp: "2026-10-09T10:30:00Z",
          measured_power: null,
          expected_power: null,
          raw_reference_power: null,
          valid: false,
        },
        {
          timestamp: "2026-10-09T11:00:00Z",
          measured_power: 320,
          expected_power: 360,
          raw_reference_power: 400,
          valid: true,
        },
      ],
    },
    metrics: {
      energy_deficit: { value: 12.5, unit: "Wh", calculation: "SAMPLE value" },
      deficit_fraction: {
        value: 0.1,
        unit: "fraction",
        numerator: quantity,
        denominator: quantity,
      },
      coverage: {
        value: 0.8,
        unit: "fraction",
        numerator: quantity,
        denominator: quantity,
      },
      calibration_error: {
        value: 5,
        unit: "W",
        statistic: "SAMPLE RMSE",
        evaluation_population: "held_out_healthy",
        denominator: quantity,
      },
      valid_interval_count: 8,
      total_interval_count: 10,
    },
    baseline_comparison: {
      metric: "SAMPLE RMSE",
      unit: "W",
      evaluation_population: "SAMPLE held-out",
      simple_baseline: { name: "SAMPLE baseline", value: 8 },
      calibrated_reference: { name: "SAMPLE expected", value: 5 },
    },
    uncertainty: {
      method: "SAMPLE",
      independent_blocks: { count: 2, unit: "SAMPLE blocks" },
      interval: null,
      not_estimated_reason: "SAMPLE unavailable uncertainty",
      exploratory: true,
      limitations: ["SAMPLE only"],
    },
    quality_checks: [
      { name: "SAMPLE quality", status: "passed", detail: "Synthetic check" },
    ],
    exclusions: [
      {
        start: "2026-10-09T10:30:00Z",
        end: "2026-10-09T10:35:00Z",
        reason: "SAMPLE exclusion",
      },
    ],
    decision: {
      state,
      reasons: ["SAMPLE decision reason"],
      rules_version: "SAMPLE",
    },
    limitations: ["SAMPLE synthetic fixture, not measured evidence"],
    robustness: { status: "not_evaluated", findings: [] },
    placebo: { status: "not_evaluated", findings: [] },
  };
}
export function listing() {
  const r = fixture();
  return {
    experiments: [
      {
        experiment_id: r.experiment.identifier,
        review_id: r.review_id,
        analysis_version: r.analysis_version,
        experiment_type: r.experiment.type,
        experimental_system: r.experiment.experimental_system,
        reference_system: r.experiment.reference_system,
        time_window: r.experiment.time_window,
        decision_state: r.decision.state,
      },
    ],
  };
}
