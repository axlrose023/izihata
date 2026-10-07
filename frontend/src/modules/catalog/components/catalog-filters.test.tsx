import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import {
  createMemoryRouter,
  RouterProvider,
  useSearchParams,
} from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";
import { CatalogFilters } from "./catalog-filters";

vi.mock("@/shared/api/client", () => ({
  apiClient: vi.fn(async () => ({
    brands: [],
    availability: [],
    sale_units: [],
    specs: {},
    price: { minimum: null, maximum: null },
  })),
}));
vi.mock("./catalog-spec-filters", () => ({ CatalogSpecFilters: () => null }));
afterEach(cleanup);

it("clears category-specific filters and retains independent choices", () => {
  const categories = ["panels", "lowvoltage"].map((slug) => ({
    id: slug,
    slug,
    name: slug,
    description: "",
    accent: "gold",
    icon: "",
    position: 0,
    product_count: 1,
    subcategories: [],
  }));
  function Filters() {
    const [params] = useSearchParams();
    return (
      <CatalogFilters
        action="/catalog"
        categories={categories}
        activeCategory={categories.find(
          (item) => item.slug === params.get("category"),
        )}
        categoryIsRouteParam={false}
        params={{ category: params.get("category") ?? undefined }}
        total={1}
        query={{
          brand: params.getAll("brand"),
          availability: [],
          sale_unit: [],
          spec: params.getAll("spec"),
          min_price: params.get("min_price") ?? undefined,
          max_price: params.get("max_price") ?? undefined,
        }}
      />
    );
  }
  const router = createMemoryRouter(
    [{ path: "/catalog", element: <Filters /> }],
    {
      initialEntries: [
        "/catalog?category=panels&subcategory=panels-1&section=installation&spec=x&min_price=10&max_price=20&page=3&brand=Hager&brand=ETI&search=test&sort=price_asc",
      ],
    },
  );
  render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
  fireEvent.change(screen.getByRole("combobox", { name: "Категорія" }), {
    target: { value: "lowvoltage" },
  });
  const params = new URLSearchParams(router.state.location.search);
  expect(params.get("category")).toBe("lowvoltage");
  for (const name of [
    "subcategory",
    "section",
    "spec",
    "min_price",
    "max_price",
    "page",
  ])
    expect(params.has(name)).toBe(false);
  expect(params.getAll("brand")).toEqual(["Hager", "ETI"]);
  expect(params.get("search")).toBe("test");
  expect(params.get("sort")).toBe("price_asc");
  fireEvent.change(screen.getByRole("combobox", { name: "Категорія" }), {
    target: { value: "" },
  });
  expect(
    new URLSearchParams(router.state.location.search).has("category"),
  ).toBe(false);
});
