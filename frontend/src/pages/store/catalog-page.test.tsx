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
import {
  fetchCategories,
  fetchProducts,
} from "@/modules/catalog/api/catalog-api";
import { ApiError } from "@/shared/api/errors";
import { CatalogPage } from "./catalog-page";
vi.mock("@/modules/catalog/api/catalog-api", () => ({
  fetchCategories: vi.fn(async () => [
    { id: "cat", slug: "tools", name: "Tools", subcategories: [] },
  ]),
  fetchProducts: vi.fn(async () => productListFixture()),
}));
vi.mock("@/modules/catalog/components/catalog-filters", () => ({
  CatalogFilters: () => null,
}));
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});
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

it("waits for the recommendations block before requesting extra products", async () => {
  let notify!: IntersectionObserverCallback;
  vi.stubGlobal(
    "IntersectionObserver",
    class {
      constructor(callback: IntersectionObserverCallback) {
        notify = callback;
      }
      observe() {}
      disconnect() {}
    },
  );
  vi.mocked(fetchProducts).mockClear();
  vi.mocked(fetchProducts).mockResolvedValue(productListFixture());
  const router = createMemoryRouter(
    [{ path: "/catalog/:category", element: <CatalogPage /> }],
    { initialEntries: ["/catalog/tools"] },
  );
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={client}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
  await screen.findByRole("textbox", { name: "Пошук у каталозі" });
  expect(
    vi
      .mocked(fetchProducts)
      .mock.calls.some(([params]) => params?.page_size === 20),
  ).toBe(false);
  await act(async () => {
    notify(
      [{ isIntersecting: true } as IntersectionObserverEntry],
      {} as IntersectionObserver,
    );
  });
  await waitFor(() =>
    expect(
      vi
        .mocked(fetchProducts)
        .mock.calls.some(([params]) => params?.page_size === 20),
    ).toBe(true),
  );
});

const categoryFixture = (slug: string) => ({
  id: slug,
  slug,
  name: slug,
  description: "",
  accent: "gold",
  icon: "",
  position: 0,
  product_count: 100,
  subcategories: Array.from({ length: 8 }, (_, index) => ({
    id: `${slug}-${index}`,
    slug: `${slug}-${index}`,
    name: `Sub ${slug} ${index}`,
    product_count: 8 - index,
  })),
});

it("keeps collapse available and resets expansion when switching categories", async () => {
  vi.mocked(fetchCategories).mockResolvedValueOnce([
    categoryFixture("one"),
    categoryFixture("two"),
  ]);
  const router = createMemoryRouter(
    [{ path: "/catalog/:category", element: <CatalogPage /> }],
    { initialEntries: ["/catalog/one?subcategory=one-7"] },
  );
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={client}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
  const more = await screen.findByRole("button", { name: "Ще 2 підкатегорії" });
  expect(screen.getByRole("link", { name: /Sub one 7/ })).toHaveAttribute(
    "data-active",
    "true",
  );
  expect(screen.getAllByRole("link", { name: /Sub one/ })).toHaveLength(6);
  fireEvent.click(more);
  expect(screen.getAllByRole("link", { name: /Sub one/ })).toHaveLength(8);
  fireEvent.click(screen.getByRole("button", { name: "Згорнути" }));
  expect(screen.getAllByRole("link", { name: /Sub one/ })).toHaveLength(6);
  fireEvent.click(screen.getByRole("button", { name: "Ще 2 підкатегорії" }));
  await act(async () => {
    await router.navigate("/catalog/two");
  });
  await screen.findByRole("link", { name: /Sub two 0/ });
  expect(screen.getAllByRole("link", { name: /Sub two/ })).toHaveLength(6);
  expect(
    screen.getByRole("button", { name: "Ще 2 підкатегорії" }),
  ).toHaveAttribute("aria-expanded", "false");
});
