import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";
import { fetchProducts } from "@/modules/catalog/api/catalog-api";
import { productListFixture } from "@/tests/product-fixture";
import { PopularProducts } from "./popular-products";
vi.mock("@/modules/catalog/api/catalog-api", () => ({
  fetchProducts: vi.fn(async () => productListFixture()),
}));
vi.mock("@/shared/lib/use-in-view", () => ({
  useInView: () => ({ ref: vi.fn(), isVisible: true }),
}));
afterEach(cleanup);
function show() {
  render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      <MemoryRouter>
        <PopularProducts />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}
it("shows actual catalog products without assigning popularity or badges", async () => {
  show();
  await screen.findByText("Test product");
  expect(
    screen.getByRole("heading", { name: "Усі товари" }),
  ).toBeInTheDocument();
  expect(vi.mocked(fetchProducts).mock.calls[0][0]).toMatchObject({
    page: 1,
    page_size: 8,
    include_facets: false,
  });
  expect(vi.mocked(fetchProducts).mock.calls[0][0]).not.toHaveProperty(
    "is_popular",
  );
  expect(vi.mocked(fetchProducts).mock.calls[0][0]).not.toHaveProperty("badge");
});
it("shows retry for a failed request instead of an empty selection", async () => {
  vi.mocked(fetchProducts).mockRejectedValueOnce(new Error("failed"));
  show();
  await screen.findByRole("button", { name: "Повторити" });
  expect(
    screen.queryByText("У цій добірці поки порожньо."),
  ).not.toBeInTheDocument();
});
