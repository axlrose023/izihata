import type { Product, ProductBadge, StockStatus } from "@/shared/types/api";

export type AdminRequest = <T>(path: string, init?: RequestInit) => Promise<T>;

export interface CreateProductPayload {
  category_id: string;
  subcategory_id: string | null;
  sku: string;
  name: string;
  brand: string;
  image_url: string | null;
  price: string;
  old_price: string | null;
  badge: ProductBadge | null;
  stock_status: StockStatus;
  specs: Record<string, string>;
}

export function createAdminProduct(
  request: AdminRequest,
  payload: CreateProductPayload,
): Promise<Product> {
  return request("/admin/catalog/products", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateAdminProductDetails(
  request: AdminRequest,
  productId: string,
  payload: CreateProductPayload,
): Promise<Product> {
  return request(`/admin/catalog/products/${productId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function updateAdminProduct(
  request: AdminRequest,
  productId: string,
  payload: {
    price: string;
    old_price: string | null;
    stock_status: StockStatus;
  },
): Promise<Product> {
  return request(`/admin/catalog/products/${productId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}
