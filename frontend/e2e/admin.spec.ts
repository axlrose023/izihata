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

// A 1x1 PNG, enough to prove the whole upload path works end to end.
const PNG_BASE64 =
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==";

test("hiding a product keeps it recoverable", async ({ page }) => {
  await login(page);
  await page
    .locator(".admin-sidebar")
    .getByRole("link", { name: "Товари" })
    .click();

  const row = page.locator(".admin-table tbody tr").first();
  await expect(row).toBeVisible();
  const name = (await row.locator("strong").innerText()).trim();

  // Hide it…
  await row.getByRole("button", { name: `Прибрати з вітрини ${name}` }).click();
  const hiddenRow = page
    .locator(".admin-table tbody tr")
    .filter({ hasText: name })
    .first();
  await expect(hiddenRow).toHaveAttribute("data-hidden", "true");

  // …it must still be listed for staff, otherwise hiding is a one-way door.
  await page.getByLabel("Лише приховані").check();
  await expect(
    page.locator(".admin-table tbody tr").filter({ hasText: name }).first(),
  ).toBeVisible();

  // …and restoring it must work from the same place.
  await page
    .locator(".admin-table tbody tr")
    .filter({ hasText: name })
    .first()
    .getByRole("button", { name: `Повернути на вітрину ${name}` })
    .click();
  await page.getByLabel("Лише приховані").uncheck();
  await expect(
    page.locator(".admin-table tbody tr").filter({ hasText: name }).first(),
  ).not.toHaveAttribute("data-hidden", "true");
});

test("staff can upload a product photo", async ({ page }) => {
  await login(page);
  await page
    .locator(".admin-sidebar")
    .getByRole("link", { name: "Товари" })
    .click();
  await page
    .getByRole("button", { name: /^Редагувати/ })
    .first()
    .click();

  const dialog = page.getByRole("dialog", { name: "Редагувати товар" });
  await expect(dialog).toBeVisible();
  // Upload immediately: the full product loads a moment later and must not
  // overwrite the photo that was just attached.
  await dialog.getByLabel("Файл зображення товару").setInputFiles({
    name: "product.png",
    mimeType: "image/png",
    buffer: Buffer.from(PNG_BASE64, "base64"),
  });

  const field = dialog.getByRole("textbox", { name: /^Зображення/ });
  await expect(field).toHaveValue(/^\/api\/v1\/media\//, { timeout: 20_000 });
  await expect(dialog.locator(".field-image-preview")).toBeVisible();

  const stored = await page.request.get(await field.inputValue());
  expect(stored.status()).toBe(200);
});

test("staff can upload a brand logo", async ({ page }) => {
  await login(page);
  await page
    .locator(".admin-sidebar")
    .getByRole("link", { name: "Бренди" })
    .click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Бренди");

  const row = page.locator(".admin-brands tbody tr").first();
  await expect(row).toBeVisible();
  await row.locator('input[type="file"]').setInputFiles({
    name: "logo.png",
    mimeType: "image/png",
    buffer: Buffer.from(PNG_BASE64, "base64"),
  });

  const logo = row.locator(".admin-brand__logo img");
  await expect(logo).toBeVisible({ timeout: 20_000 });
  const src = await logo.getAttribute("src");
  expect(src).toMatch(/^\/api\/v1\/media\//);

  // The stored file must actually be served back.
  const stored = await page.request.get(src!);
  expect(stored.status()).toBe(200);
  expect(stored.headers()["content-type"]).toContain("image");
});

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
    ["Бренди", "Бренди"],
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
