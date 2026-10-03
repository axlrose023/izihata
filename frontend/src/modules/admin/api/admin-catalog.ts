import type {
  AdminProductDetail,
  AdminProductRelation,
  Product,
  ProductBadge,
  StockStatus,
} from "@/shared/types/api";

export type AdminRequest = <T>(path: string, init?: RequestInit) => Promise<T>;

export interface CreateProductPayload {
  category_id: string;
  subcategory_id: string | null;
  sku: string;
  name: string;
  brand: string;
  brand_country?: string | null;
  production_country?: string | null;
  short_description?: string | null;
  description?: string | null;
  image_url: string | null;
  price: string;
  old_price: string | null;
  badge: ProductBadge | null;
  is_popular: boolean;
  is_active: boolean;
  stock_status: StockStatus;
  stock_quantity: number;
  availability_days?: number | null;
  sale_unit: "piece" | "meter" | "coil";
  wholesale_price?: string | null;
  wholesale_min_quantity?: number | null;
  specs: Record<string, string>;
  relations?: Array<
    Pick<AdminProductRelation, "product_id" | "kind"> & {
      position: number;
    }
  >;
}

export function fetchAdminProduct(
  request: AdminRequest,
  productId: string,
): Promise<AdminProductDetail> {
  return request(`/admin/catalog/products/${productId}`);
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
  payload: Partial<CreateProductPayload> & { expected_updated_at?: string },
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
    price?: string;
    old_price?: string | null;
    stock_status?: StockStatus;
  },
): Promise<Product> {
  return request(`/admin/catalog/products/${productId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}
