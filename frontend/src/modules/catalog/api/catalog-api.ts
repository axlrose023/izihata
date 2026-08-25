import { apiClient } from "@/shared/api/client";
import { buildQuery, type QueryValue } from "@/shared/api/query";
import type {
  Category,
  CatalogSection,
  ProductDetail,
  ProductList,
  ProductReview,
  ReviewStatus,
  StockSubscriptionStatus,
} from "@/shared/types/api";

export function fetchCategories(): Promise<Category[]> {
  return apiClient("/catalog/categories");
}

export function fetchSections(): Promise<CatalogSection[]> {
  return apiClient("/catalog/sections");
}

export function fetchProducts(
  params: Record<string, QueryValue | QueryValue[]> = {},
): Promise<ProductList> {
  return apiClient(`/catalog/products${buildQuery(params)}`);
}

export function fetchProduct(slug: string): Promise<ProductDetail> {
  return apiClient(`/catalog/products/${encodeURIComponent(slug)}`);
}

export function fetchFeaturedReviews(): Promise<ProductReview[]> {
  return apiClient("/catalog/reviews/featured");
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

export function createStockSubscription(
  slug: string,
  email: string,
): Promise<{ id: string; status: StockSubscriptionStatus }> {
  return apiClient(
    `/catalog/products/${encodeURIComponent(slug)}/stock-subscriptions`,
    {
      method: "POST",
      body: JSON.stringify({ email }),
    },
  );
}
