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

test("font configuration prevents late replacement of painted text", async ({
  page,
}) => {
  await page.goto("/catalog");
  const href = await page
    .locator('link[href*="fonts.googleapis.com/css2"]')
    .getAttribute("href");
  expect(new URL(href!).searchParams.get("display")).toBe("optional");
});

test("catalog breadcrumbs open the category directory", async ({
  page,
  request,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const products = await request.get(
    "/api/v1/catalog/products?page_size=1&include_facets=false",
  );
  const categoriesResponse = await request.get("/api/v1/catalog/categories");
  const slug = (await products.json()).items[0].slug as string;
  const categories = (await categoriesResponse.json()) as Array<unknown>;
  await page.goto(`/products/${slug}`);
  await page
    .locator(".breadcrumbs")
    .getByRole("link", { name: "Каталог", exact: true })
    .click();
  await expect(page).toHaveURL(/\/catalog\/categories$/);
  await expect(
    page.getByRole("heading", { name: "Каталог товарів", exact: true }),
  ).toBeVisible();
  await expect(page.locator(".category-card").first()).toBeVisible();
  await expect(page.locator(".category-card")).toHaveCount(
    Math.min(categories.length, 6),
  );
  if (categories.length > 6) {
    const showAll = page.locator(".show-all-button");
    await expect(showAll).toHaveText(
      `Показати всі напрями (${categories.length})`,
    );
    await showAll.click();
    await expect(page.locator(".category-card")).toHaveCount(categories.length);
    await expect(showAll).toHaveText("Згорнути");
  }
  await expectDocumentFits(page);
});

test("home shows the collapsible category directory before catalog products", async ({
  page,
  request,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const categoriesResponse = await request.get("/api/v1/catalog/categories");
  const categories = (await categoriesResponse.json()) as Array<unknown>;
  await page.goto("/");
  const directory = page.locator(".home-category-directory");
  await expect(directory.locator(".category-card").first()).toBeVisible();
  await expect(directory.locator(".category-card")).toHaveCount(
    Math.min(categories.length, 6),
  );
  expect(
    await directory.evaluate((element) => {
      const directions = document.querySelector("#catalog");
      const products = document.querySelector(".popular-products");
      return Boolean(
        directions &&
        products &&
        directions.compareDocumentPosition(element) &
          Node.DOCUMENT_POSITION_FOLLOWING &&
        element.compareDocumentPosition(products) &
          Node.DOCUMENT_POSITION_FOLLOWING,
      );
    }),
  ).toBe(true);
  if (categories.length > 6) {
    const showAll = directory.locator(".show-all-button");
    await showAll.click();
    await expect(directory.locator(".category-card")).toHaveCount(
      categories.length,
    );
  }
  await expectDocumentFits(page);
});

for (const width of [320, 390, 768]) {
  test(`populated basket, collections and checkout fit at ${width}px`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 844 });
    await page.goto("/catalog");
    let card = page.locator(".product-card").first();
    await expect(card).toBeVisible();
    await card
      .getByRole("button", { name: "Додати в обране", exact: true })
      .click();
    await card
      .getByRole("button", { name: "Додати до порівняння", exact: true })
      .click();
    await page
      .locator(".product-card")
      .nth(1)
      .getByRole("button", { name: "Додати до порівняння", exact: true })
      .click();
    await page.goto("/favorites");
    await expect(page.locator(".product-card").first()).toBeVisible();
    await expectDocumentFits(page);
    await page.goto("/compare");
    await expect(page.locator(".compare-table")).toBeVisible();
    await expectDocumentFits(page);
    await page.goto("/catalog");
    card = page.locator(".product-card").first();
    await card
      .getByRole("button", { name: "Додати в кошик", exact: true })
      .click();
    const cart = page.getByRole("dialog", { name: "Кошик", exact: true });
    await expect(cart).toBeVisible();
    await expectDocumentFits(page);
    await cart.getByRole("button", { name: "Збільшити кількість" }).click();
    await cart
      .getByRole("link", { name: "Оформити замовлення", exact: true })
      .click();
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(
      "Оформлення замовлення",
    );
    await page.getByLabel("Ім’я та прізвище").fill("Перевірка верстки");
    await expectDocumentFits(page);
    expect(
      await page
        .locator(".checkout-form")
        .evaluate((el) => el.scrollWidth <= el.clientWidth + 1),
    ).toBe(true);
    await expect(page.locator(".order-totals")).toBeVisible();
    // No order is submitted: only a price quote is requested.
    await page.getByLabel("Промокод", { exact: true }).focus();
    await expectDocumentFits(page);
    await page.goto("/catalog");
    await page.getByRole("button", { name: "Фільтри", exact: true }).click();
    const filters = page.getByRole("dialog", { name: "Фільтри товарів" });
    await expect(filters).toBeVisible();
    expect(
      await filters
        .locator(".filters__body")
        .evaluate((el) => el.scrollWidth <= el.clientWidth + 1),
    ).toBe(true);
    await expectDocumentFits(page);
    await page.keyboard.press("Escape");
  });

  test(`long product values and maximum monetary amounts fit at ${width}px`, async ({
    page,
    request,
  }) => {
    await page.setViewportSize({ width, height: 844 });
    const products = await request.get(
      "/api/v1/catalog/products?page_size=1&include_facets=false",
    );
    const slug = (await products.json()).items[0].slug as string;
    await page.goto(`/products/${slug}`);
    await expect(page.locator(".product-detail__price strong")).toBeVisible();
    await page.evaluate(() => {
      document.querySelector(".product-detail__price strong")!.textContent =
        "9 999 999 999,99 грн";
      document.querySelector(".product-detail h1")!.textContent = "X".repeat(
        200,
      );
      document.querySelector(".specification-list dd")!.textContent =
        "X".repeat(300);
    });
    await expectDocumentFits(page);
    await page.goto("/catalog");
    const card = page.locator(".product-card").first();
    await expect(card).toBeVisible();
    await card.locator(".price-stack strong").evaluate((el) => {
      el.firstChild!.textContent = "9 999 999 999,99 грн";
    });
    expect(
      await card
        .locator(".price-stack")
        .evaluate((el) => el.scrollWidth <= el.clientWidth + 1),
    ).toBe(true);
    await expectDocumentFits(page);
  });
}

test("lazy home products do not move the following sections", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  let release!: () => void;
  const pending = new Promise<void>((done) => {
    release = done;
  });
  await page.route("**/api/v1/catalog/products?**", async (route) => {
    await pending;
    await route.continue();
  });
  await page.goto("/");
  await page.evaluate(() => document.fonts.ready);
  await expect(
    page.locator("#catalog .section-card:not(.section-card--skeleton)").first(),
  ).toBeVisible();
  const rail = page.locator(".popular-products");
  await rail.scrollIntoViewIfNeeded();
  const nextSection = page.locator(".home-entry-points");
  const documentTop = () =>
    nextSection.evaluate(
      (element) => element.getBoundingClientRect().top + window.scrollY,
    );
  const before = await documentTop();
  try {
    await expect(rail.getByText("Завантажуємо товари…")).toBeVisible();
  } finally {
    release();
  }
  await expect(rail.locator(".product-card").first()).toBeVisible();
  expect(await documentTop()).toBeCloseTo(before, 0);
  await expectDocumentFits(page);
});

test("switching a home rail keeps the current cards visible while loading", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  const rail = page.locator(".popular-products");
  await rail.scrollIntoViewIfNeeded();
  const card = rail.locator(".product-card").first();
  await expect(card).toBeVisible();
  const before = await card.boundingBox();
  let release!: () => void;
  const pending = new Promise<void>((done) => {
    release = done;
  });
  await page.route("**/api/v1/catalog/products?**", async (route) => {
    const requestUrl = new URL(route.request().url());
    if (requestUrl.searchParams.get("is_popular") !== "true")
      return route.continue();
    await pending;
    await route.continue();
  });
  try {
    await rail.getByRole("tab", { name: "Популярне", exact: true }).click();
    await expect(rail.locator(".home-rail-content")).toHaveAttribute(
      "aria-busy",
      "true",
    );
    await expect(card).toBeVisible();
    expect((await card.boundingBox())!.y).toBeCloseTo(before!.y, 0);
    await expectDocumentFits(page);
  } finally {
    release();
  }
  await expect(rail.locator(".home-rail-content")).toHaveAttribute(
    "aria-busy",
    "false",
  );
});

test("broken gallery images keep the reserved media dimensions", async ({
  page,
  request,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const products = await request.get(
    "/api/v1/catalog/products?page_size=1&include_facets=false",
  );
  const product = (await products.json()).items[0] as { slug: string };
  let release!: () => void;
  const pending = new Promise<void>((done) => {
    release = done;
  });
  await page.route("**/*", async (route) => {
    if (route.request().resourceType() !== "image") return route.continue();
    await pending;
    await route.abort();
  });
  await page.goto(`/products/${product.slug}`, {
    waitUntil: "domcontentloaded",
  });
  const visual = page.locator(".product-detail__visual");
  await expect(visual).toBeVisible();
  const before = await visual.boundingBox();
  release();
  await expect(visual.locator("svg")).toBeVisible();
  const after = await visual.boundingBox();
  expect(after!.height).toBe(before!.height);
  expect(after!.width).toBe(before!.width);
  await expectDocumentFits(page);
});

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
    const product = (await products.json()).items[0] as {
      slug: string;
      category: { slug: string };
    };
    const [brandsResponse, sectionsResponse] = await Promise.all([
      request.get("/api/v1/catalog/brands"),
      request.get("/api/v1/catalog/sections"),
    ]);
    expect(brandsResponse.ok()).toBe(true);
    expect(sectionsResponse.ok()).toBe(true);
    const brands = (await brandsResponse.json()) as Array<{ slug: string }>;
    const sections = (await sectionsResponse.json()) as Array<{ slug: string }>;

    for (const path of [
      "/",
      "/catalog",
      "/catalog/categories",
      `/products/${product.slug}`,
      "/brands",
      `/brands/${brands[0].slug}`,
      `/catalog/${product.category.slug}`,
      "/catalog/sale",
      "/catalog/new",
      `/sections/${sections[0].slug}`,
      "/account/login",
      "/account/login?mode=register",
      "/account",
      "/favorites",
      "/compare",
      "/checkout",
      "/advisors",
      "/custom-boards",
      "/admin/login",
      "/not-a-real-page",
    ]) {
      await page.goto(path);
      if (path !== "/admin/login") {
        await expect(page.locator(".site-header")).toBeVisible();
      } else {
        await expect(page.getByLabel("Логін")).toBeVisible();
      }
      await expect(
        page.getByRole("heading", { level: 1 }).first(),
      ).toBeVisible();
      await expectDocumentFits(page);

      if (path === "/") {
        const tabs = page.getByRole("tablist");
        for (const tab of await tabs.getByRole("tab").all()) {
          expect(
            await tab.evaluate(
              (element) => element.scrollHeight <= element.clientHeight + 1,
            ),
          ).toBe(true);
        }
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
