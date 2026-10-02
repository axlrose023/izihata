import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";
import { productFixture } from "@/tests/product-fixture";
import { CatalogPage } from "./catalog-page";
vi.mock("@/modules/catalog/api/catalog-api", () => ({
  fetchCategories: async () => [
    { id: "cat", slug: "tools", name: "Tools", subcategories: [] },
  ],
  fetchProducts: async () => ({
    items: [productFixture()],
    total: 1,
    total_pages: 1,
    page: 1,
    page_size: 24,
    has_next: false,
    has_prev: false,
  }),
}));
vi.mock("@/modules/catalog/components/catalog-filters", () => ({
  CatalogFilters: () => null,
}));
afterEach(cleanup);
it("preserves repeated filters and resets only pagination during mobile search", async () => {
  const router = createMemoryRouter(
    [{ path: "/catalog/:category", element: <CatalogPage /> }],
    {
      initialEntries: [
        "/catalog/tools?brand=Hager&brand=ETI&spec=x:16&sort=price_asc&page=3",
      ],
    },
  );
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={client}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
  const input = await screen.findByRole("textbox", {
    name: "Пошук у каталозі",
  });
  fireEvent.change(input, { target: { value: "автомат" } });
  fireEvent.submit(input.closest("form")!);
  await waitFor(() =>
    expect(router.state.location.search).toContain("search="),
  );
  const params = new URLSearchParams(router.state.location.search);
  expect(params.getAll("brand")).toEqual(["Hager", "ETI"]);
  expect(params.get("spec")).toBe("x:16");
  expect(params.get("sort")).toBe("price_asc");
  expect(params.has("page")).toBe(false);
});
