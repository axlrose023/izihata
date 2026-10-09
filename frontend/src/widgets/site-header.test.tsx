import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";

import { categoriesQuery } from "@/modules/catalog/api/catalog-queries";
import type { Category } from "@/shared/types/api";
import { SiteHeader } from "./site-header";

vi.mock("@/modules/cart/store", () => ({
  cartCount: () => 0,
  useCartStore: (
    select: (state: { lines: never[]; open: () => void }) => unknown,
  ) => select({ lines: [], open: vi.fn() }),
}));
vi.mock("@/modules/cart/components/load-cart-drawer", () => ({
  preloadCartDrawer: vi.fn(),
}));
vi.mock("@/modules/collections/store", () => ({
  useCollectionStore: (
    select: (state: { favorites: never[]; compare: never[] }) => unknown,
  ) => select({ favorites: [], compare: [] }),
}));
vi.mock("@/modules/catalog/components/product-search", () => ({
  ProductSearch: () => null,
}));
vi.mock("@/modules/customers/customer-auth-context", () => ({
  useCustomerAuth: () => ({ status: "unauthenticated" }),
}));
vi.mock("@/modules/leads/components/lead-action", () => ({
  LeadAction: () => null,
}));
vi.mock("@/shared/ui/logo", () => ({ Logo: () => null }));
vi.mock("./site-sidebar", () => ({ SiteSidebar: () => null }));

afterEach(() => {
  vi.restoreAllMocks();
});

const categories: Category[] = [
  {
    id: "sockets-id",
    slug: "sockets",
    name: "Розетки та вимикачі",
    accent: "#f2a30b",
    product_count: 6,
    subcategories: [
      {
        id: "sockets-subcategory-id",
        slug: "sockets-outlets",
        name: "Розетки",
        product_count: 6,
      },
    ],
  },
  {
    id: "cable-id",
    slug: "cable",
    name: "Кабель та провід",
    accent: "#16a34a",
    product_count: 12,
    subcategories: [],
  },
];

function renderHeader(initialEntry: string) {
  const router = createMemoryRouter([{ path: "*", element: <SiteHeader /> }], {
    initialEntries: [initialEntry],
  });
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  queryClient.setQueryData(categoriesQuery().queryKey, categories);

  return {
    router,
    ...render(
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>,
    ),
  };
}

it("returns from a filtered category route to the unfiltered all-products route", async () => {
  const { router } = renderHeader(
    "/catalog/lowvoltage?brand=ETI&spec=%5B%22Матеріал%22%2C%22Метал%22%5D&page=4",
  );
  fireEvent.click(screen.getByRole("button", { name: "Усі товари" }));
  fireEvent.click(
    within(
      screen.getByRole("navigation", { name: "Категорії товарів" }),
    ).getByRole("link", { name: /Переглянути всі товари/ }),
  );

  await waitFor(() => expect(router.state.location.pathname).toBe("/catalog"));
  expect(router.state.location.search).toBe("");
});

it("opens the category popover on click and closes it with Escape", () => {
  renderHeader("/");
  const trigger = document.querySelector<HTMLButtonElement>(
    ".catalog-nav__primary",
  )!;

  fireEvent.mouseEnter(trigger.parentElement!);
  expect(trigger).toHaveAttribute("aria-expanded", "false");

  fireEvent.click(trigger);

  expect(trigger).toHaveAttribute("aria-expanded", "true");
  const menu = screen.getByRole("navigation", {
    name: "Категорії товарів",
  });
  const categoryButton = within(menu).getByRole("button", {
    name: "Розетки та вимикачі",
  });
  fireEvent.mouseEnter(categoryButton);
  expect(within(menu).getByRole("link", { name: "Розетки" })).toHaveAttribute(
    "href",
    "/catalog/sockets?subcategory=sockets-outlets",
  );

  fireEvent.keyDown(trigger, { key: "Escape" });
  expect(
    screen.queryByRole("navigation", { name: "Категорії товарів" }),
  ).not.toBeInTheDocument();
});
