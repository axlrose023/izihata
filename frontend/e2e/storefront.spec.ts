import { expect, test } from "@playwright/test";

test("public routes render and product navigation works", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toContainText(
    "Правильна деталь",
  );
  await expect(page.getByText("Усі категорії", { exact: true })).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Бренди в каталозі" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Що кажуть покупці" }),
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
  const product = page.locator(".product-card__name").first();
  await expect(product).toBeVisible();
  const productRequest = page.waitForResponse(
    (response) =>
      response.url().includes("/api/v1/catalog/products/") &&
      response.status() === 200,
  );
  await product.click();
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

  await page.getByLabel("Місто").fill("Київ");
  await expect(page.locator("#nova-poshta-cities option")).toHaveCount(1);
  await page.getByLabel("Місто").fill("м. Київ, Київська обл.");
  await expect(
    page.getByRole("combobox", { name: "Відділення" }),
  ).toBeEnabled();
  await expect(page.locator("#nova-poshta-points option")).toHaveCount(1);
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
  await page.locator(".product-card__name").first().click();
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
  await expect(page.getByText("З цим купують")).toBeVisible();
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
  await expect(
    page.getByRole("navigation", { name: "Мобільна навігація" }),
  ).toBeVisible();

  await page.goto("/catalog");
  await expect(page.getByRole("heading", { name: "Усі товари" })).toBeVisible();
  const filters = page.locator(".filters");
  const results = page.locator(".catalog-results");
  await expect(filters.locator(".filters__summary")).toContainText("Фільтри");
  await filters.locator(".filters__summary").click();
  await expect(
    filters.getByRole("button", { name: "Застосувати" }),
  ).toBeVisible();
  const filterBox = await filters.locator(".filters__summary").boundingBox();
  const resultBox = await results.locator(".catalog-toolbar").boundingBox();
  expect(filterBox).not.toBeNull();
  expect(resultBox).not.toBeNull();
  expect(filterBox!.y).toBeLessThan(resultBox!.y);
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
