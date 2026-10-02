import { apiClient } from "@/shared/api/client";
import { buildQuery, type QueryValue } from "@/shared/api/query";
import type {
  Brand,
  CatalogSection,
  Category,
  ProductDetail,
  ProductList,
  ProductReviewPage,
  ProductReview,
  ReviewStatus,
} from "@/shared/types/api";

export function fetchCategories(): Promise<Category[]> {
  return apiClient("/catalog/categories");
}

export function fetchSections(): Promise<CatalogSection[]> {
  return apiClient("/catalog/sections");
}

export function fetchProducts(
  params: Record<string, QueryValue | QueryValue[]> = {},
  signal?: AbortSignal,
): Promise<ProductList> {
  return apiClient(`/catalog/products${buildQuery(params)}`, { signal });
}

export function fetchBrands(): Promise<Brand[]> {
  return apiClient("/catalog/brands");
}

export function fetchProduct(
  slug: string,
  signal?: AbortSignal,
): Promise<ProductDetail> {
  return apiClient(`/catalog/products/${encodeURIComponent(slug)}`, { signal });
}

export function fetchFeaturedReviews(): Promise<ProductReview[]> {
  return apiClient("/catalog/reviews/featured");
}

export function fetchProductReviews(
  slug: string,
  page: number,
  signal?: AbortSignal,
): Promise<ProductReviewPage> {
  return apiClient(
    `/catalog/products/${encodeURIComponent(slug)}/reviews${buildQuery({ page, page_size: 10 })}`,
    { signal },
  );
}

export function createProductReview(
  slug: string,
  payload: { author: string; email: string; rating: number; text: string },
): Promise<{ id: string; status: ReviewStatus }> {
  return apiClient(`/catalog/products/${encodeURIComponent(slug)}/reviews`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
