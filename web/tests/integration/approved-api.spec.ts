import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { mkdir, readFile } from "node:fs/promises";
import { createHash } from "node:crypto";

const releasePath = new URL(
  "../../../artifacts/releases/v0.2.0/shading_01/approved/review_shading_01.json",
  import.meta.url,
);

test("real backend returns the genuine approved release and its versioned listing", async ({
  request,
}) => {
  const release = JSON.parse(await readFile(releasePath, "utf8"));
  const response = await request.get("/api/v1/reviews/shading_01");
  expect(response.status()).toBe(200);
  expect(await response.json()).toEqual(release);
  const listing = await request.get("/api/v1/experiments");
  expect(listing.status()).toBe(200);
  expect((await listing.json()).experiments).toEqual([
    {
      experiment_id: "shading_01",
      review_id: "review_shading_01",
      schema_version: "0.2.0",
      experiment_type: "documented_shading",
      time_window: {
        start: release.experiment.start,
        end: release.experiment.end,
      },
      research_verdict: "LIMIT",
      event_review: release.decision.event_review,
    },
  ]);
  expect((await request.get("/api/v1/reviews/not-stored")).status()).toBe(404);
});

for (const width of [375, 768, 1280]) {
  test(`approved API journey and actual HTML download at ${width}px`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 900 });
    const errors: string[] = [],
      requests: string[] = [];
    page.on("pageerror", (e) => errors.push(e.message));
    page.on("request", (r) => requests.push(r.url()));
    const listingResponse = page.waitForResponse((response) =>
      response.url().endsWith("/api/v1/experiments"),
    );
    await page.goto("/experiments?mode=summary");
    expect((await listingResponse).status()).toBe(200);
    await expect(page.getByText(/Research LIMIT/)).toBeVisible();
    await page
      .getByRole("link", { name: "Review experiment", exact: true })
      .click();
    await expect(
      page.getByRole("heading", {
        name: "Measured against expected",
        exact: true,
      }),
    ).toBeVisible();
    await expect(page.locator(".case-metrics")).toContainText(
      "Signed modelled deviation",
    );
    await page
      .getByRole("link", { name: /Explore the two-inverter setup/ })
      .click();
    const setup = page.locator("#experimental-setup");
    await expect(setup.locator(".array-viewport")).toHaveAttribute(
      "data-renderer",
      "3d",
      { timeout: 30_000 },
    );
    await setup
      .getByRole("button", { name: "Documented shading", exact: true })
      .click();
    await expect(setup.locator(".array-explanation")).toContainText(
      "One entire module",
    );
    await setup
      .getByRole("link", { name: /Review measured versus expected/ })
      .click();
    await expect(page.locator("#performance-comparison")).toBeInViewport();
    await expect(
      page.getByRole("heading", { name: "Unavailable", exact: true }),
    ).toBeVisible();
    await mkdir("qa-screenshots", { recursive: true });
    await page.mouse.move(width - 2, 0);
    await page.evaluate(() => {
      (document.activeElement as HTMLElement)?.blur();
      window.scrollTo({ top: 0, behavior: "instant" });
    });
    await page.screenshot({
      path: `qa-screenshots/api-${width}-investigation-viewport.png`,
    });
    await page.screenshot({
      path: `qa-screenshots/api-${width}-investigation.png`,
      fullPage: true,
    });
    await setup
      .getByRole("button", { name: "Use 2D view", exact: true })
      .click();
    await expect(setup.locator(".array-viewport")).toHaveAttribute(
      "data-renderer",
      "2d",
    );
    const module = setup.getByRole("button", {
      name: "Inverter 1, string 1, module 3",
      exact: true,
    });
    await module.focus();
    await page.keyboard.press("Enter");
    await expect(setup.locator(".array-module-info")).toContainText(
      "representative fully shaded module",
    );
    expect(
      (
        await new AxeBuilder({ page })
          .include("#experimental-setup")
          .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
          .analyze()
      ).violations,
    ).toEqual([]);
    await page.evaluate(() => {
      (document.activeElement as HTMLElement)?.blur();
      window.scrollTo({ top: 0, behavior: "instant" });
    });
    await page.screenshot({
      path: `qa-screenshots/api-${width}-fallback.png`,
      fullPage: true,
    });
    await page
      .getByRole("link", { name: "Check the evidence", exact: true })
      .click();
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(
      "Documented shading: evidence & next checks",
    );
    await expect(
      page.getByRole("heading", { name: "LIMIT", exact: true }),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Suggested investigation plan" }),
    ).toBeVisible();
    await expect(
      page.getByText("Proposed · Unapproved", { exact: true }).first(),
    ).toBeVisible();
    await page.evaluate(() => window.scrollTo({ top: 0, behavior: "instant" }));
    await page.screenshot({
      path: `qa-screenshots/api-${width}-overview-viewport.png`,
    });
    await page
      .getByRole("button", { name: "Technical details", exact: true })
      .click();
    await page
      .getByText("Electrical evidence — window-level contextual summaries", {
        exact: true,
      })
      .click();
    await expect(
      page.getByText(/No per-measurement observation time is supplied/),
    ).toBeVisible();
    expect(
      (
        await new AxeBuilder({ page })
          .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
          .analyze()
      ).violations,
    ).toEqual([]);
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    await page.mouse.move(width - 2, 0);
    await page.evaluate(() => {
      (document.activeElement as HTMLElement)?.blur();
      window.scrollTo({ top: 0, behavior: "instant" });
    });
    await page.screenshot({
      path: `qa-screenshots/api-${width}-report.png`,
      fullPage: true,
    });
    const downloadPromise = page.waitForEvent("download");
    await page
      .getByRole("link", { name: "Export report", exact: true })
      .click();
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toBe("shading_01-report.html");
    const path = await download.path();
    expect(path).toBeTruthy();
    const html = await readFile(path!, "utf8");
    expect(html).toContain(
      "Research verdict (experiment/capability scope): LIMIT",
    );
    expect(html).toContain("0.39704897741387934");
    expect(html).toContain("2022-02-08T07:11:02Z");
    expect(html).toContain("2022-02-08T07:20:00Z");
    expect(html).toContain("SOLARLOSS-SCI-V02-20261011-SHADING01-RELEASE");
    expect(html).not.toContain("EXPERIMENTAL — PROPOSED CONTRACT");
    expect(new URL(download.url()).pathname).toBe(
      `/local-reports/${createHash("sha256").update(html).digest("hex")}.html`,
    );
    expect(requests.some((url) => url.includes("__research-preview"))).toBe(
      false,
    );
    expect(errors).toEqual([]);
  });
}

test("commercial entry and exploration preserve the approved scientific values", async ({
  page,
}) => {
  const sceneRequests: string[] = [];
  page.on("request", (r) => {
    if (/SolarArrayScene/.test(r.url())) sceneRequests.push(r.url());
  });
  await mkdir("qa-screenshots/product", { recursive: true });
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(
    "When solar output drops, see what to investigate next.",
  );
  await expect(page.locator(".preview-result")).toContainText("+0.397");
  expect(sceneRequests).toEqual([]);
  for (const width of [1280, 768, 375]) {
    await page.setViewportSize({ width, height: 900 });
    await page.screenshot({
      path: `qa-screenshots/product/${width}-landing-viewport.png`,
    });
    await page.screenshot({
      path: `qa-screenshots/product/${width}-landing.png`,
      fullPage: true,
    });
  }
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.locator(".setup-story").scrollIntoViewIfNeeded();
  await page.locator("#experimental-setup").scrollIntoViewIfNeeded();
  await expect(page.locator(".array-viewport")).toHaveAttribute(
    "data-renderer",
    "3d",
    { timeout: 30000 },
  );
  await page
    .locator("#experimental-setup")
    .screenshot({ path: "qa-screenshots/product/1280-landing-setup.png" });
  await page.evaluate(() => window.scrollTo({ top: 0, behavior: "instant" }));
  await page
    .getByRole("link", { name: "Explore a real solar case", exact: true })
    .first()
    .click();
  expect(page.url()).not.toContain("preview=");
  await expect(
    page.getByRole("button", { name: "Overview", exact: true }),
  ).toHaveAttribute("aria-pressed", "true");
  const totals = await page.locator(".case-metrics").innerText();
  const reference = page.getByRole("button", {
    name: "Raw reference",
    exact: true,
  });
  await reference.click();
  await expect(reference).toHaveAttribute("aria-pressed", "true");
  await page
    .getByRole("button", { name: "Model-expected", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Model-expected", exact: true }),
  ).toHaveAttribute("aria-pressed", "false");
  const release = JSON.parse(await readFile(releasePath, "utf8"));
  const invalidIndex = release.series.samples.findIndex(
    (s: { expected_power: number | null }) => s.expected_power === null,
  );
  await page
    .getByLabel("Inspect an exact source timestamp")
    .fill(String(invalidIndex));
  await expect(page.locator(".selected-source")).toContainText(
    release.series.samples[invalidIndex].timestamp,
  );
  await expect(page.locator(".selected-source")).toContainText("Not available");
  const handle = page.locator(".recharts-brush-traveller").first();
  await handle.focus();
  await page.keyboard.press("ArrowRight");
  expect(await page.locator(".case-metrics").innerText()).toBe(totals);
  await page
    .getByRole("button", { name: "Inspect measurements", exact: true })
    .click();
  await page.getByLabel(/Show invalid or excluded/).check();
  await expect(page.locator("tbody tr")).toHaveCount(20);
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await expect(page.locator("tbody tr")).toHaveCount(8);
  await page.keyboard.press("Escape");
});

test("downloaded report is self-contained, accessible and compact in print", async ({
  page,
  request,
}) => {
  test.setTimeout(90_000);
  const response = await request.get("/api/v1/reviews/shading_01/report", {
    maxRedirects: 0,
  });
  expect(response.status()).toBe(302);
  const download = await request.get(response.headers().location);
  const html = await download.text();
  const { writeFile } = await import("node:fs/promises");
  await mkdir("qa-screenshots/reports", { recursive: true });
  await writeFile("qa-screenshots/reports/shading_01-report.html", html);
  const requests: string[] = [];
  page.on("request", (r) => requests.push(r.url()));
  for (const width of [1280, 768, 375]) {
    await page.setViewportSize({ width, height: 900 });
    await page.setContent(html);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(
      "Documented shading: evidence & next checks",
    );
    await expect(
      page.getByRole("img", {
        name: "Measured versus model-expected target power",
      }),
    ).toBeVisible();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    expect(
      (
        await new AxeBuilder({ page })
          .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
          .analyze()
      ).violations,
    ).toEqual([]);
    await page.screenshot({
      path: `qa-screenshots/reports/${width}-executive.png`,
    });
    await page.screenshot({
      path: `qa-screenshots/reports/${width}-full.png`,
      fullPage: true,
    });
  }
  await page.setViewportSize({ width: 1280, height: 900 });
  const appendix = page.locator("details").filter({
    has: page.locator("summary", {
      hasText: "Original measurement table — all retained records",
    }),
  });
  await appendix.locator("summary").click();
  await expect(appendix.locator("tbody tr")).toHaveCount(2148);
  await appendix.locator("summary").scrollIntoViewIfNeeded();
  await page.screenshot({
    path: "qa-screenshots/reports/measurement-appendix.png",
  });
  const metrics = page.locator("details").filter({
    has: page.locator("summary", {
      hasText: "Full metric definitions, values and populations",
    }),
  });
  await metrics.locator("summary").click();
  await expect(metrics).toContainText("0.39704897741387934");
  await page.emulateMedia({ media: "print" });
  await expect(appendix).toBeHidden();
  await expect(metrics).toBeHidden();
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({ path: "qa-screenshots/reports/print-preview.png" });
  const pdf = await page.pdf({
    path: "qa-screenshots/reports/shading_01-print.pdf",
    preferCSSPageSize: true,
    printBackground: true,
  });
  expect(
    pdf.toString("latin1").match(/\/Type \/Page\b/g)!.length,
  ).toBeLessThanOrEqual(8);
  expect(requests).toEqual([]);
});
