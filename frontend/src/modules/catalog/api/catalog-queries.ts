import { queryOptions } from "@tanstack/react-query";

import type { QueryValue } from "@/shared/api/query";

import {
  fetchSections,
  fetchCategories,
  fetchFeaturedReviews,
  fetchProduct,
  fetchProducts,
} from "./catalog-api";

export const catalogKeys = {
  all: ["catalog"] as const,
  categories: () => [...catalogKeys.all, "categories"] as const,
  sections: () => [...catalogKeys.all, "sections"] as const,
  featuredReviews: () => [...catalogKeys.all, "featured-reviews"] as const,
  products: (params: Record<string, QueryValue | QueryValue[]>) =>
    [...catalogKeys.all, "products", params] as const,
  product: (slug: string) => [...catalogKeys.all, "product", slug] as const,
};

export const categoriesQuery = () =>
  queryOptions({
    queryKey: catalogKeys.categories(),
    queryFn: fetchCategories,
    staleTime: 5 * 60_000,
  });

export const sectionsQuery = () =>
  queryOptions({
    queryKey: catalogKeys.sections(),
    queryFn: fetchSections,
    staleTime: 5 * 60_000,
  });

export const featuredReviewsQuery = () =>
  queryOptions({
    queryKey: catalogKeys.featuredReviews(),
    queryFn: fetchFeaturedReviews,
    staleTime: 5 * 60_000,
  });

export const productsQuery = (
  params: Record<string, QueryValue | QueryValue[]>,
) =>
  queryOptions({
    queryKey: catalogKeys.products(params),
    queryFn: () => fetchProducts(params),
  });

export const productQuery = (slug: string) =>
  queryOptions({
    queryKey: catalogKeys.product(slug),
    queryFn: () => fetchProduct(slug),
  });
