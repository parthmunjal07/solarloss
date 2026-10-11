import { describe, it, expect, vi } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { createHash } from "node:crypto";
import { MemoryRouter } from "react-router";
import { render, screen } from "@testing-library/react";
import { reviewV2Schema, adaptV2, APPROVED_SCHEMA_SHA256 } from "../src/lib/v2";
import { fetchReview, fetchExperiments } from "../src/lib/api";
import { experimentsSchema } from "../src/lib/schemas";
import { plotPoints } from "../src/lib/chart-data";
import {
  ResearchStatus,
  V2Evidence,
  V2Checks,
} from "../src/components/decision/V2Evidence";
import type { ReviewV2 } from "../src/lib/v2-types";
import { fixture } from "./fixtures";
const source = (): ReviewV2 =>
  JSON.parse(
    readFileSync(
      resolve("../analysis/results/reviews_v3/review_shading_01.json"),
      "utf8",
    ),
  );
describe("semantics-approved production V2 readiness", () => {
  it("accepts the genuinely authorized separate release through the production API parser", async () => {
    const r: ReviewV2 = JSON.parse(
      readFileSync(
        resolve(
          "../artifacts/releases/v0.2.0/shading_01/approved/review_shading_01.json",
        ),
        "utf8",
      ),
    );
    expect(reviewV2Schema.parse(r)).toEqual(r);
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(new Response(JSON.stringify(r), { status: 200 })),
    );
    const review = await fetchReview("shading_01");
    expect(review.origin).toBe("api-v2");
    expect(review.v2).toEqual(r);
    expect(review.decision).toBeNull();
    expect(review.metrics.deviation.value).toBe(0.39704897741387934);
  });
  it("ships the exact approved schema bytes, never a loosened copy", () => {
    const local = readFileSync(resolve("src/lib/review-v2-contract.json"));
    expect(
      local.equals(
        readFileSync(
          resolve("../artifacts/schema/review.schema.v0.2.0.proposed.json"),
        ),
      ),
    ).toBe(true);
    expect(createHash("sha256").update(local).digest("hex")).toBe(
      APPROVED_SCHEMA_SHA256,
    );
  });
  it("rejects proposed artifacts at the production boundary without manufacturing approval", async () => {
    const r = source();
    expect(reviewV2Schema.safeParse(r).success).toBe(false);
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(new Response(JSON.stringify(r), { status: 200 })),
    );
    await expect(fetchReview("shading_01")).rejects.toThrow(/approval record/);
    r.approval_status = "owner_approved";
    expect(reviewV2Schema.safeParse(r).success).toBe(false); // missing owner approval remains rejected
  });
  it("preserves V1 API compatibility", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          new Response(JSON.stringify(fixture()), { status: 200 }),
        ),
    );
    expect((await fetchReview("sample")).origin).toBe("api-v1");
  });
  it("accepts the actual backend V2 listing shape and keeps decisions separate", async () => {
    const r = source(),
      item = {
        experiment_id: r.experiment.identifier,
        review_id: r.review_id,
        schema_version: r.schema_version,
        experiment_type: r.experiment.type,
        time_window: { start: r.experiment.start, end: r.experiment.end },
        research_verdict: r.decision.verdict,
        event_review: r.decision.event_review,
      };
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ experiments: [item] }), {
          status: 200,
        }),
      ),
    );
    const list = await fetchExperiments();
    expect(list.experiments[0]).toMatchObject({
      research_verdict: "LIMIT",
      decision_state: null,
      event_review: { state: null, availability: "unavailable" },
    });
    expect(
      experimentsSchema.safeParse({
        experiments: [
          {
            ...item,
            event_review: { ...item.event_review, state: "supported_change" },
          },
        ],
      }).success,
    ).toBe(false);
  });
  it("preserves scientific channel identity and null expected-power gaps", () => {
    // Direct offline projection for rendering tests only; this never passes the API gate.
    const sourceReview = source(),
      r = adaptV2(sourceReview),
      points = plotPoints(r);
    expect(r.samples).toEqual(sourceReview.series.samples);
    const i = sourceReview.series.samples.findIndex((s) => !s.valid);
    expect(points[i].expected).toBeNull();
    expect(points[i].measured).toBe(
      sourceReview.series.samples[i].measured_power! / 1000,
    );
    expect(points[i].reference).toBe(
      sourceReview.series.samples[i].raw_reference_power! / 1000,
    );
    expect(r.metrics.deviation.value).toBe(0.39704897741387934);
    expect(r.event?.start).toBe("2022-02-08T07:11:02Z");
    expect(r.alerts[0]).toBe("2022-02-08T07:20:00Z");
  });
  it("renders LIMIT, unavailable event review and every proposed check boundary", () => {
    const r = source();
    render(
      <MemoryRouter>
        <ResearchStatus review={r} />
        <V2Evidence review={r} />
        <V2Checks review={r} />
      </MemoryRouter>,
    );
    expect(screen.getByRole("heading", { name: "LIMIT" })).toBeInTheDocument();
    expect(
      screen.getByText("Event-level review: Unavailable."),
    ).toBeInTheDocument();
    expect(screen.getAllByText("Proposed · Unapproved")).toHaveLength(
      r.candidate_checks.length,
    );
    for (const c of r.candidate_checks)
      expect(screen.getByText(c.safety_constraint)).toBeInTheDocument();
    expect(
      screen.getByText(/No per-measurement observation time/),
    ).toBeInTheDocument();
  });
});
