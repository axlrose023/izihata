import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

const pages = [
  {
    path: "/delivery-and-payment",
    title: "Доставка й оплата",
    headings: ["Доставка", "Оплата"],
  },
  {
    path: "/warranty-return",
    title: "Гарантія та повернення",
    headings: [
      "Гарантійні умови",
      "Повернення товару та коштів",
      "Повернення онлайн-платежів",
    ],
  },
  {
    path: "/terms-of-use",
    title: "Умови користування сайтом",
    headings: [
      "Загальні умови",
      "Зв’язок із магазином",
      "Ціни та наявність товарів",
      "Оформлення замовлення",
      "Доставка товару",
      "Повернення товару",
      "Конфіденційність і захист персональних даних",
      "Cookies і збереження даних у браузері",
      "Прикінцеві положення",
    ],
  },
];

test("footer policies open with working navigation, metadata and a contact form", async ({
  page,
}) => {
  await page.goto("/");
  for (const policy of pages) {
    await page
      .locator(".site-footer")
      .getByRole("link", { name: policy.title, exact: true })
      .click();
    await expect(page).toHaveURL(new RegExp(`${policy.path}$`));
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(
      policy.title,
    );
    await expect(page).toHaveTitle(`${policy.title} | IZI HATA`);
    await expect(
      page.locator(".policy-navigation").getByRole("link", {
        name: policy.title,
        exact: true,
      }),
    ).toHaveAttribute("aria-current", "page");
    for (const heading of policy.headings) {
      await expect(
        page.getByRole("heading", { name: heading, exact: true }),
      ).toBeVisible();
    }
  }
  await page.getByRole("button", { name: "Зв’язатися з менеджером" }).click();
  await expect(page.getByRole("textbox", { name: "Ім’я" })).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);
});

test("direct policy links and reloads work without catalog queries or overflow", async ({
  page,
}) => {
  const catalogRequests: string[] = [];
  page.on("request", (request) => {
    if (new URL(request.url()).pathname.startsWith("/api/v1/catalog/")) {
      catalogRequests.push(request.url());
    }
  });
  for (const policy of pages) {
    const response = await page.goto(policy.path);
    expect(response?.status()).toBe(200);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(
      policy.title,
    );
    for (const width of [320, 390, 820, 1024]) {
      await page.setViewportSize({ width, height: 844 });
      expect(
        await page.evaluate(() => document.documentElement.scrollWidth),
      ).toBeLessThanOrEqual(width + 1);
    }
    await page.reload();
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(
      policy.title,
    );
    await expect(page.locator('link[rel="canonical"]')).toHaveAttribute(
      "href",
      new URL(policy.path, page.url()).href,
    );
    const result = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
      .analyze();
    expect(result.violations, JSON.stringify(result.violations)).toEqual([]);
  }
  expect(catalogRequests).toEqual([]);
});

test("checkout policies open separately and preserve entered order details", async ({
  page,
}) => {
  await page.goto("/catalog");
  await page
    .locator(".product-card")
    .first()
    .getByRole("button", {
      name: "Додати в кошик",
      exact: true,
    })
    .click();
  await page
    .getByRole("dialog", { name: "Кошик", exact: true })
    .getByRole("link", { name: "Оформити замовлення", exact: true })
    .click();
  const name = page.getByLabel("Ім’я та прізвище");
  await name.fill("Перевірка умов");
  const consent = page.locator(".checkout-consent");
  for (const policy of pages) {
    await expect(consent.locator(`a[href="${policy.path}"]`)).toHaveAttribute(
      "target",
      "_blank",
    );
  }
  const popup = page.waitForEvent("popup");
  await consent.locator('a[href="/terms-of-use"]').click();
  const terms = await popup;
  await expect(terms.getByRole("heading", { level: 1 })).toHaveText(
    "Умови користування сайтом",
  );
  await terms.close();
  await expect(name).toHaveValue("Перевірка умов");
  await expect(page).toHaveURL(/\/checkout$/);
});
