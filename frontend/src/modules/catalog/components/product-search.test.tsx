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
import { apiClient } from "@/shared/api/client";
import { ProductSearch } from "./product-search";

vi.mock("@/shared/api/client", () => ({ apiClient: vi.fn() }));
afterEach(cleanup);

it("requests suggestions only while the search is open", async () => {
  vi.mocked(apiClient).mockResolvedValue({ items: [], total: 0 });
  const router = createMemoryRouter([
    { path: "/", element: <ProductSearch /> },
  ]);
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={client}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
  const input = screen.getByRole("combobox");
  expect(apiClient).not.toHaveBeenCalled();
  fireEvent.focus(input);
  fireEvent.change(input, { target: { value: "автомат" } });
  // Cold lazy imports can exceed the default 1s wait during parallel CI checks.
  await screen.findByText("Нічого не знайдено", {}, { timeout: 3000 });
  expect(apiClient).toHaveBeenCalledTimes(1);
  fireEvent.blur(input, { relatedTarget: null });
  fireEvent.change(input, { target: { value: "кабель" } });
  await client.invalidateQueries();
  expect(apiClient).toHaveBeenCalledTimes(1);
  fireEvent.focus(input);
  await waitFor(() => expect(apiClient).toHaveBeenCalledTimes(2));
});
