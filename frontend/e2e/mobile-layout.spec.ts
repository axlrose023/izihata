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

test("catalog refresh keeps scroll position and card geometry", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/catalog");
  const card = page.locator(".product-card").first();
  await expect(card).toBeVisible();
  await page.evaluate(() => window.scrollTo(0, 180));
  const before = await card.boundingBox();
  const scroll = await page.evaluate(() => window.scrollY);
  let release!: () => void;
  const pending = new Promise<void>((done) => {
    release = done;
  });
  await page.route("**/api/v1/catalog/products?**", async (route) => {
    await pending;
    await route.continue();
  });
  try {
    await page
      .getByLabel("Сортування", { exact: true })
      .selectOption("price_asc");
    await expect(page.locator(".catalog-results")).toHaveAttribute(
      "aria-busy",
      "true",
    );
    expect(await page.evaluate(() => window.scrollY)).toBe(scroll);
    expect((await card.boundingBox())!.y).toBeCloseTo(before!.y, 0);
    await expectDocumentFits(page);
  } finally {
    release();
  }
  await expect(page.locator(".catalog-results")).toHaveAttribute(
    "aria-busy",
    "false",
  );
  expect(await page.evaluate(() => window.scrollY)).toBe(scroll);
});

for (const overlay of ["menu", "cart"] as const) {
  test(`cold ${overlay} overlay does not resize the header and can be cancelled`, async ({
    page,
  }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    let release!: () => void;
    const pending = new Promise<void>((done) => {
      release = done;
    });
    const module =
      overlay === "menu"
        ? /(?:\/assets\/site-sidebar-[^/]+\.js|\/src\/widgets\/site-sidebar\.tsx)(?:\?|$)/
        : /(?:\/assets\/cart-drawer-[^/]+\.js|\/src\/modules\/cart\/components\/cart-drawer\.tsx)(?:\?|$)/;
    await page.route(module, async (route) => {
      await pending;
      await route.continue();
    });
    await page.goto("/catalog");
    const header = page.locator(".site-header");
    await expect(header).toBeVisible();
    const before = await header.boundingBox();
    try {
      await page
        .getByRole("button", {
          name: overlay === "menu" ? "Відкрити меню" : "Кошик: 0",
          exact: true,
        })
        .click();
      await expect(page.locator(".overlay-loading")).toBeVisible();
      expect((await header.boundingBox())!.height).toBe(before!.height);
      await expectDocumentFits(page);
      await page.keyboard.press("Escape");
      await expect(page.locator(".overlay-loading")).toHaveCount(0);
      expect(await page.evaluate(() => document.body.style.overflow)).toBe("");
    } finally {
      release();
    }
  });
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
