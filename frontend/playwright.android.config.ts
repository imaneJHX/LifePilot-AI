import { defineConfig } from "@playwright/test";
import path from "node:path";
import website from "./playwright.config";

const python = path.resolve(
  "..", ".venv", process.platform === "win32" ? "Scripts/python.exe" : "bin/python",
);

// Build with NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8001 using CAPACITOR_BUILD=true
// before running. This tests the same export through a static server, with NO proxy.
export default defineConfig({
  ...website,
  testIgnore: [],
  testMatch: ["journey.spec.ts", "android-export.spec.ts", "real-programs.spec.ts"],
  use: { ...website.use, baseURL: "http://127.0.0.1:3001" },
  webServer: [
    {
      command: `"${python}" ../scripts/serve_test_api.py --port 8001 --database android-e2e.db`,
      env: {
        DATABASE_URL: `sqlite:///${path.resolve("..", "android-e2e.db").replaceAll("\\", "/")}`,
        CORS_ORIGINS: '["http://127.0.0.1:3001","https://localhost"]',
      },
      url: "http://127.0.0.1:8001/api/health",
      reuseExistingServer: false,
      timeout: 60000,
    },
    {
      command: `"${python}" -m http.server 3001 --bind 127.0.0.1 --directory out`,
      stderr: "ignore",
      url: "http://127.0.0.1:3001",
      reuseExistingServer: false,
      timeout: 60000,
    },
  ],
});
