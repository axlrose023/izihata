import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";

async function expectNoAccessibilityViolations(page: Page) {
  const result = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .analyze();

  expect(result.violations, JSON.stringify(result.violations, null, 2)).toEqual(
    [],
  );
}

test("key public and staff pages meet WCAG A/AA checks", async ({ page }) => {
  for (const path of ["/", "/catalog", "/admin/login"]) {
    await page.goto(path);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    await expectNoAccessibilityViolations(page);
  }
});

test("lead dialog meets WCAG A/AA checks", async ({ page }) => {
  await page.goto("/catalog");
  if ((page.viewportSize()?.width ?? 1000) <= 820) {
    await page.locator(".product-card__link-overlay").first().click();
    await page.getByRole("button", { name: "Купити в один клік" }).click();
  } else {
    await page.getByRole("button", { name: "1 клік" }).first().click();
  }
  await expect(page.getByRole("dialog")).toBeVisible();
  await expectNoAccessibilityViolations(page);
});

test("signed-in admin screens meet WCAG A/AA checks", async ({ page }) => {
  const username = process.env.ADMIN_USERNAME;
  const password = process.env.ADMIN_PASSWORD;
  test.skip(!username || !password, "Admin credentials are not configured");

  await page.goto("/admin/login");
  await page.getByLabel("Логін").fill(username!);
  await page.getByLabel("Пароль").fill(password!);
  await page.getByRole("button", { name: "Увійти" }).click();
  await expect(page).toHaveURL(/\/admin$/);

  // The tables, badges and the dark rail only render once signed in, so the
  // public sweep above never reaches them.
  for (const path of [
    "/admin",
    "/admin/products",
    "/admin/orders",
    "/admin/leads",
    "/admin/reviews",
    "/admin/brands",
    "/admin/companies",
  ]) {
    await page.goto(path);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    await expectNoAccessibilityViolations(page);
  }
});
