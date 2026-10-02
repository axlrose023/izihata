import { infiniteQueryOptions, queryOptions } from "@tanstack/react-query";

import { apiClient } from "@/shared/api/client";
import { buildQuery, type QueryValue } from "@/shared/api/query";
import type { FacetOption, ProductList } from "@/shared/types/api";
import { catalogKeys } from "./catalog-queries";

type FilterParams = Record<string, QueryValue | QueryValue[]>;
interface SpecFacetPage {
  items: FacetOption[];
  page: number;
  has_next: boolean;
}

export function facetParams(params: FilterParams): FilterParams {
  const filters = { ...params };
  for (const key of ["page", "page_size", "sort", "include_facets"])
    delete filters[key];
  return filters;
}

export const facetsQuery = (params: FilterParams) =>
  queryOptions({
    queryKey: [...catalogKeys.all, "facets", facetParams(params)],
    queryFn: ({ signal }) =>
      apiClient<ProductList["facets"]>(
        `/catalog/facets${buildQuery(facetParams(params))}`,
        { signal },
      ),
    staleTime: 30_000,
  });

export const specFacetsQuery = (
  params: FilterParams,
  key?: string,
  search?: string,
) =>
  infiniteQueryOptions({
    queryKey: [
      ...catalogKeys.all,
      "spec-facets",
      facetParams(params),
      key,
      search,
    ],
    initialPageParam: 1,
    queryFn: ({ signal, pageParam }) =>
      apiClient<SpecFacetPage>(
        `/catalog/spec-facets${buildQuery({ ...facetParams(params), facet_key: key, facet_search: search || undefined, page: pageParam, page_size: key ? 50 : 20 })}`,
        { signal },
      ),
    getNextPageParam: (lastPage) =>
      lastPage.has_next ? lastPage.page + 1 : undefined,
    staleTime: 30_000,
  });
