import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";

import { productDetailFixture } from "@/tests/product-fixture";
import { ProductPage } from "./product-page";

const { reviewRender } = vi.hoisted(() => ({ reviewRender: vi.fn() }));
vi.mock("@/modules/catalog/api/catalog-api", () => ({
  fetchProduct: async () => productDetailFixture(),
}));
vi.mock("@/modules/reviews/components/product-reviews", () => ({
  ProductReviews: () => {
    reviewRender();
    return <input aria-label="Review draft" />;
  },
}));
afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

it("loads reviews on first opening and retains the draft between tabs", async () => {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={["/products/test-product"]}>
        <Routes>
          <Route path="/products/:slug" element={<ProductPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
  await screen.findByRole("heading", { name: "Test product" });
  expect(reviewRender).not.toHaveBeenCalled();
  expect(screen.queryByLabelText("Review draft")).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("tab", { name: /^Відгуки/ }));
  const input = await screen.findByLabelText(
    "Review draft",
    {},
    { timeout: 3000 },
  );
  fireEvent.change(input, { target: { value: "Retained review draft" } });
  fireEvent.click(screen.getByRole("tab", { name: "Характеристики" }));
  expect(input).not.toBeVisible();
  fireEvent.click(screen.getByRole("tab", { name: /^Відгуки/ }));
  expect(screen.getByLabelText("Review draft")).toHaveValue(
    "Retained review draft",
  );
  expect(input).toBeVisible();
});
