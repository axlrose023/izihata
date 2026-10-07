import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";

import { SiteHeader } from "./site-header";

vi.mock("@/modules/cart/store", () => ({
  cartCount: () => 0,
  useCartStore: (select: (state: { lines: never[]; open: () => void }) => unknown) =>
    select({ lines: [], open: vi.fn() }),
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

it("returns from a filtered category route to the unfiltered all-products route", async () => {
  const router = createMemoryRouter(
    [{ path: "*", element: <SiteHeader /> }],
    {
      initialEntries: [
        "/catalog/lowvoltage?brand=ETI&spec=%5B%22Матеріал%22%2C%22Метал%22%5D&page=4",
      ],
    },
  );

  render(<RouterProvider router={router} />);
  fireEvent.click(screen.getByRole("link", { name: "Усі товари" }));

  await waitFor(() => expect(router.state.location.pathname).toBe("/catalog"));
  expect(router.state.location.search).toBe("");
});
