import { expect, test, type Page } from "@playwright/test";

async function expectDocumentFits(page: Page) {
  await expect
    .poll(() =>
      page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth + 1,
      ),
    )
    .toBe(true);
  expect(await page.evaluate(() => window.scrollX)).toBe(0);
}

for (const width of [320, 360, 390, 414, 768, 820, 1024]) {
  test(`storefront fits a ${width}px viewport`, async ({ page, request }) => {
    await page.setViewportSize({ width, height: 844 });
    const products = await request.get(
      "/api/v1/catalog/products?page_size=1&include_facets=false",
    );
    expect(products.ok()).toBe(true);
    const product = (await products.json()).items[0] as { slug: string };

    for (const path of [
      "/",
      "/catalog",
      `/products/${product.slug}`,
      "/brands",
      "/account/login",
      "/favorites",
      "/compare",
      "/checkout",
      "/advisors",
      "/custom-boards",
    ]) {
      await page.goto(path);
      await expect(
        page.getByRole("heading", { level: 1 }).first(),
      ).toBeVisible();
      await expectDocumentFits(page);

      if (path === "/") {
        const tabs = page.getByRole("tablist");
        await tabs
          .getByRole("tab", { name: "Акції", exact: true })
          .evaluate((element) => element.scrollIntoView({ block: "nearest" }));
        await expectDocumentFits(page);
      }
      if (path === "/custom-boards") {
        await expect(page.locator(".board-builder__schematic")).toBeVisible();
        for (const panel of await page
          .locator(".board-builder__right > section")
          .all()) {
          const rect = await panel.boundingBox();
          expect(rect).not.toBeNull();
          expect(rect!.x).toBeGreaterThanOrEqual(0);
          expect(rect!.x + rect!.width).toBeLessThanOrEqual(width + 1);
        }
      }
      if (path === "/account/login" && width <= 820) {
        for (const input of await page
          .locator("input:not([type=hidden])")
          .all()) {
          expect(
            await input.evaluate((element) =>
              Number.parseFloat(getComputedStyle(element).fontSize),
            ),
          ).toBeGreaterThanOrEqual(16);
        }
      }
    }
  });
}
