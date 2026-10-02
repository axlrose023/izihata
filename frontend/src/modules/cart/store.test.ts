import { beforeEach, describe, expect, it } from "vitest";

import type { Product } from "@/shared/types/api";

import { cartCount, useCartStore } from "./store";

const product: Product = {
  id: "c4a06a4b-6d5b-4c13-b9b4-700f2e266466",
  sku: "TEST-1",
  slug: "test-product",
  name: "Test product",
  brand: "Test",
  brand_country: null,
  production_country: null,
  short_description: null,
  image_url: null,
  price: "100.00",
  old_price: null,
  badge: null,
  stock_status: "in_stock",
  availability: {
    status: "in_stock",
    lead_time_days: null,
    dispatch_cutoff_hour: null,
  },
  sale_unit: "piece",
  wholesale_min_quantity: null,
  rating: "5.0",
  reviews_count: 0,
  category: { id: "cat", slug: "tools", name: "Tools" },
  subcategory: null,
  specs: {},
};

describe("cart store", () => {
  beforeEach(() => useCartStore.setState({ lines: [], isOpen: false }));

  it("merges duplicate products and opens the cart", () => {
    useCartStore.getState().add(product, 2);
    useCartStore.getState().add(product, 3);

    expect(useCartStore.getState().lines).toEqual([{ product, quantity: 5 }]);
    expect(useCartStore.getState().isOpen).toBe(true);
    expect(cartCount(useCartStore.getState().lines)).toBe(5);
  });

  it("clamps quantity and removes a line", () => {
    useCartStore.getState().add(product);
    useCartStore.getState().setQuantity(product.id, 0);
    expect(useCartStore.getState().lines[0].quantity).toBe(1);

    useCartStore.getState().remove(product.id);
    expect(useCartStore.getState().lines).toHaveLength(0);
  });
  it("normalizes fractional, negative and non-finite quantities", () => {
    useCartStore.getState().add(product, 1.5);
    expect(useCartStore.getState().lines[0].quantity).toBe(1);
    useCartStore.getState().setQuantity(product.id, 3.9);
    expect(useCartStore.getState().lines[0].quantity).toBe(3);
    useCartStore.getState().setQuantity(product.id, Number.NaN);
    expect(useCartStore.getState().lines[0].quantity).toBe(1);
    useCartStore.getState().add(product, -5);
    expect(useCartStore.getState().lines[0].quantity).toBe(2);
  });
  it("repairs persisted fractional quantities without losing the product", async () => {
    localStorage.setItem(
      "izihata-cart-v1",
      JSON.stringify({
        state: { lines: [{ product, quantity: 2.5 }] },
        version: 0,
      }),
    );
    await useCartStore.persist.rehydrate();
    expect(useCartStore.getState().lines).toEqual([{ product, quantity: 2 }]);
  });
  it("rejects a new line over the limit but permits existing quantities", () => {
    for (let index = 0; index < 100; index++)
      expect(
        useCartStore.getState().add({ ...product, id: String(index) }),
      ).toBe(true);
    expect(useCartStore.getState().add({ ...product, id: "overflow" })).toBe(
      false,
    );
    expect(useCartStore.getState().lines).toHaveLength(100);
    expect(useCartStore.getState().error).toContain("100");
    expect(useCartStore.getState().add({ ...product, id: "0" })).toBe(true);
    expect(useCartStore.getState().lines[0].quantity).toBe(2);
  });
  it("adds a bundle atomically and retains oversized persisted carts for editing", async () => {
    const lines = Array.from({ length: 101 }, (_, index) => ({
      product: { ...product, id: String(index) },
      quantity: 1,
    }));
    localStorage.setItem(
      "izihata-cart-v1",
      JSON.stringify({ state: { lines }, version: 0 }),
    );
    await useCartStore.persist.rehydrate();
    expect(useCartStore.getState().lines).toHaveLength(101);
    useCartStore.getState().remove("100");
    useCartStore.getState().remove("99");
    expect(
      useCartStore.getState().addMany([
        { product: { ...product, id: "new-1" }, quantity: 1 },
        { product: { ...product, id: "new-2" }, quantity: 1 },
      ]),
    ).toBe(false);
    expect(useCartStore.getState().lines).toHaveLength(99);
  });
});

it("refreshes current prices without changing quantities or reviving removed products", () => {
  const store = useCartStore.getState();
  store.clear();
  store.add(product, 3);
  const second = { ...product, id: "second" };
  store.add(second, 2);
  store.remove(second.id);
  store.refreshProducts(
    [{ ...product, price: "120.00" }, second],
    [product.id, second.id],
  );
  expect(useCartStore.getState().lines).toEqual([
    { product: { ...product, price: "120.00" }, quantity: 3 },
  ]);
  store.refreshProducts([], [product.id]);
  expect(useCartStore.getState().lines).toHaveLength(1);
});
