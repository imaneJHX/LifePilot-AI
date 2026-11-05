import { defineConfig, devices } from "@playwright/test";
import path from "node:path";

const python = path.resolve(
  "..",
  ".venv",
  process.platform === "win32" ? "Scripts/python.exe" : "bin/python",
);
const webPort = Number(process.env.PLAYWRIGHT_WEB_PORT ?? 3000);
const apiPort = Number(process.env.PLAYWRIGHT_API_PORT ?? 8000);

export default defineConfig({
  testDir: "./tests",
  testIgnore: "**/android-export.spec.ts",
  fullyParallel: false,
  workers: 1,
  timeout: 45000,
  expect: { timeout: 15000 },
  reporter: "list",
  use: {
    baseURL: `http://127.0.0.1:${webPort}`,
    channel:
      process.env.PLAYWRIGHT_CHANNEL ??
      (process.platform === "win32" ? "msedge" : undefined),
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "desktop",
      use: {
        ...devices["Desktop Chrome"],
        viewport: { width: 1440, height: 1000 },
      },
    },
    {
      name: "mobile",
      use: { ...devices["iPhone 13"], defaultBrowserType: "chromium" },
    },
  ],
  webServer: [
    {
      command: `"${python}" ../scripts/serve_test_api.py --port ${apiPort} --database e2e.db`,
      env: {
        DATABASE_URL: `sqlite:///${path.resolve("..", "e2e.db").replaceAll("\\", "/")}`,
      },
      url: `http://127.0.0.1:${apiPort}/api/health`,
      reuseExistingServer: !process.env.CI,
      timeout: 60000,
    },
    {
      command: `npm run start -- --port ${webPort}`,
      url: `http://127.0.0.1:${webPort}`,
      reuseExistingServer: !process.env.CI,
      timeout: 60000,
    },
  ],
});
