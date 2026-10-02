import { catalogPaths } from "./catalog-paths";
import { publicCatalogSeed } from "./public-catalog-seed";
import type {
  Category,
  CatalogSection,
  Brand,
  ProductDetail,
  ProductList,
} from "@/shared/types/api";
import { keepPreviousData, queryOptions } from "@tanstack/react-query";

import type { QueryValue } from "@/shared/api/query";

import {
  fetchSections,
  fetchCategories,
  fetchBrands,
  fetchFeaturedReviews,
  fetchProduct,
  fetchProducts,
} from "./catalog-api";

export const catalogKeys = {
  all: ["catalog"] as const,
  categories: () => [...catalogKeys.all, "categories"] as const,
  sections: () => [...catalogKeys.all, "sections"] as const,
  brands: () => [...catalogKeys.all, "brands"] as const,
  featuredReviews: () => [...catalogKeys.all, "featured-reviews"] as const,
  products: (params: Record<string, QueryValue | QueryValue[]>) =>
    [...catalogKeys.all, "products", params] as const,
  product: (slug: string) => [...catalogKeys.all, "product", slug] as const,
};

export const categoriesQuery = () =>
  queryOptions({
    queryKey: catalogKeys.categories(),
    ...publicCatalogSeed<Category[]>(catalogPaths.categories),
    queryFn: fetchCategories,
    staleTime: 5 * 60_000,
  });

export const sectionsQuery = () =>
  queryOptions({
    queryKey: catalogKeys.sections(),
    ...publicCatalogSeed<CatalogSection[]>(catalogPaths.sections),
    queryFn: fetchSections,
    staleTime: 5 * 60_000,
  });

export const brandsQuery = () =>
  queryOptions({
    queryKey: catalogKeys.brands(),
    ...publicCatalogSeed<Brand[]>(catalogPaths.brands),
    queryFn: fetchBrands,
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
    ...publicCatalogSeed<ProductList>(catalogPaths.products(params)),
    queryFn: ({ signal }) => fetchProducts(params, signal),
    // Filters apply as you click them, so keep the previous page visible
    // instead of dropping the grid into a loader on every change.
    placeholderData: keepPreviousData,
  });

export const productQuery = (slug: string) =>
  queryOptions({
    queryKey: catalogKeys.product(slug),
    ...publicCatalogSeed<ProductDetail>(catalogPaths.product(slug)),
    staleTime: 30_000,
    queryFn: ({ signal }) => fetchProduct(slug, signal),
  });
