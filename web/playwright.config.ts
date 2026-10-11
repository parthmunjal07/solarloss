import { defineConfig } from "@playwright/test";
const devPort = process.env.WEB_TEST_PORT || "5173";
const previewPort = process.env.WEB_PREVIEW_PORT || "4173";
export default defineConfig({
  testDir: "./tests/browser",
  fullyParallel: false,
  workers: 1,
  timeout: 30_000,
  use: {
    baseURL: `http://127.0.0.1:${devPort}`,
    channel: process.env.PLAYWRIGHT_CHANNEL || "chrome",
    launchOptions: { executablePath: process.env.PLAYWRIGHT_EXECUTABLE_PATH },
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
  },
  webServer: [
    {
      command: `npm run dev -- --port ${devPort} --strictPort`,
      url: `http://127.0.0.1:${devPort}`,
      reuseExistingServer: !process.env.CI,
    },
    {
      command: `npm run preview -- --host 127.0.0.1 --port ${previewPort} --strictPort`,
      url: `http://127.0.0.1:${previewPort}`,
      reuseExistingServer: !process.env.CI,
    },
  ],
});
