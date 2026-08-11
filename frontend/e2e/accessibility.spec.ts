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
  await page.goto("/");
  await page.getByRole("button", { name: "Потрібна консультація" }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await expectNoAccessibilityViolations(page);
});
