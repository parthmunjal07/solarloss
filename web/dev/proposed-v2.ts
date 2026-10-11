import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { z } from "zod";
import Ajv2020 from "ajv/dist/2020.js";
import addFormats from "ajv-formats";
import type { Metric } from "../src/lib/types";

// Offline only: the production import guard excludes this directory.
// Use the unchanged authoritative schema, including its nested/conditional rules.
// These interfaces expose validated fields; they do not replace schema validation.
import type { ReviewV2 } from "../src/lib/v2-types";

export type ProposedV2 = ReviewV2 & {
  approval_status: "proposed";
  decision: ReviewV2["decision"] & { owner_review: null };
};

const contract = JSON.parse(
  readFileSync(
    resolve("../artifacts/schema/review.schema.v0.2.0.proposed.json"),
    "utf8",
  ),
);
const validator = new Ajv2020({
  strict: false,
  strictNumbers: true,
  allErrors: true,
});
addFormats(validator);
const validate = validator.compile<ProposedV2>(contract);
export const proposedV2Schema = z
  .unknown()
  .transform((input, ctx): ProposedV2 => {
    if (!validate(input)) {
      ctx.addIssue({
        code: "custom",
        message: `Proposed contract mismatch: ${validator.errorsText(validate.errors)}`,
      });
      return z.NEVER;
    }
    if (
      input.approval_status !== "proposed" ||
      input.decision.owner_review !== null
    ) {
      ctx.addIssue({
        code: "custom",
        message: "This offline adapter accepts unapproved proposals only",
      });
      return z.NEVER;
    }
    if (input.review_id !== `review_${input.experiment.identifier}`) {
      ctx.addIssue({ code: "custom", message: "Review identity mismatch" });
      return z.NEVER;
    }
    return input;
  });
export function adaptProposedV2(input: unknown) {
  const r = proposedV2Schema.parse(input);
  const labels: Partial<Record<ReviewV2["metrics"][number]["id"], string>> = {
    signed_generation_deviation:
      "Signed model-expected minus measured generation deviation",
    positive_only_generation_deviation:
      "Positive-only model-expected minus measured generation deviation",
    observed_energy: "Measured target AC energy",
    expected_energy: "Model-expected target AC energy",
  };
  const metrics = Object.fromEntries(
    r.metrics.map((m) => [
      m.id,
      {
        ...m,
        label: labels[m.id] ?? m.id.replaceAll("_", " "),
        reason: m.reason ?? `${m.definition} Population: ${m.population}`,
      } satisfies Metric,
    ]),
  );
  return {
    origin: "proposed-v2" as const,
    approval: r.approval_status,
    id: r.experiment.identifier,
    researchVerdict: r.decision.verdict,
    reviewDecision: r.decision.event_review.state,
    eventReview: r.decision.event_review,
    ownerReview: r.decision.owner_review,
    experiment: r.experiment,
    provenance: r.provenance,
    metrics,
    series: r.series,
    electricalEvidence: r.electrical_evidence,
    candidateChecks: r.candidate_checks,
    limitations: r.limitations,
  };
}
