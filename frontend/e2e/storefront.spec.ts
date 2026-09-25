import { expect, test, type Page } from "@playwright/test";

async function continueToCheckout(page: Page) {
  const checkout = page.getByRole("link", { name: "Оформити замовлення" });

  if ((page.viewportSize()?.width ?? 1000) > 820) {
    await checkout.click();
    return;
  }

  // The full-screen mobile drawer is fixed. Chromium's automatic scrolling can
  // misidentify its preceding text as an overlap, while a real tap at the
  // button's visible centre works as expected.
  await checkout.scrollIntoViewIfNeeded();
  const box = await checkout.boundingBox();
  if (!box) throw new Error("Checkout button has no visible bounding box");
  await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
}

test("public routes render and product navigation works", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toContainText(
    "Все для щита, кабелю й освітлення",
  );
  await expect(
    page.getByRole("heading", { name: "Часто купують" }),
  ).toBeVisible();
  await expect(page.getByRole("link", { name: /Дім і ремонт/ })).toBeVisible();
  await expect(page.getByText("Гуртові ціни", { exact: true })).toHaveCount(0);
  const searchResponse = page.waitForResponse(
    (response) =>
      response.url().includes("/api/v1/catalog/products?") &&
      response.url().includes("search=AX-10014") &&
      response.status() === 200,
  );
  if ((page.viewportSize()?.width ?? 1000) <= 820) {
    await page.getByRole("link", { name: "Відкрити пошук товарів" }).click();
    await page.getByLabel("Пошук у каталозі").fill("AX-10014");
    await page.getByRole("button", { name: "Знайти" }).click();
  } else {
    await page
      .getByRole("combobox", { name: "Пошук товарів" })
      .fill("AX-10014");
  }
  await searchResponse;
  if ((page.viewportSize()?.width ?? 1000) > 820) {
    await expect(page.locator(".search-suggestions a")).toHaveCount(1);
  }

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
  // Відгуки й умови повернення живуть у вкладках, тож спершу відкриваємо їх.
  await page.getByRole("tab", { name: /^Відгуки/ }).click();
  await expect(page.getByRole("heading", { name: "Відгуки" })).toBeVisible();
  await page.getByRole("tab", { name: "Гарантія та повернення" }).click();
  await expect(
    page.getByText("Офіційна гарантія та повернення протягом 14 днів"),
  ).toBeVisible();
  await page.getByRole("tab", { name: "Характеристики" }).click();
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

test("catalog CTAs reuse the category directory on the home page", async ({
  page,
}) => {
  await page.goto("/");
  const categoryDirectory = page.locator("#catalog");
  const homeCatalogCta = page.getByRole("link", {
    name: "Перейти в каталог",
    exact: true,
  });
  await expect(homeCatalogCta).toHaveAttribute("href", "/#catalog");
  await homeCatalogCta.click();
  await expect(page).toHaveURL(/\/#catalog$/);
  await expect(categoryDirectory).toBeInViewport();

  await page.getByRole("button", { name: "Кошик: 0" }).click();
  await expect(
    page
      .locator(".drawer__empty")
      .getByRole("link", { name: "Перейти в каталог" }),
  ).toHaveAttribute("href", "/#catalog");

  await page.goto("/checkout");
  await expect(
    page.getByRole("link", { name: "Перейти до каталогу" }),
  ).toHaveAttribute("href", "/#catalog");

  await page.goto("/not-a-real-page");
  await expect(page.getByRole("link", { name: "До каталогу" })).toHaveAttribute(
    "href",
    "/#catalog",
  );
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
  const [headerGrid, sectionBreadcrumbs] = await Promise.all([
    page.locator(".header-main").boundingBox(),
    page.locator(".section-hub .breadcrumbs").boundingBox(),
  ]);
  expect(headerGrid).not.toBeNull();
  expect(sectionBreadcrumbs).not.toBeNull();
  expect(sectionBreadcrumbs?.x).toBeCloseTo(headerGrid?.x ?? 0, 0);
  expect(sectionBreadcrumbs?.width).toBeCloseTo(headerGrid?.width ?? 0, 0);

  await page.goto("/advisors");
  await expect(
    page.getByRole("heading", { name: "Який переріз і номінал вам потрібні" }),
  ).toBeVisible();
  await expect(page.getByText("Робочий струм")).toBeVisible();
  await expect(page.getByText("Підібрані позиції з каталогу")).toBeVisible();

  await page.goto("/custom-boards");
  await expect(
    page.getByRole("heading", { name: "Корпус щита" }),
  ).toBeVisible();
  await expect(page.getByText("Схема складання")).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Надіслати заявку на складання" }),
  ).toBeEnabled();
  await page
    .getByRole("button", { name: "Надіслати заявку на складання" })
    .click();
  await expect(
    page.getByRole("dialog", { name: "Контакти для заявки" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Закрити" }).click();

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
  await continueToCheckout(page);

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
    "Замовлення прийнято",
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
  await continueToCheckout(page);

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
  await page.goto("/catalog");
  if ((page.viewportSize()?.width ?? 1000) <= 820) {
    await page.locator(".product-card__name a").first().click();
    await page.getByRole("button", { name: "Купити в один клік" }).click();
  } else {
    await page.getByRole("button", { name: "1 клік" }).first().click();
  }
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
  await expect(page.getByRole("heading", { name: "Кошик" })).toBeVisible();
  await expect(page.locator(".drawer__count")).toHaveText("3 позиції");
});

test("the cart matches the delivery and totals artboard", async ({ page }) => {
  await page.goto("/products/demo-modular-circuit-breaker-1p-c16");
  await page
    .locator(".product-actions-panel")
    .getByRole("button", { name: "Додати в кошик" })
    .click();

  const drawer = page.locator(".drawer__panel");
  await expect(drawer.locator(".drawer__delivery-progress")).toBeVisible();
  await expect(drawer.getByText("До сплати")).toBeVisible();
  await expect(
    drawer.getByRole("button", { name: "Продовжити покупки" }),
  ).toBeVisible();
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
  // Картки теж друкують «Полюси» у таблиці характеристик, тож фасет
  // шукаємо саме в панелі фільтрів.
  const filters = page.locator(".filters");
  await expect(filters.getByText("Полюси", { exact: true })).toBeVisible();
  await expect(
    filters.getByText("Вибір серії покаже всі сумісні елементи цього дизайну."),
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
  await expect(
    page.getByRole("button", { name: "Відкрити меню" }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Пошук товарів" }),
  ).toHaveAttribute("href", "/catalog");
  const mobileNavigation = page.getByRole("navigation", {
    name: "Мобільна навігація",
  });
  await expect(mobileNavigation).toBeHidden();

  await page.goto("/catalog");
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

test("product rail cards keep their footers aligned", async ({ page }) => {
  await page.goto("/");
  const cards = page.locator(".popular-products .product-card");
  await expect.poll(() => cards.count()).toBeGreaterThan(1);

  // Product attributes are data-driven. Add extra rows to one card to ensure
  // the rest of the rail still stretches to the same height and CTA baseline.
  await cards.evaluateAll((elements) => {
    const target = elements.at(-1);
    const body = target?.querySelector(".product-card__body");
    if (!body) return;

    let specs = body.querySelector(".product-card__specs");
    if (!specs) {
      specs = document.createElement("dl");
      specs.className = "product-card__specs";
      body.insertBefore(specs, body.querySelector(".product-card__footer"));
    }
    for (let index = 0; index < 3; index += 1) {
      const row = document.createElement("div");
      row.innerHTML = "<dt>Додаткова характеристика</dt><dd>значення</dd>";
      specs.append(row);
    }
  });

  const layout = await cards.evaluateAll((elements) =>
    elements.map((card) => {
      const cardRect = card.getBoundingClientRect();
      const footerRect = card
        .querySelector(".product-card__footer")
        ?.getBoundingClientRect();
      return {
        bottom: cardRect.bottom,
        height: cardRect.height,
        footerBottom: footerRect?.bottom,
      };
    }),
  );
  const first = layout[0];
  expect(first).toBeDefined();
  for (const card of layout.slice(1)) {
    expect(card.height).toBeCloseTo(first!.height, 0);
    expect(card.bottom).toBeCloseTo(first!.bottom, 0);
    expect(card.footerBottom).toBeCloseTo(first!.footerBottom ?? 0, 0);
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

test("a section is reachable from the home directory", async ({ page }) => {
  test.skip(
    (page.viewportSize()?.width ?? 1000) <= 820,
    "The approved mobile artboard deliberately omits the desktop category directory.",
  );
  await page.goto("/");
  const section = page
    .getByRole("navigation", { name: "Розділи каталогу" })
    .getByRole("link")
    .first();
  await expect(section).toHaveAttribute("href", /^\/sections\//);
  await section.click();
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
  if ((page.viewportSize()?.width ?? 1000) > 820) {
    await expect(
      page.getByRole("banner").getByRole("link", { name: "Усі товари" }),
    ).toHaveAttribute("href", "/catalog");
    return;
  }
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

test("every overlay closes with Escape and announces itself as a dialog", async ({
  page,
}) => {
  await page.goto("/catalog");

  // Кошик: відкривається сам після додавання товару.
  await page.locator(".cart-add").first().click();
  const cart = page.getByRole("dialog", { name: "Кошик" });
  await expect(cart).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(cart).toBeHidden();

  if ((page.viewportSize()?.width ?? 1000) <= 820) {
    await page.getByRole("button", { name: "Відкрити меню" }).click();
    const menu = page.getByRole("dialog", { name: "Головне меню" });
    await expect(menu).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(menu).toBeHidden();
  }
});
