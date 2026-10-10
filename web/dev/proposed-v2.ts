import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { z } from "zod";
import Ajv2020 from "ajv/dist/2020.js";
import addFormats from "ajv-formats";
import type { Metric } from "../src/lib/types";

// Offline adapter only. Importing this directory from a production screen fails the build.
// Validate against the actual proposed contract, then narrow only the typed fields we can render.
const contract = JSON.parse(
  readFileSync(
    resolve("../artifacts/schema/review.schema.v0.2.0.proposed.json"),
    "utf8",
  ),
);
const validator = new Ajv2020({ strict: false, allErrors: true });
addFormats(validator);
const validate = validator.compile(contract);
const finite = z.number().finite();
const metricSchema = z
  .looseObject({
    id: z.enum([
      "healthy_mae",
      "healthy_nmae",
      "healthy_bias",
      "episode_recall",
      "healthy_alarm_runs_per_hour",
      "signed_generation_deviation",
      "positive_only_generation_deviation",
      "observed_energy",
      "expected_energy",
    ]),
    availability: z.enum(["estimated", "unavailable"]),
    value: finite.nullable(),
    unit: z.string(),
    reason: z.string().nullable(),
    population: z.string(),
    definition: z.string(),
    calculation: z.string(),
  })
  .superRefine((m, ctx) => {
    if (
      (m.availability === "estimated" &&
        (m.value === null || m.reason !== null)) ||
      (m.availability === "unavailable" && (m.value !== null || !m.reason))
    )
      ctx.addIssue({
        code: "custom",
        message:
          "Availability requires a finite value or null plus a source reason",
      });
  });
export const proposedV2Schema = z
  .unknown()
  .superRefine((input, ctx) => {
    if (!validate(input))
      ctx.addIssue({
        code: "custom",
        message: `Proposed contract mismatch: ${validator.errorsText(validate.errors)}`,
      });
  })
  .pipe(
    z.looseObject({
      schema_version: z.literal("0.2.0"),
      approval_status: z.literal("proposed"),
      review_id: z.string(),
      experiment: z.looseObject({
        identifier: z.string(),
        type: z.string(),
        start: z.string(),
        end: z.string(),
      }),
      metrics: z.array(metricSchema),
      decision: z.looseObject({
        verdict: z.enum(["GO", "LIMIT", "REJECT"]),
        reasons: z.array(z.string()),
        rule_version: z.string(),
      }),
    }),
  )
  .superRefine((r, ctx) => {
    if (r.review_id !== `review_${r.experiment.identifier}`)
      ctx.addIssue({ code: "custom", message: "Review identity mismatch" });
  });
export type ProposedV2 = z.infer<typeof proposedV2Schema>;
export function adaptProposedV2(input: unknown) {
  const r = proposedV2Schema.parse(input);
  const labels: Record<string, string> = {
    signed_generation_deviation: "Signed modelled generation deviation",
    positive_only_generation_deviation: "Positive-only generation deviation",
    observed_energy: "Observed energy",
    expected_energy: "Model-expected energy",
  };
  const metrics: Record<string, Metric> = Object.fromEntries(
    r.metrics.map((m) => [
      m.id,
      {
        label: labels[m.id] ?? m.id.replaceAll("_", " "),
        value: m.value,
        unit: m.unit,
        reason: m.reason ?? `${m.definition}. Population: ${m.population}.`,
      },
    ]),
  );
  return {
    origin: "proposed-v2" as const,
    approval: "proposed" as const,
    id: r.experiment.identifier,
    researchVerdict: r.decision.verdict,
    reviewDecision: null,
    metrics,
  };
}
