import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { specFacetsQuery } from "@/modules/catalog/api/facet-queries";
import type { FacetOption } from "@/shared/types/api";
import { CatalogSpecFilters } from "./catalog-spec-filters";

afterEach(() => {
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
      { value: "Матеріал виготовлення", count: 5 },
      { value: "Ступінь захисту, IP", count: 8 },
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
