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
afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

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
  await screen.findByText("Нічого не знайдено");
  expect(apiClient).toHaveBeenCalledTimes(1);
  fireEvent.blur(input, { relatedTarget: null });
  fireEvent.change(input, { target: { value: "кабель" } });
  await client.invalidateQueries();
  expect(apiClient).toHaveBeenCalledTimes(1);
  fireEvent.focus(input);
  await waitFor(() => expect(apiClient).toHaveBeenCalledTimes(2));
});

it("opens mobile search without navigation or requests and submits to the catalog", async () => {
  vi.mocked(apiClient).mockResolvedValue({ items: [], total: 0 });
  const router = createMemoryRouter([
    { path: "/", element: <ProductSearch /> },
    { path: "/catalog", element: <p>Catalog results</p> },
  ]);
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={client}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
  const toggle = screen.getByRole("button", {
    name: "Відкрити пошук товарів",
  });
  fireEvent.click(toggle);
  const input = screen.getByRole("combobox");
  expect(input).toHaveFocus();
  expect(router.state.location.pathname).toBe("/");
  expect(apiClient).not.toHaveBeenCalled();
  fireEvent.keyDown(document, { key: "Escape" });
  expect(toggle).toHaveAttribute("aria-expanded", "false");
  expect(toggle).toHaveFocus();

  fireEvent.click(toggle);
  fireEvent.pointerDown(document.body);
  expect(toggle).toHaveAttribute("aria-expanded", "false");
  fireEvent.click(toggle);
  fireEvent.change(input, { target: { value: "AX-10014" } });
  fireEvent.submit(screen.getByRole("search"));
  await screen.findByText("Catalog results");
  expect(router.state.location.search).toBe("?search=AX-10014");
});
