import { expect, test } from "@playwright/test";

test("export calls FastAPI directly and restores a saved profile after navigation", async ({ page }) => {
  const requests: string[] = [];
  const missingNavigationData: string[] = [];
  page.on("request", (request) => {
    if (new URL(request.url()).pathname.startsWith("/api/")) requests.push(request.url());
  });
  page.on("response", (response) => {
    if (response.url().includes("__next.") && response.status() >= 400) {
      missingNavigationData.push(response.url());
    }
  });
  await page.goto("/profile/");
  // The sidebar is hidden on phones, but its active-route state must stay correct.
  await expect(page.locator(".sidebar nav a").filter({ hasText: "My profile" }))
    .toHaveAttribute("aria-current", "page");
  const health = await page.evaluate(async () => {
    const response = await fetch("http://127.0.0.1:8001/api/health", {
      headers: { "Content-Type": "application/json" },
    });
    return { status: response.status, body: await response.json() };
  });
  expect(health.status).toBe(200);
  expect(health.body.status).toBe("ok");
  await page.getByRole("button", { name: "Use sample profile" }).click();
  await page.getByRole("button", { name: "Find my direction" }).click();
  await expect(page.locator(".rank-card").first()).toBeVisible();
  await page.reload();
  await expect(page.locator(".rank-card").first()).toBeVisible();
  await page.goto("/explore/");
  await expect(page.locator(".program-card")).toHaveCount(24);
  expect(requests.some((url) => url.endsWith("/api/profile"))).toBe(true);
  expect(requests.some((url) => new URL(url).pathname.startsWith("/api/profile/"))).toBe(true);
  expect(requests.some((url) => url.endsWith("/api/recommendations"))).toBe(true);
  expect(requests.some((url) => url.endsWith("/api/universities"))).toBe(true);
  expect(requests.every((url) => new URL(url).origin === "http://127.0.0.1:8001")).toBe(true);
  expect(missingNavigationData).toEqual([]);
});
