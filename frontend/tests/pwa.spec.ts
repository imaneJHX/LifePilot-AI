import { expect, test, type Page } from "@playwright/test";

async function controlled(page: Page) {
  await page.goto("/");
  await page.evaluate(async () => {
    await navigator.serviceWorker.ready;
    if (!navigator.serviceWorker.controller) {
      await new Promise<void>((resolve) => navigator.serviceWorker.addEventListener(
        "controllerchange", () => resolve(), { once: true },
      ));
    }
  });
}

test("PWA metadata, icons and worker headers are available", async ({ page, request }) => {
  await page.goto("/");
  await expect(page.locator('link[rel="manifest"]')).toHaveAttribute("href", "/manifest.webmanifest");
  await expect(page.locator('meta[name="apple-mobile-web-app-capable"]')).toHaveAttribute("content", "yes");
  await expect(page.locator('meta[name="apple-mobile-web-app-title"]')).toHaveAttribute("content", "LifePilot AI");
  await expect(page.locator('meta[name="viewport"]')).toHaveAttribute("content", /viewport-fit=cover/);
  const manifest = await (await request.get("/manifest.webmanifest")).json();
  expect(manifest.display).toBe("standalone");
  expect(manifest.start_url).toBe("/");
  for (const [url, size] of [
    ["/icons/icon-192.png", 192], ["/icons/icon-512.png", 512],
    ["/icons/icon-maskable-512.png", 512], ["/icons/apple-touch-icon.png", 180],
  ] as const) {
    const icon = await request.get(url);
    expect(icon.ok()).toBe(true);
    const bytes = await icon.body();
    expect(bytes.readUInt32BE(16)).toBe(size);
    expect(bytes.readUInt32BE(20)).toBe(size);
  }
  const worker = await request.get("/sw.js");
  expect(worker.headers()["cache-control"]).toContain("no-store");
  expect(worker.headers()["content-type"]).toContain("javascript");
  expect(worker.headers()["service-worker-allowed"]).toBe("/");
});

test("offline navigation shows a generic fallback without caching student information", async ({ page, context }) => {
  await controlled(page);
  await page.goto("/profile");
  await page.getByRole("button", { name: "Use sample profile" }).click();
  await page.getByLabel("Your first name").fill("Private PWA Student");
  await page.getByRole("button", { name: "Find my direction" }).click();
  await expect(page.locator(".rank-card").first()).toBeVisible();
  await page.goto("/assistant");
  const networkResponses = await page.evaluate(async () => {
    const responses = await Promise.all([
      fetch("/api/health", { cache: "no-store" }),
      fetch("/api/recommendations", {
        method: "POST", headers: { "Content-Type": "application/json" }, body: "{}",
      }),
      fetch("/api/chat", {
        method: "POST", headers: { "Content-Type": "application/json" }, body: "{}",
      }),
    ]);
    return responses.map((response) => ({ status: response.status, cacheControl: response.headers.get("cache-control") }));
  });
  expect(networkResponses.map((response) => response.status)).toEqual([200, 422, 422]);
  expect(networkResponses.every((response) => response.cacheControl?.includes("no-store"))).toBe(true);
  const cached = await page.evaluate(async () => {
    const urls: string[] = [];
    const bodies: string[] = [];
    for (const name of await caches.keys()) {
      const cache = await caches.open(name);
      for (const request of await cache.keys()) {
        urls.push(new URL(request.url).pathname);
        if (!request.url.endsWith(".png")) bodies.push(await (await cache.match(request))!.text());
      }
    }
    return { urls, bodies: bodies.join("\n") };
  });
  expect(cached.urls.sort()).toEqual([
    "/offline.html", "/offline.css", "/manifest.webmanifest",
    "/icons/icon-192.png", "/icons/icon-512.png", "/icons/icon-maskable-512.png", "/icons/apple-touch-icon.png",
  ].sort());
  expect(cached.bodies).not.toContain("Private PWA Student");
  await context.setOffline(true);
  await page.goto("/dashboard");
  await expect(page.getByRole("heading", { name: "You’re offline." })).toBeVisible();
  await expect(page.getByText("Private PWA Student")).toHaveCount(0);
  expect((await page.getByRole("link", { name: "Try again" }).boundingBox())!.height).toBeGreaterThanOrEqual(44);
  const apiFailsOffline = await page.evaluate(async () => {
    try { await fetch("/api/health", { cache: "no-store" }); return false; }
    catch { return true; }
  });
  expect(apiFailsOffline).toBe(true);
  await context.setOffline(false);
  await page.getByRole("link", { name: "Try again" }).click();
  await expect(page.getByRole("heading", { name: /Your next chapter/ }).first()).toBeVisible();
});

test("phone controls, dashboard, comparison and themes remain usable", async ({ page, isMobile }) => {
  await page.goto("/profile");
  const input = page.getByLabel("Your first name");
  if (isMobile) {
    await expect(input).toHaveCSS("font-size", "16px");
    const links = page.getByRole("navigation", { name: "Mobile navigation" }).getByRole("link");
    await expect(links).toHaveCount(4);
    for (const link of await links.all()) expect((await link.boundingBox())!.height).toBeGreaterThanOrEqual(44);
    expect((await page.getByRole("button", { name: /Switch to .* mode/ }).boundingBox())!.height).toBeGreaterThanOrEqual(44);
  }
  await page.getByRole("button", { name: "Use sample profile" }).click();
  await page.getByRole("button", { name: "Find my direction" }).click();
  await expect(page.locator(".rank-card").first()).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.getByRole("button", { name: /Switch to .* mode/ }).click();
  const theme = await page.locator("html").getAttribute("data-theme");
  const expectedColor = theme === "dark" ? "#121b23" : "#f6f7f9";
  expect(await page.locator('meta[name="theme-color"]').evaluateAll((nodes) => nodes.map((node) => node.getAttribute("content"))))
    .toEqual([expectedColor, expectedColor]);
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", theme!);
  await page.goto("/explore");
  await expect(page.locator(".program-card")).toHaveCount(24);
  for (let index = 0; index < 3; index++) {
    await page.locator(".program-card").nth(index).getByRole("button", { name: "Compare", exact: true }).click();
  }
  await page.getByRole("button", { name: "Compare side by side" }).click();
  const comparison = page.getByRole("region", { name: "Program comparison" });
  await expect(comparison.getByRole("table")).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  if (isMobile) {
    await expect(page.getByText("Swipe across to compare every program.")).toBeVisible();
    const moved = await comparison.evaluate((element) => {
      element.scrollLeft = element.scrollWidth;
      return element.scrollLeft > 0;
    });
    expect(moved).toBe(true);
    await expect(comparison.locator("tbody th").first()).toHaveCSS("position", "sticky");
    await page.setViewportSize({ width: 844, height: 390 });
    await expect(page.getByRole("navigation", { name: "Mobile navigation" })).toBeVisible();
    await expect(page.locator(".sidebar")).toBeHidden();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  }
});
