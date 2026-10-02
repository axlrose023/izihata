import { QueryClient } from "@tanstack/react-query";
import { afterEach, expect, it, vi } from "vitest";
import { fetchProduct } from "./catalog-api";
import { productQuery } from "./catalog-queries";
import { publicCatalogSeed } from "./public-catalog-seed";
import { productDetailFixture } from "@/tests/product-fixture";
vi.mock("./catalog-api", () => ({
  fetchProduct: vi.fn(),
  fetchProducts: vi.fn(),
  fetchCategories: vi.fn(),
  fetchSections: vi.fn(),
  fetchBrands: vi.fn(),
  fetchFeaturedReviews: vi.fn(),
}));
afterEach(() => {
  document.getElementById("public-catalog-data")?.remove();
  vi.useRealTimers();
});
function seed(data: unknown) {
  document.getElementById("public-catalog-data")?.remove();
  const script = document.createElement("script");
  script.id = "public-catalog-data";
  script.type = "application/json";
  script.textContent = typeof data === "string" ? data : JSON.stringify(data);
  document.body.append(script);
}
it("matches reordered query parameters while retaining repeated filters", () => {
  seed({ "/catalog/products?brand=Hager&brand=ETI&page=2": { total: 4 } });
  expect(
    publicCatalogSeed("/catalog/products?page=2&brand=Hager&brand=ETI")
      .initialData,
  ).toEqual({ total: 4 });
  expect(
    publicCatalogSeed("/catalog/products?page=1&brand=Hager&brand=ETI")
      .initialData,
  ).toBeUndefined();
});
it("falls back to the API for malformed data and ignores private resources", () => {
  seed("bad JSON");
  expect(publicCatalogSeed("/catalog/categories")).toEqual({});
  seed({
    "/customers/me": { email: "private" },
    "/catalog/../customers/me": { email: "private" },
  });
  expect(publicCatalogSeed("/customers/me")).toEqual({});
});
it("keeps the receipt timestamp so old seeds cannot become freshly cached on navigation", () => {
  vi.useFakeTimers();
  seed({ "/catalog/categories": [] });
  const first = publicCatalogSeed("/catalog/categories");
  vi.advanceTimersByTime(600_000);
  expect(publicCatalogSeed("/catalog/categories").initialDataUpdatedAt).toBe(
    first.initialDataUpdatedAt,
  );
});
it("uses a fresh product seed without a duplicate request", async () => {
  const product = productDetailFixture();
  seed({ ["/catalog/products/" + product.slug]: product });
  const client = new QueryClient();
  expect(await client.fetchQuery(productQuery(product.slug))).toEqual(product);
  expect(fetchProduct).not.toHaveBeenCalled();
});
