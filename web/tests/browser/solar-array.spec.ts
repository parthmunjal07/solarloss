import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { mkdir } from "node:fs/promises";

// Exercise the real renderer even on CI machines without a hardware GPU.
test.use({
  launchOptions: {
    executablePath: process.env.PLAYWRIGHT_EXECUTABLE_PATH,
    args: [
      "--use-gl=angle",
      "--use-angle=swiftshader",
      "--enable-unsafe-swiftshader",
    ],
  },
});
async function openSetup(page: import("@playwright/test").Page) {
  await page.goto("/experiments/shading_01?preview=research&mode=summary");
  await page.locator("#experimental-setup").scrollIntoViewIfNeeded();
  await expect(page.locator(".array-viewport")).toHaveAttribute(
    "data-renderer",
    "3d",
    { timeout: 20_000 },
  );
}
for (const width of [375, 768, 1280])
  test(`real 3D controls and layout at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.emulateMedia({ reducedMotion: "reduce" });
    await openSetup(page);
    const setup = page.locator("#experimental-setup");
    await expect(
      setup.getByText(/naturally different production levels/),
    ).toBeVisible();
    await page
      .getByRole("button", { name: "Documented shading", exact: true })
      .click();
    await expect(
      setup.getByRole("heading", {
        name: "One entire module was deliberately shaded.",
      }),
    ).toBeVisible();
    const module = setup.getByRole("button", {
      name: "Inverter 1, string 1, module 3",
      exact: true,
    });
    await module.focus();
    await page.keyboard.press("Enter");
    await expect(module).toHaveAttribute("aria-pressed", "true");
    await expect(setup.locator(".array-module-info")).toContainText(
      "representative fully shaded module",
    );
    await page
      .getByRole("button", { name: "Reference comparison", exact: true })
      .click();
    await expect(setup.locator(".array-explanation")).toContainText(
      "weather conditions",
    );
    await expect(setup.locator(".reference-active")).toContainText(
      "Inverter 2",
    );
    await expect(
      setup.getByRole("link", { name: /Review measured versus expected/ }),
    ).toHaveAttribute("href", "#performance-comparison");
    const canvas = setup.locator("canvas"),
      before = await canvas.screenshot();
    await page.getByRole("button", { name: "Zoom in", exact: true }).click();
    await expect(async () =>
      expect((await canvas.screenshot()).equals(before)).toBe(false),
    ).toPass();
    await page
      .getByRole("button", { name: "Reset camera", exact: true })
      .click();
    const box = await canvas.boundingBox();
    if (!box) throw new Error("No canvas bounds");
    await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
    await page.mouse.down();
    await page.mouse.move(
      box.x + box.width / 2 + 55,
      box.y + box.height / 2 - 20,
      { steps: 8 },
    );
    await page.mouse.up();
    await page
      .getByRole("button", { name: "Reset camera", exact: true })
      .click();
    await page
      .getByRole("button", { name: "Documented shading", exact: true })
      .click();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    expect(
      (
        await new AxeBuilder({ page })
          .include("#experimental-setup")
          .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
          .analyze()
      ).violations,
    ).toEqual([]);
    await mkdir("qa-screenshots", { recursive: true });
    await setup.screenshot({ path: `qa-screenshots/solar-${width}-3d.png` });
    await page
      .getByRole("button", { name: "Use 2D view", exact: true })
      .click();
    await expect(setup.locator(".array-viewport")).toHaveAttribute(
      "data-renderer",
      "2d",
    );
    await expect(setup.locator(".array-module-info")).toContainText(
      "Inverter 1, string 1, module 3",
    );
    await setup.screenshot({ path: `qa-screenshots/solar-${width}-2d.png` });
  });
test("WebGL unavailable leaves every explanation and keyboard module control available", async ({
  page,
}) => {
  await page.addInitScript(() => {
    const original = HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = function (
      this: HTMLCanvasElement,
      type: string,
      ...args: unknown[]
    ) {
      if (type.startsWith("webgl")) return null;
      return Reflect.apply(original, this, [type, ...args]);
    } as typeof original;
  });
  await page.goto("/method");
  const setup = page.locator("#experimental-setup");
  await setup.scrollIntoViewIfNeeded();
  await expect(setup.locator(".array-viewport")).toHaveAttribute(
    "data-renderer",
    "2d",
  );
  await expect(setup.getByText(/3D unavailable/)).toBeVisible();
  await setup
    .getByRole("button", { name: "Reference comparison", exact: true })
    .click();
  const module = setup.getByRole("button", {
    name: "Inverter 2, string 2, module 6",
    exact: true,
  });
  await module.focus();
  await page.keyboard.press("Space");
  await expect(module).toHaveAttribute("aria-pressed", "true");
  await expect(setup.locator(".array-module-info")).toContainText(
    "not the expected target output",
  );
  expect(
    (
      await new AxeBuilder({ page })
        .include("#experimental-setup")
        .withTags(["wcag2a", "wcag2aa"])
        .analyze()
    ).violations,
  ).toEqual([]);
});
test("canvas context loss switches to the complete fallback", async ({
  page,
}) => {
  await openSetup(page);
  await page
    .locator(".array-viewport canvas")
    .dispatchEvent("webglcontextlost");
  await expect(page.locator(".array-viewport")).toHaveAttribute(
    "data-renderer",
    "2d",
  );
  await page
    .getByRole("button", { name: "Documented shading", exact: true })
    .click();
  await expect(page.locator(".array-explanation")).toContainText("position");
});
test("landing defers the 3D runtime and report never requests it", async ({
  page,
}) => {
  const requests: string[] = [];
  page.on("request", (r) => requests.push(r.url()));
  await page.goto("/");
  await page.goto("/experiments/shading_01/report?preview=research");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  expect(
    requests.filter((u) => /SolarArrayScene|@react-three|three\.js/.test(u)),
  ).toEqual([]);
});
