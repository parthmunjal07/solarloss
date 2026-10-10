import { labels } from "./formatters";
import type { ReviewV1 } from "./schemas";
import type { Metric, Review } from "./types";

const missing = (label: string): Metric => ({
  label,
  value: null,
  unit: "kWh",
  reason: "This total is not supplied by the v0.1 review artifact.",
});
export function adaptV1(r: ReviewV1): Review {
  return {
    origin: "api-v1",
    id: r.experiment.identifier,
    title: r.experiment.label_provenance.label,
    type: r.experiment.type,
    start: r.experiment.time_window.start,
    end: r.experiment.time_window.end,
    analysisVersion: r.analysis_version,
    producedAt: r.produced_at,
    dataset: { ...r.dataset, extractionDate: r.dataset.extraction_date },
    target: `${r.experiment.experimental_system.identifier}: ${r.experiment.experimental_system.description}`,
    reference: `${r.experiment.reference_system.identifier}: ${r.experiment.reference_system.description}`,
    powerUnit: r.series.power_unit,
    samples: r.series.samples,
    metrics: {
      expected: missing("Model-expected energy"),
      measured: missing("Observed energy"),
      deviation: {
        label: "Provisional energy deficit",
        value: r.metrics.energy_deficit.value,
        unit: r.metrics.energy_deficit.unit,
        reason:
          "v0.1 scientific semantics are provisional. This is not confirmed shading loss or recoverable energy.",
      },
      positive: missing("Positive-only generation deviation"),
      coverage: {
        label: "Valid data coverage",
        value: r.metrics.coverage.value,
        unit: r.metrics.coverage.unit,
        reason: `${r.metrics.coverage.numerator.value} ${r.metrics.coverage.numerator.unit} / ${r.metrics.coverage.denominator.value} ${r.metrics.coverage.denominator.unit}`,
      },
    },
    decision: { ...r.decision, rules: r.decision.rules_version },
    observations: [
      r.experiment.label_provenance.label,
      ...r.quality_checks
        .filter((c) => c.status === "reported")
        .map((c) => c.detail),
    ],
    limitations: r.limitations,
    nextChecks: [],
    exclusions: r.exclusions,
    // A time window and a label do not establish precise intervention boundaries or detector times.
    event: null,
    alerts: [],
    maxGapSeconds: null,
    original: r,
  };
}
export const metricLabels = {
  signed: labels.deviation,
  positive: "Positive-only generation deviation",
  measured: "Observed energy",
  expected: "Model-expected energy",
};
