import { defineConfig } from "@playwright/test";
import website from "./playwright.config";

export default defineConfig({
  ...website,
  testMatch: "pwa.spec.ts",
  webServer: Array.isArray(website.webServer)
    ? website.webServer.map((server) => ({ ...server, reuseExistingServer: false }))
    : website.webServer,
});
