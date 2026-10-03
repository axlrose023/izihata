import { expect, test } from "@playwright/test";

const catalogModule =
  /(?:\/assets\/catalog-page-[^/]+\.js|\/src\/pages\/store\/catalog-page\.tsx)(?:\?|$)/;

test("link intent prepares its route without fetching the next page's products", async ({
  page,
}) => {
  await page.goto("/");
  await page.waitForLoadState("networkidle");
  await expect(page.locator(".hero h1")).toBeVisible();
  const originalUrl = page.url();
  const productRequests: string[] = [];
  page.on("request", (request) => {
    if (new URL(request.url()).pathname === "/api/v1/catalog/products") {
      productRequests.push(request.url());
    }
  });
  const catalogReady = page.waitForResponse((response) =>
    catalogModule.test(response.url()),
  );
  let link = page.locator(".catalog-nav__primary");
  if ((page.viewportSize()?.width ?? 1000) <= 820) {
    await page.getByRole("button", { name: "Відкрити меню" }).click();
    const menu = page.getByRole("dialog", { name: "Головне меню" });
    await menu.getByRole("button", { name: "Каталог товарів" }).click();
    link = menu.getByRole("link", { name: "Усі товари", exact: true });
  }
  await link.focus();
  await catalogReady;
  await page.waitForLoadState("networkidle");
  expect(page.url()).toBe(originalUrl);
  expect(productRequests).toEqual([]);
  // Navigation must still work if a fresh module request would fail.
  await page.route(catalogModule, (route) => route.abort());
  await link.click();
  await expect(page).toHaveURL(/\/catalog$/);
  await expect(page.locator(".product-card").first()).toBeVisible();
});
