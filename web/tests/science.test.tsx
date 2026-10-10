import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { DecisionBanner } from "../src/components/decision/DecisionBanner";
import { MetricFigure } from "../src/components/ui/Common";
import { reviewV1Schema } from "../src/lib/schemas";
import { adaptV1 } from "../src/lib/adapters";
import { downsample, missingRegions, plotPoints } from "../src/lib/chart-data";
import {
  ApiError,
  fetchReview,
  fetchHealth,
  request,
  reportUrl,
  shouldRetry,
} from "../src/lib/api";
import { prohibitedModule, fixtureGuard } from "../scripts/fixture-guard";
import { fixture } from "./fixtures";

describe("scientific decisions and unavailable metrics", () => {
  it.each([
    ["supported_change", "Supported change"],
    ["inconclusive", "Inconclusive"],
    ["insufficient_evidence", "Insufficient evidence"],
  ] as const)("renders %s with the source reason", (state, label) => {
    render(
      <DecisionBanner
        decision={{
          state,
          reasons: ["SAMPLE supplied reason"],
          rules: "SAMPLE-rules",
        }}
      />,
    );
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(label);
    expect(screen.getByRole("region")).toHaveClass(state);
    expect(screen.getByText("SAMPLE supplied reason")).toBeInTheDocument();
  });
  it("does not convert a missing decision to a research decision", () => {
    render(<DecisionBanner decision={null} />);
    expect(screen.getByRole("heading")).toHaveTextContent(
      "Review decision not available",
    );
    expect(screen.queryByText("Inconclusive")).not.toBeInTheDocument();
  });
  it("shows a null metric as unavailable with its reason", () => {
    render(
      <MetricFigure
        metric={{
          label: "Observed energy",
          value: null,
          unit: "kWh",
          reason: "Not supplied by the source",
        }}
      />,
    );
    expect(screen.getByText("Not available")).toBeInTheDocument();
    expect(screen.getByText("Not supplied by the source")).toBeInTheDocument();
  });
  it("does not fabricate energies or relabel the provisional v1 value", () => {
    const r = adaptV1(fixture());
    expect(r.metrics.expected.value).toBeNull();
    expect(r.metrics.measured.value).toBeNull();
    expect(r.metrics.deviation.label).toBe("Provisional energy deficit");
    expect(r.metrics.deviation.value).toBe(12.5);
    expect(r.samples[0].expected_power).toBe(450);
    expect(r.samples[0].raw_reference_power).toBe(500);
    expect(r.event).toBeNull();
  });
});
describe("contract validation", () => {
  it("accepts the complete v1 test shape", () => {
    expect(reviewV1Schema.safeParse(fixture()).success).toBe(true);
  });
  it("rejects v2 and any owner-approval flag in production", () => {
    expect(
      reviewV1Schema.safeParse({
        ...fixture(),
        schema_version: "0.2.0",
        approval_status: "proposed",
      }).success,
    ).toBe(false);
    expect(
      reviewV1Schema.safeParse({
        ...fixture(),
        approval_status: "owner_approved",
      }).success,
    ).toBe(false);
  });
  it("rejects valid null samples, unpaired bounds, reversed intervals and unsafe source URLs", () => {
    const r = fixture();
    r.series.samples[0].measured_power = null;
    expect(reviewV1Schema.safeParse(r).success).toBe(false);
    const b = fixture();
    b.series.samples[0].expected_lower_bound = 3;
    expect(reviewV1Schema.safeParse(b).success).toBe(false);
    const c = fixture();
    c.exclusions[0].end = c.exclusions[0].start;
    expect(reviewV1Schema.safeParse(c).success).toBe(false);
    const u = fixture();
    u.dataset.source = "javascript:alert(1)";
    expect(reviewV1Schema.safeParse(u).success).toBe(false);
  });
});
describe("chart continuity and point budget", () => {
  it("breaks explicit exclusions that fall between sparse source rows", () => {
    const r = adaptV1(fixture());
    r.samples = [r.samples[0], r.samples[2]];
    const p = plotPoints(r);
    expect(p.some((point) => point.gap && !point.valid)).toBe(true);
    expect(p.filter((point) => point.valid)).toHaveLength(2);
  });
  it("preserves null and excluded rows with accurate units", () => {
    const points = plotPoints(adaptV1(fixture()));
    expect(points[0].measured).toBe(0.4);
    expect(points[0].expected).toBe(0.45);
    expect(points[0].reference).toBe(0.5);
    expect(
      points.find((p) => p.timestamp === "2026-10-09T10:30:00Z" && !p.gap)
        ?.measured,
    ).toBeNull();
    expect(missingRegions(points)).toHaveLength(1);
  });
  it("preserves gaps, boundaries and extrema when reducing thousands of samples", () => {
    const r = adaptV1(fixture()),
      points = Array.from({ length: 10000 }, (_, i) => ({
        time: i,
        timestamp: String(i),
        measured: i === 1240 ? 999 : Math.sin(i),
        expected: Math.cos(i),
        reference: 1,
        residual: null,
        bounds: null,
        valid: i < 400 || i > 450,
      }));
    const compact = downsample(points, [520]);
    expect(compact.length).toBeLessThanOrEqual(1500);
    expect(compact.some((p) => p.time === 1240)).toBe(true);
    expect(compact.some((p) => p.time === 520)).toBe(true);
    expect(compact.some((p) => !p.valid)).toBe(true);
    expect(r.metrics.deviation.value).toBe(12.5);
  });
  it("refuses unsafe reduction when alternating gaps exceed the budget", () => {
    const p = plotPoints(adaptV1(fixture()))[0];
    expect(
      downsample(
        Array.from({ length: 3000 }, (_, i) => ({
          ...p,
          time: i,
          valid: i % 2 === 0,
        })),
      ),
    ).toEqual([]);
  });
});
describe("API failures and report navigation", () => {
  it("validates the backend health route", async () => {
    const fetch = vi.fn().mockResolvedValue(new Response('{"status":"ok"}'));
    vi.stubGlobal("fetch", fetch);
    expect(await fetchHealth()).toEqual({ status: "ok" });
    expect(fetch).toHaveBeenCalledWith("/api/v1/health", expect.anything());
  });
  it.each([400, 404, 500, 503])(
    "handles HTTP %s without fixture substitution",
    async (status) => {
      vi.stubGlobal(
        "fetch",
        vi.fn().mockResolvedValue(new Response("{}", { status })),
      );
      await expect(fetchReview("sample")).rejects.toMatchObject({ status });
    },
  );
  it("rejects invalid JSON and wrong experiment identities", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("not-json")));
    await expect(fetchReview("sample")).rejects.toThrow("invalid results file");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(JSON.stringify(fixture()))),
    );
    await expect(fetchReview("another")).rejects.toThrow("belongs to another");
  });
  it("rejects malformed schema responses and only retries temporary errors", async () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response('{"schema_version":"0.2.0"}')),
    );
    await expect(
      request("/api/v1/reviews/sample", reviewV1Schema),
    ).rejects.toThrow("unsupported contract");
    expect(shouldRetry(0, new ApiError("missing", 404))).toBe(false);
    expect(shouldRetry(0, new ApiError("temporary", 503))).toBe(true);
    expect(shouldRetry(2, new ApiError("temporary", 503))).toBe(false);
  });
  it("uses the backend HTML redirect route and rejects unsafe identifiers", () => {
    expect(reportUrl("shading_01")).toBe("/api/v1/reviews/shading_01/report");
    expect(() => reportUrl("../unsafe")).toThrow();
  });
});
describe("production import guard", () => {
  it.each([
    "C:/repo/web/src/fixtures/sample.json",
    "C:\\repo\\web\\tests\\fixture.ts",
    "/repo/analysis/results/demo.csv",
    "/repo/web/scripts/research-preview.ts",
  ])("blocks %s", (path) => expect(prohibitedModule(path)).toBe(true));
  it("fails the actual Vite build hook for prohibited imports", () => {
    const hook = fixtureGuard().moduleParsed as (
      this: { error: (message: string) => never },
      module: { id: string },
    ) => void;
    expect(() =>
      hook.call(
        {
          error: (message) => {
            throw new Error(message);
          },
        },
        { id: "/repo/src/fixtures/sample.ts" },
      ),
    ).toThrow("Production fixture import prohibited");
    expect(prohibitedModule("/repo/src/lib/adapters.ts")).toBe(false);
  });
});
