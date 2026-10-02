import type { Product } from "@/shared/types/api";

export function productFixture(overrides: Partial<Product> = {}): Product {
  return {
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
    ...overrides,
  };
}
