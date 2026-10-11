import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/integration",
  fullyParallel: false,
  workers: 1,
  timeout: 60_000,
  expect: { timeout: 15_000 },
  use: {
    baseURL: "http://127.0.0.1:4173",
    channel: process.env.PLAYWRIGHT_CHANNEL || "chrome",
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
    launchOptions: {
      args: [
        "--use-gl=angle",
        "--use-angle=swiftshader",
        "--enable-unsafe-swiftshader",
      ],
    },
  },
  webServer: [
    {
      command:
        "python -m backend.local_release_server --artifact artifacts/releases/v0.2.0/shading_01/approved/review_shading_01.json --schema-sha256 51001cac97423b454afac7b98ee733306666fe52e3ba22f5cb422ce987c461bd",
      cwd: "..",
      url: "http://127.0.0.1:8000/api/v1/health",
      reuseExistingServer: false,
    },
    {
      command: "npm run preview -- --host 127.0.0.1 --port 4173 --strictPort",
      url: "http://127.0.0.1:4173",
      reuseExistingServer: !process.env.CI,
    },
  ],
});
