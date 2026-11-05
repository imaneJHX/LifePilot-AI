import { expect, test } from "@playwright/test";

test("build a profile, rank programs, compare options, and handle offline chat", async ({
  page,
}, testInfo) => {
  const browserErrors: string[] = [];
  page.on("pageerror", (error) => browserErrors.push(error.message));
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: /Your next chapter/ }).first(),
  ).toBeVisible();
  await expect(page.locator(".hero-visual")).toHaveCSS("opacity", "1");
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: testInfo.outputPath("landing.png"),
    fullPage: true,
  });
  await page.getByRole("link", { name: "Find my direction" }).click();
  await page.getByLabel("Your first name").fill("Taylor");
  await page.getByLabel("Field of interest").selectOption("Data Science");
  await page.getByLabel("GPA", { exact: false }).fill("3.5");
  await page.getByLabel("Annual budget", { exact: false }).fill("15000");
  await page.getByLabel("Germany", { exact: true }).check();
  await page.getByLabel("France", { exact: true }).check();
  await page.getByRole("button", { name: "Find my direction" }).click();
  await expect(
    page.getByRole("heading", { name: "A little more clarity, Taylor." }),
  ).toBeVisible();
  await expect(page.locator(".rank-card")).toHaveCount(2);
  await page.evaluate(() => window.scrollTo({ top: 0, behavior: "instant" }));
  await expect(page.locator(".rank-explanation")).toContainText(
    "does not measure eligibility",
  );
  await expect(page.locator(".rank-card").first()).toContainText("below cap");
  await page.getByRole("button", { name: "Adjust ranking priorities" }).click();
  await page.getByLabel("Affordability", { exact: false }).fill("90");
  await page.getByRole("button", { name: "Recalculate" }).click();
  await expect(page.locator(".rank-card")).toHaveCount(2);
  await page.evaluate(() => window.scrollTo({ top: 0, behavior: "instant" }));
  await page.screenshot({
    path: testInfo.outputPath("dashboard.png"),
    fullPage: true,
  });
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "A little more clarity, Taylor." }),
  ).toBeVisible();

  await page.goto("/explore");
  await expect(page.locator(".program-card")).toHaveCount(24);
  await page
    .getByRole("combobox", { name: "Study area", exact: true })
    .selectOption("Data Science");
  await expect(page.locator(".program-card")).toHaveCount(6);
  await page.getByRole("button", { name: "View details" }).first().click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.getByRole("button", { name: "Close program details" }).click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await page
    .locator(".program-card")
    .nth(0)
    .getByRole("button", { name: "Compare", exact: true })
    .click();
  await page
    .locator(".program-card")
    .nth(1)
    .getByRole("button", { name: "Compare", exact: true })
    .click();
  await page.getByRole("button", { name: "Compare side by side" }).click();
  await expect(page.getByRole("table")).toBeVisible();
  await expect(page.getByRole("table")).toContainText("Annual total");

  // Inject a deterministic offline response; no model download is needed for this test.
  await page.route("**/api/chat", (route) =>
    route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({
        error: {
          code: "ollama_unavailable",
          message:
            "Cannot connect to Ollama. Start Ollama and pull the configured model.",
        },
      }),
    }),
  );
  await page.goto("/assistant");
  await page
    .getByLabel("Message LifePilot")
    .fill("Help me compare my options.");
  await page.getByRole("button", { name: "Send message" }).click();
  await expect(
    page.getByRole("log", { name: "Conversation" }).getByRole("alert"),
  ).toContainText("Cannot connect to Ollama");
  await expect(page.getByRole("button", { name: "Try again" })).toBeEnabled();
  await page.route("**/api/chat", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        message: {
          role: "assistant",
          content:
            "Compare annual cost and academic alignment, then verify official requirements.",
        },
        model: "test-model",
        synthetic_context: true,
      }),
    }),
  );
  await page.getByRole("button", { name: "Try again" }).click();
  await expect(page.locator(".chat-message.assistant")).toContainText(
    "Compare annual cost",
  );
  await expect(page.locator(".chat-message.user")).toHaveCount(1);
  await page.getByRole("button", { name: "New conversation" }).click();
  await expect(page.locator(".chat-message")).toHaveCount(0);
  expect(browserErrors).toEqual([]);
});

test("empty recommendations, theme persistence, and mobile layout", async ({
  page,
}, testInfo) => {
  await page.goto("/profile");
  await page.getByRole("button", { name: "Use sample profile" }).click();
  await page.getByLabel("Annual budget", { exact: false }).fill("1000");
  await page.getByRole("button", { name: "Find my direction" }).click();
  await expect(
    page.getByRole("heading", { name: "Let’s widen the horizon." }),
  ).toBeVisible();
  const toggle = page.getByRole("button", { name: /Switch to .* mode/ });
  await toggle.click();
  const theme = await page.locator("html").getAttribute("data-theme");
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", theme!);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: testInfo.outputPath("empty-and-theme.png"),
    fullPage: true,
  });
});
