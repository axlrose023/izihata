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
});
