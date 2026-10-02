import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";
import { apiClient } from "@/shared/api/client";
import { ApiError } from "@/shared/api/errors";
import { productListFixture } from "@/tests/product-fixture";
import { useCollectionStore } from "../store";
import { CollectionPage } from "./collection-page";
vi.mock("@/shared/api/client", () => ({ apiClient: vi.fn() }));
afterEach(cleanup);
function page() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <CollectionPage mode="favorites" />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}
it("lets the user remove missing favorites without discarding other collections", async () => {
  useCollectionStore.setState({
    favorites: ["missing"],
    compare: ["preserved"],
  });
  vi.mocked(apiClient).mockResolvedValue(
    productListFixture({ items: [], total: 0 }),
  );
  page();
  fireEvent.click(
    await screen.findByRole("button", { name: "Прибрати недоступні" }),
  );
  expect(useCollectionStore.getState().favorites).toEqual([]);
  expect(useCollectionStore.getState().compare).toEqual(["preserved"]);
  expect(screen.getByText("Обране порожнє")).toBeInTheDocument();
});
it("preserves favorites when the server fails and offers explicit clearing", async () => {
  useCollectionStore.setState({ favorites: ["preserved"], compare: [] });
  vi.mocked(apiClient).mockRejectedValue(new ApiError(503, "Unavailable"));
  page();
  await screen.findByRole("alert");
  expect(useCollectionStore.getState().favorites).toEqual(["preserved"]);
  expect(
    screen.queryByRole("button", { name: "Прибрати недоступні" }),
  ).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Очистити обране" }));
  expect(useCollectionStore.getState().favorites).toEqual([]);
});
