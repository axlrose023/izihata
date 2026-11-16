import { expect, test } from "@playwright/test";
import type { Category } from "../src/shared/types/api";

const requestedSubcategories: Record<string, string[]> = {
  lowvoltage: [
    "Модульні автоматичні вимикачі",
    "Силові автоматичні вимикачі",
    "Повітряні автоматичні вимикачі",
    "Автоматичні вимикачі захисту двигуна",
    "Додаткові пристрої до автоматичних вимикачів",
    "АВР (автоматичний ввід резерву)",
  ],
  panels: ["ЯТП (ящик із знижувальним трансформатором)"],
  light: ["Блоки живлення"],
  power: ["Щити захисту PV систем"],
  installation: ["Термоусаджувальна трубка", "Ізолента"],
  cabletrays: ["Хомути (стяжки кабельні)", "Кабельні тримачі"],
};

test("requested subcategories return exactly their catalog counts", async ({
  request,
}) => {
  const response = await request.get("/api/v1/catalog/categories");
  expect(response.ok()).toBe(true);
  const categories = (await response.json()) as Category[];
  const power = categories.find((category) => category.slug === "power")!;
  expect(
    power.subcategories.some((item) => item.name === "Блоки живлення"),
  ).toBe(false);
  expect(
    categories
      .find((category) => category.slug === "panels")!
      .subcategories.some((item) => item.name.startsWith("АВР")),
  ).toBe(false);
  for (const [slug, names] of Object.entries(requestedSubcategories)) {
    const category = categories.find((category) => category.slug === slug)!;
    expect(category).toBeDefined();
    for (const name of names) {
      const subcategory = category.subcategories.find(
        (subcategory) => subcategory.name === name,
      )!;
      expect(subcategory).toBeDefined();
      const products = await request.get("/api/v1/catalog/products", {
        params: {
          category: slug,
          subcategory: subcategory.slug,
          page_size: 3,
          include_facets: false,
        },
      });
      expect(products.ok()).toBe(true);
      const body = await products.json();
      expect(body.total).toBe(subcategory.product_count);
      for (const product of body.items) {
        expect(product.category.slug).toBe(slug);
        expect(product.subcategory.slug).toBe(subcategory.slug);
      }
    }
  }
});

test("material and IP option counts agree with filtered products", async ({
  request,
}, testInfo) => {
  const username = process.env.ADMIN_USERNAME;
  const password = process.env.ADMIN_PASSWORD;
  test.skip(!username || !password, "Admin credentials are not configured");
  const login = await request.post("/api/v1/auth/login", {
    data: { username, password },
  });
  expect(login.ok()).toBe(true);
  const headers = {
    Authorization: `Bearer ${(await login.json()).access_token}`,
  };
  const response = await request.get("/api/v1/catalog/categories");
  expect(response.ok()).toBe(true);
  const categories = (await response.json()) as Category[];
  const panels = categories.find((category) => category.slug === "panels")!;
  const materials = ["Метал", "Пластик", "АБС-пластик"];
  const protection = ["IP20", "IP31", "IP40", "IP44", "IP54", "IP65"];
  const created: string[] = [];
  try {
    // The regular seed is intentionally small and is not an imported catalog.
    for (const [index, ip] of protection.entries()) {
      const product = await request.post("/api/v1/admin/catalog/products", {
        headers,
        data: {
          category_id: panels.id,
          sku: `FACET-${testInfo.project.name}-${Date.now()}-${index}`,
          name: `Перевірка фільтрів ${ip}`,
          brand: "E2E Taxonomy",
          price: "100.00",
          specs: {
            Матеріал: materials[index % materials.length],
            "Ступінь захисту IP": ip,
          },
        },
      });
      expect(product.status()).toBe(201);
      created.push((await product.json()).id);
    }
    for (const [key, expected] of [
      ["Матеріал", materials],
      ["Ступінь захисту IP", protection],
    ] as const) {
      const facets = await request.get("/api/v1/catalog/spec-facets", {
        params: { category: "panels", facet_key: key, page_size: 100 },
      });
      expect(facets.ok()).toBe(true);
      const options = (await facets.json()).items as Array<{
        value: string;
        count: number;
      }>;
      expect(options.length).toBeGreaterThan(0);
      expect(new Set(options.map((option) => option.value)).size).toBe(
        options.length,
      );
      expect(options.map((option) => option.value)).toEqual(
        expect.arrayContaining(expected),
      );
      for (const option of options) {
        expect(option.count).toBeGreaterThan(0);
        const products = await request.get("/api/v1/catalog/products", {
          params: {
            category: "panels",
            spec: JSON.stringify([key, option.value]),
            page_size: 1,
            include_facets: false,
          },
        });
        expect(products.ok()).toBe(true);
        expect((await products.json()).total).toBe(option.count);
      }
    }
  } finally {
    for (const id of created) {
      const hidden = await request.patch(
        `/api/v1/admin/catalog/products/${id}`,
        {
          headers,
          data: { is_active: false },
        },
      );
      expect(hidden.ok()).toBe(true);
    }
  }
});

test("subcategory preview expands, collapses and keeps selection visible", async ({
  page,
  request,
}) => {
  const categories = (await (
    await request.get("/api/v1/catalog/categories")
  ).json()) as Category[];
  const category = categories.find(
    (category) => category.slug === "lowvoltage",
  )!;
  const avr = category.subcategories.find((item) =>
    item.name.startsWith("АВР"),
  )!;
  // Exercise the overflow UI even when the small CI seed has fewer than
  // seven populated subcategories. API counts are tested separately above.
  category.subcategories = category.subcategories.map((item) => ({
    ...item,
    product_count: Math.max(1, item.product_count),
  }));
  expect(category.subcategories.length).toBeGreaterThan(6);
  await page.route("**/api/v1/catalog/categories", (route) =>
    route.fulfill({ json: categories }),
  );
  // The public HTML also embeds category data, so remove that seed to make
  // this UI-only fixture go through the intercepted API above.
  await page.route(
    (url) => url.pathname === "/catalog/lowvoltage",
    async (route) => {
      const response = await route.fetch();
      await route.fulfill({
        response,
        body: (await response.text()).replace(
          /<script id="public-catalog-data" type="application\/json">[\s\S]*?<\/script>/,
          "",
        ),
      });
    },
  );
  await page.goto(`/catalog/lowvoltage?subcategory=${avr.slug}`);
  const chips = page.getByRole("navigation", { name: "Підкатегорії" });
  await expect(chips.getByRole("link")).toHaveCount(6);
  await expect(chips.getByRole("link", { name: /АВР/ })).toHaveAttribute(
    "data-active",
    "true",
  );
  await chips.getByRole("button", { name: /^Ще/ }).click();
  await expect(chips.getByRole("link")).toHaveCount(
    category.subcategories.filter((item) => item.product_count > 0).length,
  );
  await chips.getByRole("button", { name: "Згорнути" }).click();
  await expect(chips.getByRole("link")).toHaveCount(6);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth + 1,
    ),
  ).toBe(true);
});

test("category changes clear dependent filters and all-products navigation resets the catalog", async ({
  page,
  request,
}) => {
  const categories = (await (
    await request.get("/api/v1/catalog/categories")
  ).json()) as Category[];
  const panels = categories.find((category) => category.slug === "panels")!;
  const subcategory = panels.subcategories.find(
    (item) => item.product_count > 0,
  )!;
  const params = new URLSearchParams({
    category: "panels",
    subcategory: subcategory.slug,
    spec: JSON.stringify(["Матеріал", "Метал"]),
    min_price: "10",
    max_price: "999",
    page: "2",
    section: "home-renovation",
    brand: "Hager",
  });
  await page.goto(`/catalog?${params}`);
  const mobile = (page.viewportSize()?.width ?? 1000) <= 820;
  if (mobile)
    await page.getByRole("button", { name: "Фільтри", exact: true }).click();
  await page
    .getByRole("combobox", { name: "Категорія", exact: true })
    .selectOption("lowvoltage");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(
    "Низьковольтне обладнання",
  );
  const next = new URL(page.url()).searchParams;
  for (const name of [
    "subcategory",
    "spec",
    "min_price",
    "max_price",
    "page",
    "section",
  ])
    expect(next.has(name)).toBe(false);
  expect(next.get("brand")).toBe("Hager");
  if (mobile) {
    await page.keyboard.press("Escape");
    await page.getByRole("button", { name: "Відкрити меню" }).click();
    const menu = page.getByRole("dialog", { name: "Головне меню" });
    await menu.getByRole("button", { name: "Каталог товарів" }).click();
    await menu.getByRole("link", { name: "Усі товари", exact: true }).click();
  } else {
    await page.locator(".catalog-nav__primary").click();
    await page
      .getByRole("navigation", { name: "Категорії товарів", exact: true })
      .getByRole("link", { name: /Переглянути всі товари/ })
      .click();
  }
  await expect(page).toHaveURL(/\/catalog$/);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(
    "Усі товари",
  );
  await expect(page.locator(".product-card").first()).toBeVisible();
});
