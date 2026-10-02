import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";
import { fetchBrands } from "@/modules/catalog/api/catalog-api";
import { ApiError } from "@/shared/api/errors";
import { BrandProductsPage } from "./brand-pages";
vi.mock("@/modules/catalog/api/catalog-api", () => ({ fetchBrands: vi.fn() }));
afterEach(cleanup);
it("distinguishes a failed lookup from a missing brand and allows retry", async () => {
  vi.mocked(fetchBrands)
    .mockRejectedValueOnce(
      new ApiError(503, "Unavailable", undefined, "service_unavailable"),
    )
    .mockResolvedValue([]);
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={["/brands/eti"]}>
        <Routes>
          <Route path="/brands/:slug" element={<BrandProductsPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
  await screen.findByRole("alert");
  expect(screen.queryByText("Бренд не знайдено")).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Повторити" }));
  await screen.findByText("Бренд не знайдено");
});
