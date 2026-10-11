import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { proposedV2Schema, adaptProposedV2 } from "../dev/proposed-v2";
import { reviewV1Schema } from "../src/lib/schemas";

// Read unchanged genuine reviews; no duplicate or invented scientific fixture.
const source = (id = "shading_01") =>
  JSON.parse(
    readFileSync(
      resolve(`../analysis/results/reviews_v3/review_${id}.json`),
      "utf8",
    ),
  );
describe("offline-only proposed v2 adapter", () => {
  it.each(["shading_01", "healthy_20220126_0300"])(
    "preserves LIMIT and unavailable event review in %s",
    (id) => {
      const input = source(id),
        r = adaptProposedV2(input);
      expect(r.approval).toBe("proposed");
      expect(r.researchVerdict).toBe("LIMIT");
      expect(r.reviewDecision).toBeNull();
      expect(r.ownerReview).toBeNull();
      expect(r.eventReview).toEqual(input.decision.event_review);
      expect(r.provenance).toEqual(input.provenance);
      expect(r.candidateChecks).toEqual(input.candidate_checks);
      expect(r.series).toEqual(input.series);
      expect(reviewV1Schema.safeParse(input).success).toBe(false);
    },
  );
  it("preserves exact energy, separate labels, coverage and uncertainty", () => {
    const input = source(),
      r = adaptProposedV2(input);
    for (const m of input.metrics)
      expect(r.metrics[m.id]).toMatchObject({
        value: m.value,
        availability: m.availability,
        unit: m.unit,
        coverage: m.coverage,
        ratio: m.ratio,
        uncertainty: m.uncertainty,
      });
    expect(r.metrics.signed_generation_deviation.label).toBe(
      "Signed model-expected minus measured generation deviation",
    );
    expect(r.metrics.positive_only_generation_deviation.label).toBe(
      "Positive-only model-expected minus measured generation deviation",
    );
    expect(r.metrics.observed_energy.label).toBe("Measured target AC energy");
    expect(r.metrics.expected_energy.label).toBe(
      "Model-expected target AC energy",
    );
    expect(
      r.metrics.expected_energy.value! - r.metrics.observed_energy.value!,
    ).toBeCloseTo(r.metrics.signed_generation_deviation.value!, 12);
    expect(r.metrics.signed_generation_deviation.coverage.valid_seconds).toBe(
      10549,
    );
  });
  it("keeps label bounds distinct from detector times and invalid estimates null", () => {
    const r = adaptProposedV2(source());
    if (r.experiment.type !== "documented_shading")
      throw new Error("Wrong case");
    expect(r.experiment.event_context.label_interval_utc?.start).toBe(
      "2022-02-08T07:11:02Z",
    );
    expect(
      r.experiment.event_context.detector_confirmations_utc["5_minute_primary"],
    ).toBe("2022-02-08T07:20:00Z");
    const invalid = r.series.samples.filter((s) => !s.valid);
    expect(invalid).toHaveLength(28);
    expect(invalid.every((s) => s.expected_power === null)).toBe(true);
    expect(invalid.some((s) => s.measured_power !== null)).toBe(true);
    expect(
      r.candidateChecks.every((c) => c.status === "proposed" && !c.approval),
    ).toBe(true);
  });
  it("retains the zero-labelled calibration population", () => {
    const r = adaptProposedV2(source("healthy_20220126_0300"));
    expect(r.experiment.event_context).toMatchObject({
      label_interval_utc: null,
      detector_calibration_population: true,
    });
    expect(r.limitations.join(" ")).toMatch(/not an independent holdout/);
  });
  it.each(["unavailable", "not_applicable"])(
    "preserves %s as null plus source reason",
    (availability) => {
      const input = source();
      input.metrics[0] = {
        ...input.metrics[0],
        availability,
        value: null,
        reason:
          "Test-only availability mutation; no new scientific measurement.",
      };
      expect(adaptProposedV2(input).metrics.healthy_mae).toMatchObject({
        availability,
        value: null,
        reason: input.metrics[0].reason,
      });
      input.metrics[0].reason = null;
      expect(proposedV2Schema.safeParse(input).success).toBe(false);
    },
  );
  it("allows negative signed deviation but rejects negative positive-only deviation", () => {
    const input = source();
    input.metrics.find(
      (m: { id: string }) => m.id === "signed_generation_deviation",
    ).value = -0.25; // test-only mutation
    expect(
      adaptProposedV2(input).metrics.signed_generation_deviation.value,
    ).toBe(-0.25);
    input.metrics.find(
      (m: { id: string }) => m.id === "positive_only_generation_deviation",
    ).value = -0.25;
    expect(proposedV2Schema.safeParse(input).success).toBe(false);
  });
  it.each([
    "event_context",
    "checksum",
    "model",
    "splits",
    "thresholds",
    "uncertainty",
    "ratio",
    "event_review",
  ])("rejects missing typed %s fields", (field) => {
    const input = source();
    switch (field) {
      case "event_context":
        delete input.experiment.event_context;
        break;
      case "checksum":
        delete input.provenance.source_checksums[0].source_verification;
        break;
      case "model":
        delete input.provenance.model.expected_power_semantics;
        break;
      case "splits":
        delete input.provenance.splits.train;
        break;
      case "thresholds":
        delete input.provenance.thresholds.by_window_minutes;
        break;
      case "uncertainty":
        delete input.metrics[5].uncertainty;
        break;
      case "ratio":
        delete input.metrics[0].ratio;
        break;
      case "event_review":
        delete input.decision.event_review;
        break;
    }
    expect(proposedV2Schema.safeParse(input).success).toBe(false);
  });
  it("rejects false approval, malformed hashes, uncertainty and event states", () => {
    const approved = source();
    approved.approval_status = "owner_approved";
    expect(proposedV2Schema.safeParse(approved).success).toBe(false);
    const hash = source();
    hash.provenance.source_checksums[0].sha256 = "invalid";
    expect(proposedV2Schema.safeParse(hash).success).toBe(false);
    const band = source();
    band.metrics[5].uncertainty.kind = "causal_confidence_interval";
    expect(proposedV2Schema.safeParse(band).success).toBe(false);
    const event = source();
    event.decision.event_review.state = "insufficient_evidence";
    expect(proposedV2Schema.safeParse(event).success).toBe(false);
  });
});
