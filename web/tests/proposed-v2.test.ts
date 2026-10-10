import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { proposedV2Schema, adaptProposedV2 } from "../dev/proposed-v2";

const source = () =>
  JSON.parse(readFileSync(resolve("tests/proposed-v2-sample.json"), "utf8"));
describe("offline-only proposed v2 adapter", () => {
  it("retains research verdict without inferring a review decision", () => {
    const r = adaptProposedV2(source());
    expect(r.approval).toBe("proposed");
    expect(r.reviewDecision).toBeNull();
    expect(r.metrics.signed_generation_deviation.label).toBe(
      "Signed modelled generation deviation",
    );
  });
  it("rejects owner-approved claims and unavailable numbers without a source reason", () => {
    const approved = source();
    approved.approval_status = "owner_approved";
    expect(proposedV2Schema.safeParse(approved).success).toBe(false);
    const malformed = source();
    malformed.metrics[0].availability = "unavailable";
    expect(proposedV2Schema.safeParse(malformed).success).toBe(false);
  });
});
