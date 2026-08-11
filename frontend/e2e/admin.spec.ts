import { expect, test } from "@playwright/test";

test("staff can log in and load every management module", async ({ page }) => {
  const username = process.env.ADMIN_USERNAME;
  const password = process.env.ADMIN_PASSWORD;
  test.skip(!username || !password, "Admin credentials are not configured");
  const authRequests: string[] = [];
  page.on("request", (request) => {
    if (request.url().includes("/api/v1/auth/")) {
      authRequests.push(new URL(request.url()).pathname);
    }
  });

  await page.goto("/admin/login");
  await page.getByLabel("Логін").fill(username!);
  await page.getByLabel("Пароль").fill(password!);
  await page.getByRole("button", { name: "Увійти" }).click();
  await expect(page).toHaveURL(/\/admin$/);
  await expect(page.locator(".metric-card").first()).toBeVisible();
  expect(authRequests).toContain("/api/v1/auth/refresh");
  expect(authRequests).toContain("/api/v1/auth/login");
  expect(authRequests.every((path) => !path.includes("/session/"))).toBe(true);

  for (const [path, heading] of [
    ["/admin/products", "Товари"],
    ["/admin/orders", "Замовлення"],
    ["/admin/leads", "Звернення"],
  ] as const) {
    await page.goto(path);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(heading);
    await expect(page.locator(".admin-table")).toBeVisible();
  }
});
