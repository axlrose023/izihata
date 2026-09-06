import { expect, test as setup } from "@playwright/test";

// One staff login for the whole suite: /auth/login is rate limited per IP,
// and every test shares the runner's address.
export const ADMIN_STATE = "e2e/.auth/admin.json";

setup("authenticate as staff", async ({ page }) => {
  const username = process.env.ADMIN_USERNAME;
  const password = process.env.ADMIN_PASSWORD;
  if (!username || !password) {
    // Admin specs load this file unconditionally, so it has to exist even when
    // there are no credentials to sign in with — they skip themselves instead.
    await page.context().storageState({ path: ADMIN_STATE });
    setup.skip(true, "Admin credentials are not configured");
    return;
  }

  await page.goto("/admin/login");
  await page.getByLabel("Логін").fill(username!);
  await page.getByLabel("Пароль").fill(password!);
  await page.getByRole("button", { name: "Увійти" }).click();
  await expect(page).toHaveURL(/\/admin$/);
  await expect(page.locator(".metric-card").first()).toBeVisible();

  await page.context().storageState({ path: ADMIN_STATE });
});
