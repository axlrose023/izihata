import { apiClient } from "@/shared/api/client";
import { buildQuery, type QueryValue } from "@/shared/api/query";
import type {
  Category,
  ProductDetail,
  ProductList,
  ProductReview,
} from "@/shared/types/api";

export function fetchCategories(): Promise<Category[]> {
  return apiClient("/catalog/categories");
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
