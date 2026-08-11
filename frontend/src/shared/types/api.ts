export type StockStatus = "in_stock" | "preorder";
export type ProductBadge = "top" | "new" | "sale";
export type ProductSort = "popular" | "price_asc" | "price_desc" | "newest";
export type DeliveryMethod =
  "nova_poshta_branch" | "nova_poshta_locker" | "pickup";
export type PaymentMethod = "cash_on_delivery" | "card" | "invoice";
export type PaymentStatus =
  "pending" | "not_required" | "paid" | "failed" | "refunded";
export type OrderStatus =
  "new" | "confirmed" | "processing" | "shipped" | "delivered" | "cancelled";
export type LeadType = "callback" | "quick_buy" | "wholesale";
export type LeadStatus = "new" | "contacted" | "closed";

export interface CatalogReference {
  id: string;
  slug: string;
  name: string;
}

export interface Subcategory extends CatalogReference {
  product_count: number;
}

export interface Category extends CatalogReference {
  accent: string;
  product_count: number;
  subcategories: Subcategory[];
}

export interface Product {
  id: string;
  sku: string;
  slug: string;
  name: string;
  brand: string;
  image_url: string | null;
  price: string;
  old_price: string | null;
  badge: ProductBadge | null;
  stock_status: StockStatus;
  rating: string;
  reviews_count: number;
  category: CatalogReference;
  subcategory: CatalogReference | null;
  specs: Record<string, string>;
}

export interface ProductReview {
  id: string;
  author: string;
  rating: number;
  text: string;
  created_at: string;
}

export interface ProductDetail extends Product {
  reviews: ProductReview[];
}

export interface FacetOption {
  value: string;
  count: number;
}

export interface ProductList {
  items: Product[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
  facets: {
    brands: FacetOption[];
    specs: Record<string, FacetOption[]>;
    price: { minimum: string | null; maximum: string | null };
  };
}

export interface CartItemInput {
  product_id: string;
  quantity: number;
}

export interface Quote {
  items: Array<{
    product_id: string;
    sku: string;
    name: string;
    stock_status: StockStatus;
    quantity: number;
    unit_price: string;
    total: string;
  }>;
  subtotal: string;
  discount: string;
  total: string;
  promotion: { code: string; discount_rate: string } | null;
}

export interface Delivery {
  method: DeliveryMethod;
  city: string | null;
  point: string | null;
}

export interface DeliveryCityOption {
  ref: string;
  name: string;
  label: string;
}

export interface DeliveryPointOption {
  ref: string;
  name: string;
  label: string;
  number: string;
}

export interface Order {
  id: string;
  number: string;
  customer_name: string;
  phone: string;
  company: { name: string; edrpou: string } | null;
  delivery: Delivery;
  payment_method: PaymentMethod;
  payment_status: PaymentStatus;
  status: OrderStatus;
  promo_code: string | null;
  subtotal: string;
  discount: string;
  total: string;
  items: Array<{
    product_id: string;
    sku: string;
    product_name: string;
    quantity: number;
    unit_price: string;
    total: string;
  }>;
  created_at: string;
}

export interface OrderSummary {
  id: string;
  number: string;
  customer_name: string;
  phone: string;
  delivery: Delivery;
  payment_method: PaymentMethod;
  payment_status: PaymentStatus;
  status: OrderStatus;
  total: string;
  created_at: string;
}

export interface Paginated<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
}

export interface Lead {
  id: string;
  type: LeadType;
  status: LeadStatus;
  created_at: string;
}

export interface AdminLead extends Lead {
  name: string;
  phone: string;
  company: string | null;
  product_id: string | null;
}

export interface Dashboard {
  revenue_last_7_days: string;
  orders_today: number;
  average_order_total: string;
  active_products: number;
  new_leads: number;
}

export interface TokenResponse {
  access_token: string;
  token_type: "bearer";
  expires_in: number;
}
