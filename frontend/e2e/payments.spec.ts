import { expect, test } from "@playwright/test";

// Browser-only payment fixtures: no order or transaction reaches the shop/PSP.
for (const outcome of [
  "approved",
  "pending",
  "declined",
  "closed",
  "script-error",
] as const) {
  test(`WayForPay checkout handles ${outcome}`, async ({ page }) => {
    let orders = 0;
    let widgetOpened = 0;
    await page.exposeFunction("paymentWidgetOpened", () => {
      widgetOpened++;
    });
    await page.route("**/api/v1/payments/availability", (route) =>
      route.fulfill({ json: { online_card_enabled: true, test_mode: true } }),
    );
    await page.route(
      "https://secure.wayforpay.com/server/pay-widget.js",
      (route) => {
        if (outcome === "script-error") return route.abort();
        return route.fulfill({
          contentType: "application/javascript",
          body: `window.Wayforpay = class {
          closeit() { document.getElementById('wfp-container')?.remove(); document.body.classList.remove('wfp-widget-open'); }
          invoice() {
          const container = document.createElement('div'); container.id = 'wfp-container'; document.body.append(container); document.body.classList.add('wfp-widget-open');
          window.paymentWidgetOpened().then(() => window.dispatchEvent(new MessageEvent("message", {origin:"https://secure.wayforpay.com", data:"WfpWidgetEvent${outcome === "closed" ? "Close" : outcome.charAt(0).toUpperCase() + outcome.slice(1)}"})));
      }};`,
        });
      },
    );
    await page.route("**/api/v1/orders", async (route) => {
      orders += 1;
      const payload = route.request().postDataJSON();
      expect(payload.payment_method).toBe("card");
      await route.fulfill({
        status: 201,
        json: {
          number: "IZI-20261117-0123456789",
          total: payload.expected_total,
          payment_method: "card",
          delivery: { method: "pickup" },
          payment_attempt_id: "11111111-1111-4111-8111-111111111111",
          payment_widget: {
            invoiceUrl: "https://secure.wayforpay.com/invoice/test",
          },
        },
      });
    });
    await page.route("**/api/v1/payments/wayforpay/*", (route) =>
      route.fulfill({
        json: {
          attempt_id: "11111111-1111-4111-8111-111111111111",
          status:
            outcome === "approved" && widgetOpened > 0
              ? "paid"
              : outcome === "declined" && widgetOpened > 0
                ? "failed"
                : "pending",
          is_test: true,
          invoice_url:
            outcome === "approved" && widgetOpened > 0
              ? null
              : "https://secure.wayforpay.com/invoice/test",
        },
      }),
    );
    await page.goto("/catalog", { waitUntil: "domcontentloaded" });
    await page.getByRole("button", { name: "Додати в кошик" }).first().click();
    await page.goto("/checkout", { waitUntil: "domcontentloaded" });
    await expect(page.getByText(/Тестовий режим WayForPay/)).toBeVisible();
    await page.locator('input[name="customer_name"]').fill("Тест Оплати");
    await page
      .locator('input[name="email"]')
      .fill("payment-test@example.invalid");
    await page.locator('input[name="phone"]').fill("+380501234567");
    await page.getByRole("radio", { name: /Самовивіз/ }).check();
    await page.getByRole("radio", { name: /Карткою онлайн/ }).check();
    await expect(
      page.getByText(
        "Після підтвердження замовлення відкриється платіжне вікно.",
      ),
    ).toBeVisible();
    await page.getByRole("button", { name: "Підтвердити замовлення" }).click();
    if (outcome !== "script-error") {
      await expect(page).toHaveURL(/\/order\/success\?/);
      await expect(page.getByText(/Тестова оплата WayForPay/)).toBeVisible();
      await expect(
        page
          .getByText(
            outcome === "approved"
              ? /Оплату успішно отримано/
              : /Оплату ще не підтверджено|Оплату не підтверджено/,
          )
          .first(),
      ).toBeVisible();
    } else {
      await expect(
        page
          .getByText(
            outcome === "declined" ? /Оплату не підтверджено/ : /Не вдалося/,
          )
          .first(),
      ).toBeVisible();
      await expect(page).toHaveURL(/\/checkout$/);
      await expect(page.locator(".order-summary__line").first()).toBeVisible();
    }
    expect(orders).toBe(outcome === "script-error" ? 0 : 1);
    await expect
      .poll(() => widgetOpened)
      .toBe(outcome === "script-error" ? 0 : 1);
    await expect(page.locator("#wfp-container")).toHaveCount(0);
    await expect(page.locator("body")).not.toHaveClass(/wfp-widget-open/);
  });
}

test("closing and reopening payment reuses the invoice and creates one order", async ({
  page,
}) => {
  let orders = 0;
  const invoices: string[] = [];
  await page.route("**/api/v1/payments/availability", (route) =>
    route.fulfill({ json: { online_card_enabled: true, test_mode: true } }),
  );
  await page.exposeFunction("recordInvoice", (url: string) =>
    invoices.push(url),
  );
  await page.route(
    "https://secure.wayforpay.com/server/pay-widget.js",
    (route) =>
      route.fulfill({
        contentType: "application/javascript",
        body: `window.Wayforpay = class {
        closeit() { document.getElementById('wfp-container')?.remove(); }
        invoice(url) {
          window.recordInvoice(url);
          const container = document.createElement('div'); container.id = 'wfp-container'; document.body.append(container);
          window.invoiceOpenCount = (window.invoiceOpenCount || 0) + 1;
          if (window.invoiceOpenCount !== 2) setTimeout(() => window.dispatchEvent(new MessageEvent('message', {origin:'https://secure.wayforpay.com', data:'WfpWidgetEventClose'})), 0);
        }
      };`,
      }),
  );
  await page.route("**/api/v1/orders", async (route) => {
    orders++;
    const payload = route.request().postDataJSON();
    await route.fulfill({
      status: 201,
      json: {
        number: "IZI-20261117-0123456789",
        total: payload.expected_total,
        payment_method: "card",
        delivery: { method: "pickup" },
        payment_attempt_id: "11111111-1111-4111-8111-111111111111",
        payment_widget: {
          invoiceUrl: "https://secure.wayforpay.com/invoice/test",
        },
      },
    });
  });
  await page.route("**/api/v1/payments/wayforpay/*", (route) =>
    route.fulfill({
      json: {
        status: "pending",
        is_test: true,
        invoice_url: "https://secure.wayforpay.com/invoice/test",
      },
    }),
  );
  await page.goto("/catalog", { waitUntil: "domcontentloaded" });
  await page.getByRole("button", { name: "Додати в кошик" }).first().click();
  await page.goto("/checkout", { waitUntil: "domcontentloaded" });
  await page.locator('input[name="customer_name"]').fill("Тест Оплати");
  await page
    .locator('input[name="email"]')
    .fill("payment-test@example.invalid");
  await page.locator('input[name="phone"]').fill("+380501234567");
  await page.getByRole("radio", { name: /Самовивіз/ }).check();
  await page.getByRole("radio", { name: /Карткою онлайн/ }).check();
  await page.getByRole("button", { name: "Підтвердити замовлення" }).click();
  await expect(page).toHaveURL(/\/order\/success\?/);
  await page.getByRole("button", { name: "Перейти до оплати" }).click();
  await expect.poll(() => invoices.length).toBe(2);
  await expect(page.locator("#wfp-container")).toHaveCount(1);
  expect(invoices[0]).toBe(invoices[1]);
  expect(orders).toBe(1);
  await page.reload();
  await expect(
    page.getByRole("button", { name: "Перейти до оплати" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Перейти до оплати" }).click();
  await expect.poll(() => invoices.length).toBe(3);
  expect(invoices[2]).toBe(invoices[0]);
  expect(orders).toBe(1);
});

test("online payment is described by method, not by provider", async ({
  page,
}) => {
  await page.route("**/api/v1/payments/availability", (route) =>
    route.fulfill({ json: { online_card_enabled: true, test_mode: false } }),
  );
  await page.goto("/catalog", { waitUntil: "domcontentloaded" });
  await page.getByRole("button", { name: "Додати в кошик" }).first().click();
  await page.goto("/checkout", { waitUntil: "domcontentloaded" });
  const payment = page.locator(".checkout-card--payment");
  await expect(payment.getByRole("radio")).toHaveCount(3);
  await expect(payment.getByText("WayForPay")).toHaveCount(0);
  await payment.getByRole("radio", { name: /Карткою онлайн/ }).check();
  await expect(
    payment.getByText(
      "Після підтвердження замовлення відкриється платіжне вікно.",
    ),
  ).toBeVisible();
});

test("card checkout is unavailable without merchant credentials", async ({
  page,
}) => {
  await page.route("**/api/v1/payments/availability", (route) =>
    route.fulfill({ json: { online_card_enabled: false } }),
  );
  await page.goto("/catalog", { waitUntil: "domcontentloaded" });
  await page.getByRole("button", { name: "Додати в кошик" }).first().click();
  await page.goto("/checkout", { waitUntil: "domcontentloaded" });
  const card = page.getByRole("radio", { name: /Карткою онлайн/ });
  await expect(card).toBeDisabled();
  await expect(card.locator("..")).toHaveCSS("cursor", "not-allowed");
  await expect(page.getByText("Тимчасово недоступна")).toBeVisible();
});
