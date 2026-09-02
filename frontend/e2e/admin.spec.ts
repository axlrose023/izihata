import { expect, test, type Page, type TestInfo } from "@playwright/test";

async function login(page: Page) {
  const username = process.env.ADMIN_USERNAME;
  const password = process.env.ADMIN_PASSWORD;
  test.skip(!username || !password, "Admin credentials are not configured");

  await page.goto("/admin/login");
  await page.getByLabel("Логін").fill(username!);
  await page.getByLabel("Пароль").fill(password!);
  await page.getByRole("button", { name: "Увійти" }).click();
  await expect(page).toHaveURL(/\/admin$/);
}

async function createProduct(page: Page, testInfo: TestInfo) {
  await page
    .locator(".admin-sidebar")
    .getByRole("link", { name: "Товари" })
    .click();

  const suffix = `${testInfo.project.name}-${Date.now().toString(36)}`;
  const sku = `E2E-${suffix}`.toUpperCase();
  const name = `Тестовий контактор ${suffix}`;
  await page.getByRole("button", { name: "Додати товар" }).click();

  const dialog = page.getByRole("dialog", { name: "Додати товар" });
  await expect(dialog).toBeVisible();
  await dialog.getByLabel("SKU").fill(sku);
  await dialog.getByLabel("Бренд", { exact: true }).fill("E2E Electric");
  await dialog.getByLabel("Назва").fill(name);
  await dialog
    .getByRole("combobox", { name: /^Категорія/ })
    .selectOption({ index: 1 });
  await dialog
    .getByRole("combobox", { name: /^Підкатегорія/ })
    .selectOption({ index: 1 });
  await dialog.getByRole("spinbutton", { name: /^Ціна/ }).fill("749.50");
  await dialog
    .getByRole("textbox", { name: /^Зображення/ })
    .fill("/product-images/automation.svg");
  await dialog.getByRole("button", { name: "Додати характеристику" }).click();
  await dialog.getByLabel("Характеристика 1").fill("Напруга котушки");
  await dialog.getByLabel("Значення характеристики 1").fill("230 В");

  const createResponse = page.waitForResponse(
    (response) =>
      response.request().method() === "POST" &&
      new URL(response.url()).pathname === "/api/v1/admin/catalog/products",
  );
  await dialog.getByRole("button", { name: "Додати товар" }).click();
  expect((await createResponse).status()).toBe(201);

  await expect(dialog).not.toBeVisible();
  await expect(page.getByText(name)).toBeVisible();

  const publicResponse = await page.request.get(
    `/api/v1/catalog/products/${sku.toLowerCase()}`,
  );
  expect(publicResponse.status()).toBe(200);
  const product = (await publicResponse.json()) as {
    sku: string;
    name: string;
    specs: Record<string, string>;
  };
  expect(product).toMatchObject({
    sku,
    name,
    specs: { "Напруга котушки": "230 В" },
  });

  const updatedName = `${name} оновлений`;
  const row = page.getByRole("row", { name: new RegExp(name) });
  await row.getByRole("button", { name: `Редагувати ${name}` }).click();
  const editDialog = page.getByRole("dialog", { name: "Редагувати товар" });
  await editDialog.getByLabel("Назва").fill(updatedName);
  const updateResponse = page.waitForResponse(
    (response) =>
      response.request().method() === "PATCH" &&
      new URL(response.url()).pathname.startsWith(
        "/api/v1/admin/catalog/products/",
      ),
  );
  await editDialog.getByRole("button", { name: "Зберегти товар" }).click();
  expect((await updateResponse).status()).toBe(200);
  await expect(editDialog).not.toBeVisible();
  await expect(page.getByText(updatedName)).toBeVisible();

  const updatedResponse = await page.request.get(
    `/api/v1/catalog/products/${sku.toLowerCase()}`,
  );
  expect(updatedResponse.status()).toBe(200);
  expect((await updatedResponse.json()).name).toBe(updatedName);
}

test("staff can manage modules and create and edit a product", async ({
  page,
}, testInfo) => {
  const authRequests: string[] = [];
  page.on("request", (request) => {
    if (request.url().includes("/api/v1/auth/")) {
      authRequests.push(new URL(request.url()).pathname);
    }
  });

  await login(page);
  await expect(page.locator(".metric-card").first()).toBeVisible();
  expect(authRequests).toContain("/api/v1/auth/refresh");
  expect(authRequests).toContain("/api/v1/auth/login");
  expect(authRequests.every((path) => !path.includes("/session/"))).toBe(true);

  for (const [navigationLabel, heading] of [
    ["Товари", "Товари"],
    ["Замовлення", "Замовлення"],
    ["Звернення", "Звернення"],
    ["Відгуки", "Відгуки"],
    ["Активність", "Активність"],
    ["Компанії", "Компанії"],
    ["Щити", "Щити на замовлення"],
  ] as const) {
    await page
      .locator(".admin-sidebar")
      .getByRole("link", { name: navigationLabel })
      .click();
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(heading);
    await expect(page.locator(".admin-table")).toBeVisible();
  }

  await createProduct(page, testInfo);
});
