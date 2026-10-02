import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, cleanup, renderHook, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { fetchProducts } from "@/modules/catalog/api/catalog-api";
import { productFixture, productListFixture } from "@/tests/product-fixture";
import { useCartStore } from "./store";
import { useCartPrices } from "./use-cart-prices";
vi.mock("@/modules/catalog/api/catalog-api", () => ({
  fetchProducts: vi.fn(),
}));
afterEach(cleanup);
it("fetches only for an open cart and retains missing lines for explicit removal", async () => {
  vi.mocked(fetchProducts).mockResolvedValue(productListFixture({ items: [] }));
  const product = productFixture();
  useCartStore.setState({ lines: [{ product, quantity: 2 }], isOpen: false });
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const { result } = renderHook(useCartPrices, {
    wrapper: ({ children }) => (
      <QueryClientProvider client={client}>{children}</QueryClientProvider>
    ),
  });
  expect(fetchProducts).not.toHaveBeenCalled();
  act(() => useCartStore.getState().open());
  await waitFor(() => expect(result.current.unavailable).toEqual([product.id]));
  expect(useCartStore.getState().lines).toEqual([{ product, quantity: 2 }]);
  act(() => useCartStore.getState().setQuantity(product.id, 3));
  expect(fetchProducts).toHaveBeenCalledTimes(1);
});
