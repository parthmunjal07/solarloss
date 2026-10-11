import Ajv2020 from "ajv/dist/2020.js";
import addFormats from "ajv-formats";
import { z } from "zod";
import contract from "./review-v2-contract.json";
import type { ReviewV2 } from "./v2-types";
import type { Metric, Review } from "./types";

// Exact semantics-approved contract; contains no research measurements.
// Lazy-loaded only after a real API response identifies itself as v0.2.
export const APPROVED_SCHEMA_SHA256 =
  "51001cac97423b454afac7b98ee733306666fe52e3ba22f5cb422ce987c461bd";
const ajv = new Ajv2020({
  strict: false,
  strictNumbers: true,
  allErrors: true,
});
addFormats(ajv);
const validate = ajv.compile<ReviewV2>(contract);
export const reviewV2Schema = z.unknown().transform((input, ctx): ReviewV2 => {
  if (!validate(input)) {
    ctx.addIssue({
      code: "custom",
      message: `v0.2 contract mismatch: ${ajv.errorsText(validate.errors)}`,
    });
    return z.NEVER;
  }
  const a = input.decision.owner_review;
  if (
    input.approval_status !== "owner_approved" ||
    !a ||
    a.schema_sha256 !== APPROVED_SCHEMA_SHA256 ||
    a.protocol_sha256 !== input.provenance.protocol_sha256
  ) {
    ctx.addIssue({
      code: "custom",
      message: "v0.2 API reviews require a matching artifact approval record",
    });
    return z.NEVER;
  }
  if (
    input.decision.event_review.availability !== "unavailable" ||
    input.candidate_checks.some((c) => c.status === "owner_approved")
  ) {
    ctx.addIssue({
      code: "custom",
      message:
        "Current v0.2 approval covers bounded research evidence only; event decisions and technician diagnoses are not approved",
    });
    return z.NEVER;
  }
  if (
    input.review_id !== `review_${input.experiment.identifier}` ||
    Date.parse(input.experiment.start) >= Date.parse(input.experiment.end) ||
    input.series.samples.some(
      (s, i, all) =>
        i > 0 && Date.parse(s.timestamp) <= Date.parse(all[i - 1].timestamp),
    )
  ) {
    ctx.addIssue({
      code: "custom",
      message: "Invalid review identity, interval or sample chronology",
    });
    return z.NEVER;
  }
  return input;
});
export function adaptV2(r: ReviewV2): Review {
  const byId = new Map(r.metrics.map((m) => [m.id, m]));
  const metric = (
    id: ReviewV2["metrics"][number]["id"],
    label: string,
  ): Metric => {
    const m = byId.get(id);
    return m
      ? {
          ...m,
          label,
          reason: m.reason ?? `${m.definition} Population: ${m.population}`,
        }
      : {
          label,
          value: null,
          unit: "kWh",
          reason: "Not supplied by this review artifact.",
        };
  };
  const e = r.experiment,
    context = e.event_context;
  const durations = byId.get("signed_generation_deviation")?.coverage;
  const valid = durations?.valid_seconds,
    observed = durations?.observed_labelled_seconds,
    wall = durations?.wall_span_seconds;
  return {
    origin: "api-v2",
    id: e.identifier,
    title:
      e.type === "documented_shading"
        ? e.event_context.label_description
        : "Zero-labelled comparison interval",
    type: e.type,
    start: e.start,
    end: e.end,
    analysisVersion: "V2 research / V3 export",
    producedAt: "Not supplied; approval time is recorded separately",
    dataset: {
      name: "University of La Réunion research installation",
      source: "https://zenodo.org/records/7291380",
      version: "Pinned Zenodo record v2",
      checksums: r.provenance.source_checksums.flatMap((c) =>
        ["md5", "sha256"].map((algorithm) => ({
          algorithm,
          digest: c[algorithm as "md5" | "sha256"],
          scope: `${c.file} · ${c.byte_count} bytes · ${c.role} · ${c.source_verification}`,
        })),
      ),
    },
    target: "Inverter 1, experimental line",
    reference: "Inverter 2, comparison line",
    powerUnit: r.series.power_unit,
    samples: r.series.samples,
    metrics: {
      expected: metric("expected_energy", "Model-expected target AC energy"),
      measured: metric("observed_energy", "Measured target AC energy"),
      deviation: metric(
        "signed_generation_deviation",
        "Signed modelled generation deviation",
      ),
      positive: metric(
        "positive_only_generation_deviation",
        "Positive-only modelled generation deviation",
      ),
      coverage: {
        label: "Valid source-record duration",
        value: valid ?? null,
        unit: "seconds",
        reason: `${valid ?? "Not available"} valid seconds; ${observed ?? "Not available"} observed labelled seconds; ${wall ?? "Not available"} wall-span seconds. Population: ${byId.get("signed_generation_deviation")?.population ?? "Not supplied"}`,
      },
    },
    decision: null,
    observations: [
      e.type === "documented_shading"
        ? e.event_context.label_description
        : e.event_context.note,
      "Measured target AC output is compared with calibrated model-expected target output; raw reference output is a separate measured input.",
    ],
    limitations: r.limitations,
    nextChecks: [],
    exclusions: [
      ...r.provenance.exclusions,
      ...r.series.downsampling.gap_markers,
    ],
    event: context.label_interval_utc
      ? {
          ...context.label_interval_utc,
          label:
            e.type === "documented_shading"
              ? e.event_context.label_description
              : "Source label",
        }
      : null,
    alerts:
      e.type === "documented_shading" &&
      e.event_context.detector_confirmations_utc["5_minute_primary"]
        ? [e.event_context.detector_confirmations_utc["5_minute_primary"]]
        : [],
    maxGapSeconds: null,
    v2: r,
  };
}
