import { expect, test } from "@playwright/test";

const cartModule =
  /(?:\/assets\/cart-drawer-[^/]+\.js|\/src\/modules\/cart\/components\/cart-drawer\.tsx)(?:\?|$)/;
const leadModule =
  /(?:\/assets\/lead-dialog-[^/]+\.js|\/src\/modules\/leads\/components\/lead-dialog\.tsx)(?:\?|$)/;

test("idle preparation leaves overlays closed and makes them usable offline", async ({
  page,
  context,
}) => {
  const cartReady = page.waitForResponse((response) =>
    cartModule.test(response.url()),
  );
  const leadReady = page.waitForResponse((response) =>
    leadModule.test(response.url()),
  );
  const cartPriceRequests: string[] = [];
  page.on("request", (request) => {
    const url = new URL(request.url());
    if (
      url.pathname === "/api/v1/catalog/products" &&
      url.searchParams.has("id")
    ) {
      cartPriceRequests.push(request.url());
    }
  });
  await page.goto("/");
  await Promise.all([cartReady, leadReady]);
  await page.waitForLoadState("networkidle");
  expect(cartPriceRequests).toEqual([]);
  await expect(page.getByRole("dialog")).toHaveCount(0);

  const laterScripts: string[] = [];
  page.on("request", (request) => {
    if (request.resourceType() === "script") laterScripts.push(request.url());
  });
  await context.setOffline(true);
  try {
    await page.getByRole("button", { name: "Кошик: 0", exact: true }).click();
    const cart = page.getByRole("dialog", { name: "Кошик", exact: true });
    await expect(cart).toBeVisible();
    await expect(cart.getByText("У кошику поки порожньо")).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(cart).toBeHidden();
    await page.locator(".support-button").click();
    await expect(page.getByRole("textbox", { name: "Ім’я" })).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(page.getByRole("dialog")).toHaveCount(0);
    expect(laterScripts).toEqual([]);
    expect(cartPriceRequests).toEqual([]);
  } finally {
    await context.setOffline(false);
  }
});

test("preparation does not revalidate a saved basket until opened", async ({
  page,
  request,
}) => {
  const response = await request.get(
    "/api/v1/catalog/products?page_size=1&include_facets=false",
  );
  expect(response.ok()).toBe(true);
  const product = (await response.json()).items[0];
  await page.addInitScript((savedProduct) => {
    localStorage.setItem(
      "izihata-cart-v1",
      JSON.stringify({
        state: { lines: [{ product: savedProduct, quantity: 2 }] },
        version: 0,
      }),
    );
  }, product);
  const cartReady = page.waitForResponse((response) =>
    cartModule.test(response.url()),
  );
  const priceRequests: string[] = [];
  page.on("request", (request) => {
    const url = new URL(request.url());
    if (
      url.pathname === "/api/v1/catalog/products" &&
      url.searchParams.has("id")
    ) {
      priceRequests.push(request.url());
    }
  });
  await page.goto("/");
  await cartReady;
  await page.waitForLoadState("networkidle");
  expect(priceRequests).toEqual([]);
  await expect(page.getByRole("dialog")).toHaveCount(0);

  const revalidate = page.waitForRequest((request) =>
    new URL(request.url()).searchParams.getAll("id").includes(product.id),
  );
  await page.getByRole("button", { name: "Кошик: 2", exact: true }).click();
  await revalidate;
  const cart = page.getByRole("dialog", { name: "Кошик", exact: true });
  await expect(cart.getByRole("link", { name: product.name })).toBeVisible();
  await expect(cart.locator(".quantity-control > span")).toHaveText("2");
  await page.keyboard.press("Escape");
  await expect(cart).toBeHidden();
});
