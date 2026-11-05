import { expect, test } from "@playwright/test";
import { existsSync } from "node:fs";
import path from "node:path";
import type { RealProgram, RealProgramCatalog } from "../src/lib/types";

test("real database catalog supports all seven countries and filters without ranking", async ({ page, isMobile }, testInfo) => {
  test.skip(
    !existsSync(path.resolve(__dirname, "../../data/processed/real_university_programs.json")),
    "Optional private university export is not included in this checkout.",
  );
  const rankingCalls: string[] = [];
  page.on("request", (request) => {
    if (new URL(request.url()).pathname === "/api/recommendations") rankingCalls.push(request.url());
  });
  await page.goto("/explore");
  await expect(page.getByRole("heading", { name: "Demo Recommendations", exact: true })).toBeVisible();
  await expect(page.locator(".program-card")).toHaveCount(24);
  const response = page.waitForResponse((response) => new URL(response.url()).pathname === "/api/real-programs");
  await page.getByRole("button", { name: "Real Programs", exact: true }).click();
  expect((await response).status()).toBe(200);
  await expect(page.locator(".real-program-card")).toHaveCount(78);
  await expect(page.getByText("Not verified", { exact: true })).toHaveCount(78);
  await expect(page.getByText("Verified", { exact: true })).toHaveCount(0);
  await expect(page.getByRole("link", { name: "Official program page" })).toHaveCount(78);
  await expect(page.locator(".real-program-card").first().getByText("Information unavailable", { exact: true }).first()).toBeVisible();
  for (const [country, count] of [
    ["Belgium", 2], ["Canada", 3], ["France", 10], ["Germany", 10],
    ["Italy", 24], ["Netherlands", 4], ["United Kingdom", 25],
  ] as const) {
    await page.getByRole("combobox", { name: "Real country", exact: true }).selectOption(country);
    await expect(page.locator(".real-program-card")).toHaveCount(count);
  }
  await page.getByRole("combobox", { name: "Real university", exact: true }).selectOption("University of Glasgow");
  await page.getByRole("combobox", { name: "Real study field", exact: true }).selectOption("Engineering");
  await page.getByRole("textbox", { name: "Search real programs" }).fill("aerospace");
  await expect(page.locator(".real-program-card")).toHaveCount(1);
  const feeCard = page.locator(".real-program-card").first();
  await feeCard.getByText("View published tuition information", { exact: true }).click();
  await expect(feeCard).toContainText("Home & RUK");
  await expect(feeCard).toContainText("International & EU");
  await expect(feeCard).toContainText("GBP");
  await page.getByRole("button", { name: "Clear real-program filters" }).click();
  await page.getByRole("combobox", { name: "Real country", exact: true }).selectOption("France");
  await expect(page.getByText("Expired deadline", { exact: true })).toHaveCount(10);
  await page.getByRole("textbox", { name: "Search real programs" }).fill("M2 Artificial Intelligence");
  await expect(page.locator(".real-program-card")).toHaveCount(1);
  await expect(page.getByRole("link", { name: "Official program page" })).toHaveAttribute("href", /^https:\/\/www\.universite-paris-saclay\.fr\//);
  await page.screenshot({ path: testInfo.outputPath("real-programs.png"), fullPage: true });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  if (isMobile) {
    await page.setViewportSize({ width: 844, height: 390 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  }
  const cachedApi = await page.evaluate(async () => {
    for (const name of await caches.keys()) {
      const cache = await caches.open(name);
      if ((await cache.keys()).some((request) => new URL(request.url).pathname.startsWith("/api/"))) return true;
    }
    return false;
  });
  expect(cachedApi).toBe(false);
  expect(rankingCalls).toEqual([]);
  await page.getByRole("button", { name: "Demo Recommendations", exact: true }).click();
  await expect(page.locator(".program-card")).toHaveCount(24);
  await expect(page.locator(".real-program-card")).toHaveCount(0);
});

// UI fixtures below are deliberately fictitious, never written to staging or university datasets.
function example(overrides: Partial<RealProgram>): RealProgram {
  return {
    id: "test-only", university_name: "Test University", program_name: "Test Master",
    country: "Canada", city: null, official_university_url: null, official_program_url: null,
    degree_type: null, study_area: null, teaching_language: null, teaching_languages: null,
    tuition_fees: null, currency: null, academic_year: null, duration: null, duration_months: null,
    description: null, admission_requirements: null, english_language_requirements: null,
    application_deadline: null, application_opening_date: null, application_deadline_date: null,
    retrieval_date: "2026-11-02T00:00:00Z", verification_status: "needs_review",
    deadline_status: "unknown", synthetic: false, recommendation_eligible: false,
    ...overrides,
  };
}
function catalog(programs: RealProgram[]): RealProgramCatalog {
  return {
    programs, total: programs.length, count: programs.length,
    countries: ["Canada"], universities: ["Test University"], study_areas: [],
    as_of_date: "2026-11-05", recommendation_eligible: false,
  };
}

test("nullable values and explicit past, future, today and undated deadlines are distinct", async ({ page }) => {
  await page.route("**/api/real-programs", (route) => route.fulfill({
    json: catalog([
      example({ id: "expired", program_name: "Past date fixture", application_deadline_date: "2020-01-01", deadline_status: "expired" }),
      example({ id: "future", program_name: "Future date fixture", application_deadline_date: "2099-01-01", deadline_status: "upcoming" }),
      example({ id: "today", program_name: "Today date fixture", application_deadline_date: "2026-11-05", deadline_status: "today" }),
      example({ id: "undated", program_name: "Undated fixture", application_deadline: "December 15 (year not established)" }),
    ]),
  }));
  await page.goto("/explore");
  await page.getByRole("button", { name: "Real Programs", exact: true }).click();
  await expect(page.getByText("Not verified", { exact: true })).toHaveCount(4);
  await expect(page.getByText("Expired deadline", { exact: true })).toHaveCount(1);
  await expect(page.getByText("Future deadline", { exact: true })).toHaveCount(1);
  await expect(page.getByText("Deadline today", { exact: true })).toHaveCount(1);
  const undated = page.locator(".real-program-card").filter({ hasText: "Undated fixture" });
  await expect(undated.locator(".deadline-badge")).toHaveCount(0);
  await expect(undated.getByText("Information unavailable", { exact: true }).first()).toBeVisible();
  await undated.getByText("Requirements and source details", { exact: true }).click();
  await expect(undated).toContainText("December 15 (year not established)");
  await expect(undated.getByRole("link")).toHaveCount(0);
  await expect(page.getByRole("button", { name: /rank|recommend/i })).toHaveCount(1); // Demo mode button only.
});

test("real catalog errors retry to an honest empty state and demo mode still works", async ({ page }) => {
  let attempts = 0;
  await page.route("**/api/real-programs", (route) => {
    attempts++;
    return attempts === 1 ? route.fulfill({
      status: 503, json: { error: { code: "database_unavailable", message: "Real program database is unavailable." } },
    }) : route.fulfill({ json: catalog([]) });
  });
  await page.goto("/explore");
  await page.getByRole("button", { name: "Real Programs", exact: true }).click();
  await expect(page.getByRole("region", { name: "Real Programs", exact: true }).getByRole("alert"))
    .toContainText("Real program database is unavailable.");
  await page.getByRole("button", { name: "Try again" }).click();
  await expect(page.getByRole("heading", { name: "No real programs are available yet." })).toBeVisible();
  await expect(page.locator(".real-program-card")).toHaveCount(0);
  await page.getByRole("button", { name: "Demo Recommendations", exact: true }).click();
  await expect(page.locator(".program-card")).toHaveCount(24);
});
