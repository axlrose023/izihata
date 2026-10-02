import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";
import { productListFixture } from "@/tests/product-fixture";
import { fetchProducts } from "@/modules/catalog/api/catalog-api";
import { ApiError } from "@/shared/api/errors";
import { CatalogPage } from "./catalog-page";
vi.mock("@/modules/catalog/api/catalog-api", () => ({
  fetchCategories: async () => [
    { id: "cat", slug: "tools", name: "Tools", subcategories: [] },
  ],
  fetchProducts: vi.fn(async () => productListFixture()),
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

it("marks retained results as updating and exposes a failed refresh", async () => {
  vi.mocked(fetchProducts).mockResolvedValue(productListFixture());
  const router = createMemoryRouter(
    [{ path: "/catalog", element: <CatalogPage /> }],
    { initialEntries: ["/catalog"] },
  );
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const view = render(
    <QueryClientProvider client={client}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
  await screen.findByRole("textbox", { name: "Пошук у каталозі" });
  let resolve!: (value: ReturnType<typeof productListFixture>) => void;
  vi.mocked(fetchProducts).mockImplementationOnce(
    () =>
      new Promise((done) => {
        resolve = done;
      }),
  );
  await act(async () => {
    await router.navigate("/catalog?search=new");
  });
  await screen.findByText("Оновлюємо товари за обраними умовами…");
  expect(view.container.querySelector(".catalog-results")).toHaveAttribute(
    "aria-busy",
    "true",
  );
  expect(view.container.querySelectorAll(".product-card")).toHaveLength(1);
  await act(async () => {
    resolve(productListFixture());
  });
  await waitFor(() =>
    expect(view.container.querySelector(".catalog-results")).toHaveAttribute(
      "aria-busy",
      "false",
    ),
  );
  vi.mocked(fetchProducts).mockRejectedValueOnce(
    new ApiError(503, "Unavailable", undefined, "service_unavailable"),
  );
  await act(async () => {
    await client.invalidateQueries({ queryKey: ["catalog", "products"] });
  });
  await screen.findByRole("alert");
  expect(screen.getByRole("button", { name: "Повторити" })).toBeInTheDocument();
});
