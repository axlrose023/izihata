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
    await page.route("**/api/v1/payments/availability", (route) =>
      route.fulfill({ json: { online_card_enabled: true } }),
    );
    await page.route(
      "https://secure.wayforpay.com/server/pay-widget.js",
      (route) => {
        if (outcome === "script-error") return route.abort();
        return route.fulfill({
          contentType: "application/javascript",
          body: `window.Wayforpay = class {
          closeit() { document.getElementById('wfp-container')?.remove(); document.body.classList.remove('wfp-widget-open'); }
          run(parameters, approved, declined, pending) {
          const container = document.createElement('div'); container.id = 'wfp-container'; document.body.append(container); document.body.classList.add('wfp-widget-open');
        ${outcome === "closed" ? 'window.dispatchEvent(new MessageEvent("message", {origin:"https://secure.wayforpay.com", data:"WfpWidgetEventClose"}));' : `${outcome}({});`}
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
          payment_widget: { merchantAccount: "browser-fixture" },
        },
      });
    });
    await page.route("**/api/v1/payments/wayforpay/*", (route) =>
      route.fulfill({
        json: {
          attempt_id: "11111111-1111-4111-8111-111111111111",
          status:
            outcome === "approved"
              ? "paid"
              : outcome === "declined"
                ? "failed"
                : "pending",
        },
      }),
    );
    await page.goto("/catalog");
    await page.getByRole("button", { name: "Додати в кошик" }).first().click();
    await page.goto("/checkout");
    await page.locator('input[name="customer_name"]').fill("Тест Оплати");
    await page
      .locator('input[name="email"]')
      .fill("payment-test@example.invalid");
    await page.locator('input[name="phone"]').fill("+380501234567");
    await page.getByRole("radio", { name: /Самовивіз/ }).check();
    await page.getByRole("radio", { name: /Карткою/ }).check();
    await page.getByRole("button", { name: "Підтвердити замовлення" }).click();
    if (outcome === "approved" || outcome === "pending") {
      await expect(page).toHaveURL(/\/order\/success\?/);
      await expect(
        page
          .getByText(
            outcome === "approved"
              ? /Оплату успішно отримано/
              : /Платіж обробляється/,
          )
          .first(),
      ).toBeVisible();
    } else {
      await expect(
        page
          .getByText(
            outcome === "declined"
              ? /Оплату не підтверджено/
              : outcome === "closed"
                ? /Платіжне вікно закрито/
                : /Не вдалося/,
          )
          .first(),
      ).toBeVisible();
      await expect(page).toHaveURL(/\/checkout$/);
      await expect(page.locator(".order-summary__line").first()).toBeVisible();
    }
    expect(orders).toBe(outcome === "script-error" ? 0 : 1);
    await expect(page.locator("#wfp-container")).toHaveCount(0);
    await expect(page.locator("body")).not.toHaveClass(/wfp-widget-open/);
  });
}

test("card checkout is unavailable without merchant credentials", async ({
  page,
}) => {
  await page.route("**/api/v1/payments/availability", (route) =>
    route.fulfill({ json: { online_card_enabled: false } }),
  );
  await page.goto("/catalog");
  await page.getByRole("button", { name: "Додати в кошик" }).first().click();
  await page.goto("/checkout");
  await expect(page.getByRole("radio", { name: /Карткою/ })).toBeDisabled();
  await expect(page.getByText("Тимчасово недоступна")).toBeVisible();
});
