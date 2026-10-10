import { z } from "zod";
import { sampleSchema } from "./schemas";
import type { Review } from "./types";
import { metricLabels } from "./adapters";

// Compact projection of committed V2 results, not the proposed API contract.
const finite = z.number().finite();
const eventSchema = z.object({
  event_id: z.string(),
  start: z.iso.datetime({ offset: true }),
  end: z.iso.datetime({ offset: true }),
  label_descriptions: z.array(z.string()),
  energy: z.object({
    signed_energy_kwh: finite,
    positive_only_kwh: finite,
    actual_energy_kwh: finite,
    expected_energy_kwh: finite,
    coverage: finite,
    valid_seconds: finite,
    observed_labelled_support_seconds: finite,
  }),
  detection: z.object({
    "5": z.object({ confirmation_utc: z.iso.datetime({ offset: true }) }),
  }),
  placebo: z.object({
    empirical_model_error_band_kwh: z.array(finite).length(2),
    blocks: finite,
    days: finite,
  }),
  electrical: z.object({
    Va: z.object({ matched_median_delta_from_healthy: finite }),
  }),
});
export const researchProjectionSchema = z.object({
  projection_version: z.literal("research-preview-1"),
  approval_status: z.literal("proposed"),
  event: eventSchema,
  samples: z.array(sampleSchema).min(1),
  analysis_version: z.string(),
  produced_at: z.string(),
  residuals: z.record(z.string(), finite.nullable()),
  protocol_sha256: z.string().regex(/^[a-f0-9]{64}$/),
  code_sha256: z.string(),
  selected_model: z.string(),
  boundaries: z.record(z.string(), z.union([z.string(), z.array(z.string())])),
  detected_episodes: finite,
  episode_count: finite,
  false_alarm_rate: finite,
  verdict: z.literal("LIMIT"),
  limitations: z.array(z.string()),
  source_files: z.array(z.string()),
  source_hashes: z.array(
    z.object({ algorithm: z.string(), digest: z.string(), scope: z.string() }),
  ),
});
export function adaptResearch(input: unknown): Review {
  const p = researchProjectionSchema.parse(input),
    e = p.event;
  const metric = (label: string, value: number, unit = "kWh") => ({
    label,
    value,
    unit,
    reason:
      label === metricLabels.expected
        ? "Healthy-model expectation over valid labelled intervals."
        : label === metricLabels.measured
          ? "Recorded output over the same valid labelled intervals."
          : "Source modelled deviation over valid labelled intervals. Not recoverable energy.",
  });
  return {
    origin: "research-preview",
    id: e.event_id,
    title: "One fully shaded module",
    type: "documented_shading",
    start: e.start,
    end: e.end,
    analysisVersion: p.analysis_version,
    producedAt: p.produced_at,
    dataset: {
      name: "University of La Réunion research installation",
      source: "https://zenodo.org/records/7291380",
      version: "Pinned Zenodo record v2",
      checksums: p.source_hashes,
    },
    target: "Inverter 1, experimentally shaded line",
    reference: "Inverter 2, comparison line",
    powerUnit: "W",
    samples: p.samples,
    residuals: p.residuals,
    metrics: {
      expected: metric(metricLabels.expected, e.energy.expected_energy_kwh),
      measured: metric(metricLabels.measured, e.energy.actual_energy_kwh),
      deviation: metric(metricLabels.signed, e.energy.signed_energy_kwh),
      positive: metric(metricLabels.positive, e.energy.positive_only_kwh),
      coverage: {
        label: "Eligible labelled-duration coverage",
        value: e.energy.coverage,
        unit: "1",
        reason: `${e.energy.valid_seconds} valid seconds / ${e.energy.observed_labelled_support_seconds} observed labelled seconds`,
      },
    },
    decision: null,
    observations: [
      "The dataset documents one fully shaded module during this interval.",
      "Measured experimental output differs from the calibrated healthy expectation.",
    ],
    limitations: p.limitations,
    exclusions: [],
    event: { start: e.start, end: e.end, label: "Documented shading" },
    alerts: [e.detection["5"].confirmation_utc],
    maxGapSeconds: 18,
    nextChecks: [
      {
        title: "Check acquisition and inverter records",
        observed: "A sustained signed AC deviation was recorded in shading_01.",
        candidate:
          "A production change is consistent with the observations; its cause is not diagnosed.",
        support:
          "Measured output and healthy-model expectation differ during the documented intervention.",
        alternatives:
          "Reference drift, curtailment, temperature and sensor errors can also affect the comparison.",
        needed:
          "Timestamp configuration, acquisition gaps, inverter status and independent irradiance records.",
        qualification:
          "An operator can review existing records; qualified PV personnel should interpret further array tests.",
        source: "analysis/INVESTIGATION_GUIDANCE_PROPOSAL.md, NREL §9",
        status: "unapproved",
      },
      {
        title: "Request operating-point context",
        observed:
          "PV-side voltage differs from its matched healthy comparator.",
        candidate:
          "Mismatch or MPPT behaviour is a candidate explanation, not a diagnosis.",
        support:
          "V2 electrical observations report a matched voltage departure.",
        alternatives:
          "Temperature, irradiance and inverter state also shift operating voltage.",
        needed:
          "Inverter MPPT/state logs and verified array configuration before further assessment.",
        qualification:
          "Qualified PV personnel determine whether additional measurements are appropriate.",
        source:
          "analysis/INVESTIGATION_GUIDANCE_PROPOSAL.md, Sandia DC Array IV",
        status: "unapproved",
      },
    ],
    research: {
      verdict: p.verdict,
      detected: p.detected_episodes,
      episodes: p.episode_count,
      falseAlarmRate: p.false_alarm_rate,
      falseAlarmLimit: 0.05,
      errorBand: e.placebo.empirical_model_error_band_kwh,
      placeboBlocks: e.placebo.blocks,
      placeboDays: e.placebo.days,
      voltageDelta: e.electrical.Va.matched_median_delta_from_healthy,
      protocol: p.protocol_sha256,
      model: p.selected_model,
      boundaries: p.boundaries,
      sourceFiles: p.source_files,
    },
  };
}
