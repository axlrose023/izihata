import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { specFacetsQuery } from "@/modules/catalog/api/facet-queries";
import type { FacetOption } from "@/shared/types/api";
import { CatalogSpecFilters } from "./catalog-spec-filters";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

it("groups material and IP values into the requested normalized filters", async () => {
  const params = { category: "panels" };
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime: Infinity } },
  });
  const page = (items: FacetOption[]) => ({
    pages: [{ items, page: 1, has_next: false }],
    pageParams: [1],
  });
  queryClient.setQueryData(
    specFacetsQuery(params, undefined, "").queryKey,
    page([
      { value: "Матеріал", count: 12 },
      { value: "Ступінь захисту IP", count: 8 },
    ]),
  );
  queryClient.setQueryData(
    specFacetsQuery(params, "Матеріал", "").queryKey,
    page([
      { value: "Метал", count: 4 },
      { value: "Пластик", count: 3 },
      { value: "АБС-пластик", count: 5 },
    ]),
  );
  queryClient.setQueryData(
    specFacetsQuery(params, "Ступінь захисту IP", "").queryKey,
    page([
      { value: "IP20", count: 1 },
      { value: "IP31", count: 2 },
    ]),
  );
  const onToggle = vi.fn();

  render(
    <QueryClientProvider client={queryClient}>
      <CatalogSpecFilters
        activeBrands={new Set()}
        activeSpecs={new Set()}
        onToggle={onToggle}
        params={params}
      />
    </QueryClientProvider>,
  );

  expect(
    await screen.findByText("Матеріал", { selector: "summary" }),
  ).toBeVisible();
  expect(
    screen.getByText("Ступінь захисту IP", { selector: "summary" }),
  ).toBeVisible();
  expect(
    screen.queryByText("Матеріал виготовлення", { selector: "summary" }),
  ).toBeNull();
  expect(
    screen.queryByText("Ступінь захисту, IP", { selector: "summary" }),
  ).toBeNull();

  fireEvent.click(screen.getByText("Матеріал", { selector: "summary" }));
  const metal = await screen.findByRole("checkbox", { name: /Метал/ });
  fireEvent.click(metal);
  expect(onToggle).toHaveBeenCalledWith(
    "spec",
    JSON.stringify(["Матеріал", "Метал"]),
    true,
  );
});

it("does not inject unrelated groups into an empty search result", async () => {
  const params = { category: "panels" };
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  client.setQueryData(specFacetsQuery(params, undefined, "").queryKey, {
    pages: [{ items: [], page: 1, has_next: false }],
    pageParams: [1],
  });
  const view = render(
    <QueryClientProvider client={client}>
      <CatalogSpecFilters
        params={params}
        activeBrands={new Set()}
        activeSpecs={new Set()}
        onToggle={vi.fn()}
      />
    </QueryClientProvider>,
  );
  expect(view.container.querySelectorAll("summary")).toHaveLength(0);
  view.unmount();
});

it("keeps an old raw selected attribute visible for removal", async () => {
  const params = { category: "panels" };
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  for (const key of [undefined, "Матеріал корпусу"]) {
    client.setQueryData(specFacetsQuery(params, key, "").queryKey, {
      pages: [{ items: [], page: 1, has_next: false }],
      pageParams: [1],
    });
  }
  const onToggle = vi.fn();
  const view = render(
    <QueryClientProvider client={client}>
      <CatalogSpecFilters
        params={params}
        activeBrands={new Set()}
        activeSpecs={new Set([JSON.stringify(["Матеріал корпусу", "метал"])])}
        onToggle={onToggle}
      />
    </QueryClientProvider>,
  );
  fireEvent.click(await screen.findByRole("checkbox", { name: /метал/ }));
  expect(onToggle).toHaveBeenCalledWith(
    "spec",
    JSON.stringify(["Матеріал корпусу", "метал"]),
    false,
  );
  view.unmount();
});
