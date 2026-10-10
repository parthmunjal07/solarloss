import { test, expect } from "@playwright/test";
import { mkdir } from "node:fs/promises";
import { createServer } from "node:http";
import type { AddressInfo } from "node:net";
import AxeBuilder from "@axe-core/playwright";
import { fixture, listing } from "../fixtures";

const sizes = [
  { width: 375, height: 812 },
  { width: 768, height: 1024 },
  { width: 1280, height: 900 },
];
const routes = [
  "/",
  "/experiments",
  "/experiments/shading_01",
  "/experiments/shading_01/report",
  "/method",
];
for (const size of sizes)
  for (const mode of ["summary", "analyst"]) {
    test(`all routes at ${size.width}px in ${mode}`, async ({ page }) => {
      await page.setViewportSize(size);
      const errors: string[] = [];
      page.on("pageerror", (error) => errors.push(error.message));
      await mkdir("qa-screenshots", { recursive: true });
      for (const path of routes) {
        await page.goto(`${path}?mode=${mode}&preview=research`);
        await expect(page.locator("main h1")).toHaveCount(1);
        await expect(
          page.getByRole("button", {
            name: mode === "summary" ? "Summary" : "Analyst",
            exact: true,
          }),
        ).toHaveAttribute("aria-pressed", "true");
        if (path === "/experiments")
          await expect(
            page.getByRole("link", { name: "Review experiment", exact: true }),
          ).toHaveCount(1);
        if (path === "/experiments/shading_01") {
          await expect(
            page.getByText("Measured against expected", { exact: true }),
          ).toBeVisible();
          await expect(
            page.getByText("Signed modelled generation deviation", {
              exact: true,
            }),
          ).toBeVisible();
          await expect(page.locator(".metrics .figure").first()).toHaveText(
            /2\.8\s*kWh/,
          );
        }
        if (path.endsWith("/report")) {
          await expect(
            page.getByRole("heading", {
              name: "Review decision not available",
            }),
          ).toBeVisible();
          await expect(
            page.getByRole("button", { name: "Export unavailable" }),
          ).toBeDisabled();
          await expect(
            page.getByText("Proposed · Unapproved").first(),
          ).toBeVisible();
        }
        expect(
          await page.evaluate(
            () => document.documentElement.scrollWidth <= window.innerWidth,
          ),
        ).toBe(true);
        await page.screenshot({
          path: `qa-screenshots/${size.width}-${mode}-${path.replaceAll("/", "_") || "home"}.png`,
          fullPage: true,
        });
      }
      expect(errors).toEqual([]);
    });
  }
test("reading mode survives reload, navigation and explicit summary override", async ({
  page,
}) => {
  await page.goto("/experiments?preview=research&mode=summary");
  await page.getByRole("button", { name: "Analyst", exact: true }).click();
  await expect(page).toHaveURL(/mode=analyst/);
  await page.reload();
  await expect(
    page.getByRole("button", { name: "Analyst", exact: true }),
  ).toHaveAttribute("aria-pressed", "true");
  await page
    .getByRole("link", { name: "Review experiment", exact: true })
    .click();
  await expect(page).toHaveURL(/shading_01.*mode=analyst/);
  await page.goto("/method?mode=summary");
  await expect(
    page.getByRole("button", { name: "Summary", exact: true }),
  ).toHaveAttribute("aria-pressed", "true");
});
test("measurement drawer is keyboard reachable, paginated and restores focus", async ({
  page,
}) => {
  await page.goto("/experiments/shading_01?preview=research&mode=analyst");
  const trigger = page.getByRole("button", { name: "Inspect measurements" });
  await trigger.focus();
  await page.keyboard.press("Enter");
  await expect(
    page.getByRole("dialog", { name: "Original measurements" }),
  ).toBeVisible();
  await expect(page.locator("tbody tr")).toHaveCount(20);
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await expect(page.getByText("Page 2 of 132")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(trigger).toBeFocused();
});
for (const state of [
  "supported_change",
  "inconclusive",
  "insufficient_evidence",
] as const) {
  test(`API review decision ${state} is artifact-driven`, async ({ page }) => {
    await page.route("**/api/v1/reviews/sample", (route) =>
      route.fulfill({ json: fixture(state) }),
    );
    await page.goto("/experiments/sample/report?mode=analyst");
    const label = {
      supported_change: "Supported change",
      inconclusive: "Inconclusive",
      insufficient_evidence: "Insufficient evidence",
    }[state];
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(label);
    await expect(
      page.getByRole("link", { name: "Export report" }),
    ).toHaveAttribute("href", "/api/v1/reviews/sample/report");
    await expect(
      page.getByText("SAMPLE decision reason").first(),
    ).toBeVisible();
  });
}
test("report anchor follows the real route shape and a redirect", async ({
  page,
}) => {
  const downloadServer = createServer((_request, response) => {
    response.setHeader("Content-Type", "text/html");
    response.end("<h1>SAMPLE redirected HTML report</h1>");
  });
  await new Promise<void>((resolve) =>
    downloadServer.listen(0, "127.0.0.1", resolve),
  );
  const port = (downloadServer.address() as AddressInfo).port;
  try {
    await page.route("**/api/v1/reviews/sample", (route) =>
      route.fulfill({ json: fixture() }),
    );
    await page.route("**/api/v1/reviews/sample/report", (route) =>
      route.fulfill({
        status: 302,
        headers: { Location: `http://127.0.0.1:${port}/download` },
      }),
    );
    await page.goto("/experiments/sample/report");
    await page.getByRole("link", { name: "Export report" }).click();
    await expect(page.getByRole("heading")).toHaveText(
      "SAMPLE redirected HTML report",
    );
  } finally {
    await new Promise<void>((resolve, reject) =>
      downloadServer.close((error) => (error ? reject(error) : resolve())),
    );
  }
});
test("empty API, malformed API and 503 are clear without synthetic fallback", async ({
  page,
}) => {
  await page.route("**/api/v1/experiments", (route) =>
    route.fulfill({ json: { experiments: [] } }),
  );
  await page.goto("/experiments");
  await expect(page.getByText("No reviews are available yet.")).toBeVisible();
  await page.unroute("**/api/v1/experiments");
  await page.route("**/api/v1/experiments", (route) =>
    route.fulfill({ json: { experiments: [{ broken: true }] } }),
  );
  await page.reload();
  await expect(
    page.getByText(/results file is invalid or uses an unsupported contract/),
  ).toBeVisible();
  await page.unroute("**/api/v1/experiments");
  await page.route("**/api/v1/experiments", (route) =>
    route.fulfill({ status: 503, json: {} }),
  );
  await page.reload();
  await expect(page.getByText(/review service is unavailable/)).toBeVisible();
});
test("real listing shows only supplied records", async ({ page }) => {
  await page.route("**/api/v1/experiments", (route) =>
    route.fulfill({ json: listing() }),
  );
  await page.route("**/api/v1/reviews/sample", (route) =>
    route.fulfill({ json: fixture() }),
  );
  await page.goto("/experiments");
  await expect(
    page.getByRole("link", { name: "Review experiment", exact: true }),
  ).toHaveCount(1);
  await expect(page.getByText("SAMPLE synthetic dataset")).toBeVisible();
});
test("production ignores research preview and does not serve measurements", async ({
  page,
}) => {
  await page.route("**/api/v1/reviews/shading_01", (route) =>
    route.fulfill({ status: 404, json: {} }),
  );
  await page.goto(
    "http://127.0.0.1:4173/experiments/shading_01/report?preview=research",
  );
  await expect(
    page.getByText("This review is not available in the API."),
  ).toBeVisible();
  await expect(page.getByText("Research preview", { exact: true })).toHaveCount(
    0,
  );
  await expect(
    page.getByRole("button", { name: "Export unavailable" }),
  ).toHaveCount(0);
  const response = await page.request.get(
    "http://127.0.0.1:4173/__research-preview",
  );
  expect(response.headers()["content-type"]).not.toContain("application/json");
});
test("reduced motion and 200 percent text scaling keep the layout usable", async ({
  page,
}) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.setViewportSize({ width: 640, height: 900 });
  await page.goto(
    "/experiments/shading_01/report?preview=research&mode=analyst",
  );
  await page.addStyleTag({ content: "body { zoom: 2; }" });
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  const overflow = await page.evaluate(() =>
    [...document.querySelectorAll("body *")]
      .filter((e) => e.getBoundingClientRect().right > window.innerWidth + 1)
      .map((e) => ({
        tag: e.tagName,
        class: e.className,
        text: e.textContent?.slice(0, 80),
      }))
      .slice(-12),
  );
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
    JSON.stringify(overflow),
  ).toBe(true);
});

test("WCAG checks cover every page in both modes and the measurement drawer", async ({
  page,
}) => {
  test.setTimeout(90_000);
  await page.setViewportSize({ width: 375, height: 812 });
  for (const mode of ["summary", "analyst"])
    for (const path of routes) {
      await page.goto(`${path}?mode=${mode}&preview=research`);
      await expect(page.locator("main h1")).toHaveCount(1);
      const results = await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
        .analyze();
      expect(
        results.violations,
        `${path} ${mode}: ${JSON.stringify(results.violations.map((v) => ({ id: v.id, nodes: v.nodes.map((n) => n.target) })))}`,
      ).toEqual([]);
    }
  await page.goto("/experiments/shading_01?mode=analyst&preview=research");
  await page.getByRole("button", { name: "Inspect measurements" }).click();
  expect(
    (await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze())
      .violations,
  ).toEqual([]);
});
