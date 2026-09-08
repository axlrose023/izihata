import { expect, test } from "@playwright/test";

test("public routes render and product navigation works", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toContainText(
    "Правильна деталь",
  );
  await expect(page.getByText("Усі категорії", { exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Виробники" })).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Відгуки наших клієнтів" }),
  ).toBeVisible();
  const searchResponse = page.waitForResponse(
    (response) =>
      response.url().includes("/api/v1/catalog/products?") &&
      response.url().includes("search=AX-10014") &&
      response.status() === 200,
  );
  await page.getByLabel("Пошук товарів").fill("AX-10014");
  await searchResponse;
  await expect(page.locator(".search-suggestions a")).toHaveCount(1);

  await page.goto("/catalog");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(
    "Усі товари",
  );
  const product = page.locator(".product-card").first();
  await expect(product).toBeVisible();
  const productName = await product.locator(".product-card__name").innerText();
  const productRequest = page.waitForResponse(
    (response) =>
      response.url().includes("/api/v1/catalog/products/") &&
      response.status() === 200,
  );
  await product.getByRole("link", { name: productName }).click();
  const productResponse = await productRequest;
  const productBody = (await productResponse.json()) as {
    image_url: string;
    name: string;
    reviews: Array<{ author: string; text: string }>;
    related: Array<{ id: string }>;
  };
  expect(new URL(productResponse.url()).origin).toBe(
    new URL(page.url()).origin,
  );
  expect(productBody.image_url).toMatch(/^\/product-images\/.+\.svg$/);
  await expect(page).toHaveURL(/\/products\//);
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await expect(page.getByRole("img", { name: productBody.name })).toBeVisible();
  if (productBody.related.length) {
    await expect(
      page.getByRole("heading", { name: "Схожі товари" }),
    ).toBeVisible();
  } else {
    await expect(
      page.getByRole("heading", { name: "Схожі товари" }),
    ).toHaveCount(0);
  }
  expect(productBody.reviews).toHaveLength(2);
  await expect(page.getByRole("heading", { name: "Відгуки" })).toBeVisible();
  await expect(
    page.getByText("Офіційна гарантія та повернення протягом 14 днів"),
  ).toBeVisible();
  const specificationHeading = page.getByRole("heading", {
    name: "Характеристики",
  });
  await expect(specificationHeading).toBeVisible();
  const specificationHeadingFits = await specificationHeading.evaluate(
    (element) => element.scrollWidth <= element.clientWidth,
  );
  expect(specificationHeadingFits).toBe(true);

  await page.goto("/");
  if ((page.viewportSize()?.width ?? 1000) <= 820) {
    await page.getByRole("button", { name: "Відкрити меню" }).click();
  }
  await expect(
    page.getByRole("link", { name: "Щити", exact: true }),
  ).toHaveAttribute("href", "/custom-boards");

  await page.goto("/not-a-real-page");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(
    "Сторінку не знайдено",
  );
});

test("guest storefront does not restore a customer session", async ({
  page,
}) => {
  const customerRefreshRequests: string[] = [];
  page.on("request", (request) => {
    if (request.url().includes("/api/v1/customer-auth/refresh")) {
      customerRefreshRequests.push(request.url());
    }
  });

  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  expect(customerRefreshRequests).toHaveLength(0);
});

test("section hubs and customer tools use the versioned API", async ({
  page,
}) => {
  await page.goto("/sections/home-repair");
  await expect(
    page.getByRole("heading", { name: "Дім і ремонт" }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Усі товари розділу" }),
  ).toBeVisible();

  await page.goto("/advisors");
  await page.getByRole("button", { name: "Розрахувати" }).first().click();
  await expect(page.getByText("Розрахунковий струм").first()).toBeVisible();
  await expect(page.getByText("Рекомендований переріз")).toBeVisible();

  await page.goto("/custom-boards");
  await page.getByRole("button", { name: "Оцінити комплектацію" }).click();
  await expect(page.locator(".custom-board-estimate")).toBeVisible();

  await page.goto("/account");
  await expect(
    page.getByRole("heading", {
      name: "Керуйте замовленнями та бізнес-умовами",
    }),
  ).toBeVisible();
});

test("cart receives an authoritative quote and creates an order", async ({
  page,
}) => {
  await page.goto("/catalog");
  await page.getByRole("button", { name: "Додати в кошик" }).first().click();
  await expect(page.getByRole("heading", { name: /Кошик/ })).toBeVisible();
  await page.getByRole("link", { name: "Оформити замовлення" }).click();

  await expect(page.getByRole("heading", { level: 1 })).toHaveText(
    "Оформлення замовлення",
  );
  await page.getByLabel("Ім’я та прізвище").fill("QA Покупець");
  await page.getByLabel("Телефон").fill("+380501112233");
  await page.getByText("Самовивіз", { exact: false }).click();
  await expect(page.locator(".order-totals")).toBeVisible();
  await page.getByRole("button", { name: "Підтвердити замовлення" }).click();

  await expect(page).toHaveURL(/\/order\/success/);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(
    "Дякуємо за замовлення!",
  );
});

test("checkout explains an invalid promo and suggests Nova Poshta addresses", async ({
  page,
}) => {
  await page.route("**/api/v1/delivery/cities?*", async (route) => {
    await route.fulfill({
      json: [
        {
          ref: "8d5a980d-391c-11dd-90d9-001a92567626",
          name: "Київ",
          label: "м. Київ, Київська обл.",
        },
      ],
    });
  });
  await page.route("**/api/v1/delivery/points?*", async (route) => {
    await route.fulfill({
      json: [
        {
          ref: "point-ref",
          name: "Відділення №12",
          label: "Київ, вул. Хрещатик, 12",
          number: "12",
        },
      ],
    });
  });

  await page.goto("/catalog");
  await page.getByRole("button", { name: "Додати в кошик" }).first().click();
  await page.getByRole("link", { name: "Оформити замовлення" }).click();

  await page.getByLabel("Промокод").fill("incorrect");
  await page.getByRole("button", { name: "Застосувати" }).click();
  await expect(
    page.getByText("Промокод недійсний або термін його дії минув."),
  ).toBeVisible();
  await page.getByLabel("Промокод").fill("correct-me");
  await expect(
    page.getByText("Промокод недійсний або термін його дії минув."),
  ).not.toBeVisible();

  await page.getByLabel("Місто").fill("Київ");
  await expect(
    page.getByRole("option", { name: "м. Київ, Київська обл." }),
  ).toBeVisible();
  await page.getByLabel("Місто").press("ArrowDown");
  await page.getByLabel("Місто").press("Enter");
  const point = page.getByRole("combobox", { name: "Відділення" });
  await expect(point).toBeEnabled();
  await expect(point).toHaveAttribute(
    "placeholder",
    "Почніть вводити номер або адресу й оберіть відділення зі списку",
  );
  await point.fill("12");
  await expect(
    page.getByRole("option", { name: "Київ, вул. Хрещатик, 12" }),
  ).toBeVisible();
  await point.press("ArrowDown");
  await point.press("Enter");
  await expect(point).toHaveValue("Київ, вул. Хрещатик, 12");
  await expect(page.getByRole("listbox")).toHaveCount(0);
});

test("favourites and comparison survive route navigation", async ({ page }) => {
  await page.goto("/catalog");
  await page.getByRole("button", { name: "Додати в обране" }).first().click();
  await page
    .getByRole("button", { name: "Додати до порівняння" })
    .first()
    .click();

  await page.goto("/compare");
  await expect(
    page.getByRole("heading", { name: "Додайте ще один товар" }),
  ).toBeVisible();

  await page.goto("/catalog");
  await page
    .getByRole("button", { name: "Додати до порівняння" })
    .nth(1)
    .click();

  await page.goto("/favorites");
  await expect(page.locator(".product-card")).toHaveCount(1);
  await page.goto("/compare");
  await expect(page.locator(".compare-table")).toBeVisible();
});

test("callback validation and submission work", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Потрібна консультація" }).click();
  const dialog = page.getByRole("dialog");
  const box = await dialog.boundingBox();
  const viewport = page.viewportSize();
  expect(box).not.toBeNull();
  expect(viewport).not.toBeNull();
  expect(Math.abs(box!.x + box!.width / 2 - viewport!.width / 2)).toBeLessThan(
    3,
  );
  expect(
    Math.abs(box!.y + box!.height / 2 - viewport!.height / 2),
  ).toBeLessThan(3);
  await dialog.getByLabel("Ім’я").fill("QA Клієнт");
  await dialog.getByLabel("Телефон").fill("+380501112233");
  await dialog.getByRole("button", { name: "Надіслати" }).click();
  await expect(dialog.getByText("Дякуємо!")).toBeVisible();
});

test("product quantity is added as one cart operation", async ({ page }) => {
  await page.goto("/catalog");
  await page.locator(".product-card__name a").first().click();
  await page
    .getByRole("button", { name: "Збільшити кількість товару" })
    .click();
  await page
    .getByRole("button", { name: "Збільшити кількість товару" })
    .click();
  await expect(
    page.getByRole("spinbutton", { name: "Кількість товару", exact: true }),
  ).toHaveValue("3");
  await page
    .locator(".product-actions-panel")
    .getByRole("button", { name: "Додати в кошик" })
    .click();
  await expect(page.getByRole("heading", { name: /Кошик · 3/ })).toBeVisible();
});

test("the cart suggests only curated companion products", async ({ page }) => {
  // "Bought together" is admin-managed; the demo product is the seeded one
  // that carries those relations.
  await page.goto("/products/demo-modular-circuit-breaker-1p-c16");
  await page
    .locator(".product-actions-panel")
    .getByRole("button", { name: "Додати в кошик" })
    .click();

  const drawer = page.locator(".drawer__panel");
  await expect(drawer.getByText("З цим купують")).toBeVisible();
  await expect(drawer.locator(".cart-recommendations article")).not.toHaveCount(
    0,
  );
});

test("catalog keeps every relevant facet", async ({ page }) => {
  await page.goto("/catalog/lowvoltage?brand=Demo%20Electric");
  await expect(
    page.getByRole("heading", {
      name: "Низьковольтне обладнання",
      exact: true,
    }),
  ).toBeVisible();
  if ((page.viewportSize()?.width ?? 1000) <= 820) {
    await page.getByRole("button", { name: "Фільтри" }).click();
    await page.getByRole("button", { name: "Більше фільтрів" }).click();
  }
  await expect(page.getByText("Полюси", { exact: true })).toBeVisible();
  await expect(
    page.getByText("Вибір серії покаже всі сумісні елементи цього дизайну."),
  ).toBeVisible();
});

test("mobile storefront keeps search, navigation and filters accessible", async ({
  page,
}) => {
  test.skip(
    (page.viewportSize()?.width ?? 1000) > 820,
    "mobile-only assertion",
  );

  await page.goto("/");
  await expect(page.locator(".header-search")).toBeVisible();
  const mobileNavigation = page.getByRole("navigation", {
    name: "Мобільна навігація",
  });
  await expect(mobileNavigation).toBeVisible();
  await expect(mobileNavigation.getByRole("link")).toHaveCount(4);
  await expect(
    mobileNavigation.getByRole("button", { name: /Кошик/ }),
  ).toBeVisible();

  await page.goto("/catalog");
  await expect(
    mobileNavigation.getByRole("link", { name: "Каталог" }),
  ).toHaveAttribute("aria-current", "page");
  await expect(page.getByRole("heading", { name: "Усі товари" })).toBeVisible();
  const filters = page.locator(".filters");
  await page.getByRole("button", { name: "Фільтри" }).click();
  await expect(filters).toHaveAttribute("data-open", "true");
  await expect(
    filters.getByRole("button", { name: /^Показати \d+/ }),
  ).toBeVisible();
  await filters.getByRole("button", { name: "Більше фільтрів" }).click();
  await expect(
    filters.getByText("Одиниця продажу", { exact: true }),
  ).toBeVisible();
  await filters.getByRole("button", { name: "Закрити фільтри" }).click();
  await expect(filters).not.toHaveAttribute("data-open", "true");
});

test("filters apply without a submit button", async ({ page }) => {
  await page.goto("/catalog");
  const filters = page.locator(".filters");
  if ((page.viewportSize()?.width ?? 1000) <= 820) {
    await page.getByRole("button", { name: "Фільтри" }).click();
    await expect(filters).toHaveAttribute("data-open", "true");
  }
  await expect(
    filters.getByRole("button", { name: "Застосувати" }),
  ).toHaveCount(0);

  const brand = filters.getByRole("checkbox", { name: /Demo Electric/ });
  await expect(brand).toBeVisible();
  await brand.click();

  await expect(page).toHaveURL(/brand=Demo\+Electric/);
  await expect(brand).toBeChecked();
  await expect(page.locator(".product-card")).not.toHaveCount(0);
});

test("the home page rails popular products", async ({ page }) => {
  await page.goto("/");
  const rail = page.locator(".popular-products .carousel__rail");
  await expect(rail).toBeVisible();
  const shown = await rail.locator(".carousel__item").count();
  expect(shown).toBeGreaterThan(0);
  expect(shown).toBeLessThanOrEqual(5);

  const more = page.locator(".popular-products .show-all-button");
  if (await more.count()) {
    await more.click();
    await expect
      .poll(() => rail.locator(".carousel__item").count())
      .toBeGreaterThan(shown);
  }
});

test("customer reviews are shown as a rail", async ({ page }) => {
  await page.goto("/");
  const reviews = page.locator(".testimonials-section");
  if (!(await reviews.count())) return;
  await expect(
    reviews.getByRole("heading", { name: "Відгуки наших клієнтів" }),
  ).toBeVisible();
  await expect(reviews.locator(".testimonial").first()).toBeVisible();
});

test("manufacturers get their own rail and pages", async ({ page }) => {
  await page.goto("/");
  const rail = page.locator(".brands-section .carousel__rail");
  await expect(rail).toBeVisible();
  await expect(rail.locator(".brand-tile").first()).toBeVisible();

  await page.goto("/brands");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Виробники");
  const tiles = page.locator(".brand-grid .brand-tile");
  await expect(tiles.first()).toBeVisible();

  // A tile may show a logo instead of a name, so navigate by its link.
  const slug = (await tiles.first().getAttribute("href"))?.split("/").pop();
  expect(slug).toBeTruthy();
  await tiles.first().click();
  await expect(page).toHaveURL(new RegExp(`/brands/${slug}$`));
  // The brand page is the catalog scoped to that manufacturer.
  await expect(page.locator(".product-card").first()).toBeVisible();
  await expect(page.getByRole("heading", { level: 1 })).not.toBeEmpty();
});

test("a section card is clickable as a whole", async ({ page }) => {
  await page.goto("/");
  const card = page.locator(".section-card").first();
  await expect(card).toBeVisible();

  // The picture must open the section, not only the call to action.
  const image = card.locator("img");
  // elementFromPoint only sees the viewport, so bring the card into it first.
  await image.scrollIntoViewIfNeeded();
  const box = await image.boundingBox();
  const topmost = await page.evaluate(
    ([x, y]) => {
      const element = document.elementFromPoint(x, y);
      return element?.closest("a")?.getAttribute("href") ?? null;
    },
    [box!.x + box!.width / 2, box!.y + box!.height / 2],
  );
  expect(topmost).toMatch(/^\/sections\//);

  await image.click();
  await expect(page).toHaveURL(/\/sections\/.+/);
  await expect(page.getByRole("heading", { level: 1 })).not.toBeEmpty();

  // The reset to the top must be instant. A smooth document default made every
  // new page slide up from the previous page's offset.
  expect(
    await page.evaluate(
      () => getComputedStyle(document.documentElement).scrollBehavior,
    ),
  ).toBe("auto");
  expect(await page.evaluate(() => Math.round(window.scrollY))).toBe(0);
});

test("sale and new arrivals are their own catalog sections", async ({
  page,
}) => {
  await page.goto("/catalog/sale");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(
    "Акції та знижки",
  );
  const cards = page.locator(".product-card");
  if (await cards.count()) {
    // Every listed product must actually carry a reduced price.
    await expect(cards.first().locator("del")).toBeVisible();
  }

  await page.goto("/catalog/new");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Новинки");
});

test("the catalog offers two grid densities", async ({ page }) => {
  await page.goto("/catalog");
  const grid = page.locator(".product-grid--catalog");
  const toggle = page.getByLabel("Вигляд каталогу");

  if ((page.viewportSize()?.width ?? 1000) <= 820) {
    await expect(toggle).toBeHidden();
    return;
  }

  await expect(toggle.getByRole("link")).toHaveCount(2);
  await expect(grid).not.toHaveAttribute("data-view", "large");
  await toggle.getByRole("link", { name: "Більша сітка" }).click();
  await expect(grid).toHaveAttribute("data-view", "large");
  await toggle.getByRole("link", { name: "Дрібніша сітка" }).click();
  await expect(grid).toHaveAttribute("data-view", "grid");
});

test("the sidebar opens the catalog one level down", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Відкрити меню" }).click();
  const panel = page.locator(".site-sidebar__panel");
  await expect(panel).toBeVisible();

  // Categories are behind the catalog entry, not listed straight away.
  await expect(panel.locator(".site-sidebar__categories")).toHaveCount(0);
  await panel.getByRole("button", { name: "Каталог товарів" }).click();
  await expect(
    panel.locator(".site-sidebar__categories a").first(),
  ).toBeVisible();
  await expect(panel.getByRole("link", { name: "Усі товари" })).toHaveAttribute(
    "href",
    "/catalog",
  );

  await panel.getByRole("button", { name: "Каталог товарів" }).click();
  await expect(panel.locator(".site-sidebar__auth")).toBeVisible();
});

test("empty checkout and staff login route have safe states", async ({
  page,
}) => {
  await page.goto("/checkout");
  await expect(
    page.getByRole("heading", { name: "Немає що оформлювати" }),
  ).toBeVisible();
  await page.goto("/admin/login");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(
    "Вхід до панелі",
  );
});
