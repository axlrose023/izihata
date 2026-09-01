export type StockStatus =
  "in_stock_today" | "in_stock" | "preorder" | "out_of_stock";
export type ProductBadge =
  "top" | "new" | "sale" | "promotion" | "clearance" | "recommended";
export type ProductSort =
  | "popular"
  | "price_asc"
  | "price_desc"
  | "newest"
  | "reviews"
  | "availability";
export type SaleUnit = "piece" | "meter" | "coil";
export type ProductDocumentKind = "certificate" | "instruction" | "datasheet";
export type ProductRelationKind = "related" | "alternative" | "bought_together";
export type ReviewStatus = "pending" | "published" | "rejected";
export type StockSubscriptionStatus = "active" | "notified" | "cancelled";
export type DeliveryMethod =
  "nova_poshta_branch" | "nova_poshta_locker" | "pickup";
export type PaymentMethod = "cash_on_delivery" | "card" | "invoice";
export type PaymentStatus =
  "pending" | "not_required" | "paid" | "failed" | "refunded";
export type OrderStatus =
  "new" | "confirmed" | "processing" | "shipped" | "delivered" | "cancelled";
export type LeadType = "callback" | "quick_buy" | "wholesale";
export type LeadStatus = "new" | "contacted" | "closed";
export type QuotePriceType = "retail" | "wholesale";
export type CompanyKind = "fop" | "legal";
export type CompanyStatus = "pending" | "approved" | "rejected";
export type BoardApplication = "apartment" | "house" | "industrial";
export type BoardRequestStatus =
  "new" | "in_review" | "quoted" | "closed" | "cancelled";
export type AttributeValueType = "text" | "number" | "boolean" | "select";

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

export interface CatalogSection extends CatalogReference {
  description: string | null;
  image_url: string | null;
  product_count: number;
  categories: Category[];
}

export interface ProductAvailability {
  status: StockStatus;
  lead_time_days: number | null;
  dispatch_cutoff_hour: number | null;
}

export interface ProductMedia {
  id: string;
  url: string;
  alt: string;
  position: number;
}

export interface ProductDocument {
  id: string;
  kind: ProductDocumentKind;
  title: string;
  url: string;
}

export interface Product {
  id: string;
  sku: string;
  slug: string;
  name: string;
  brand: string;
  brand_country: string | null;
  production_country: string | null;
  short_description: string | null;
  image_url: string | null;
  price: string;
  old_price: string | null;
  badge: ProductBadge | null;
  stock_status: StockStatus;
  availability: ProductAvailability;
  sale_unit: SaleUnit;
  wholesale_min_quantity: number | null;
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

export interface AdminProductRelation {
  product_id: string;
  kind: ProductRelationKind;
  position: number;
  name: string;
  sku: string;
}

export interface AdminProductDetail extends Product {
  wholesale_price: string | null;
  description: string | null;
  relations: AdminProductRelation[];
}

export interface ProductDetail extends Product {
  description: string | null;
  media: ProductMedia[];
  documents: ProductDocument[];
  reviews: ProductReview[];
  related: Product[];
  alternatives: Product[];
  bought_together: Product[];
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
    availability: FacetOption[];
    sale_units: FacetOption[];
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
    price_type: QuotePriceType;
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

export interface CustomerCompany {
  id: string;
  kind: CompanyKind;
  name: string;
  edrpou: string;
  status: CompanyStatus;
  manager_name: string | null;
  cumulative_discount_rate: string;
}

export interface CustomerProfile {
  id: string;
  full_name: string;
  email: string;
  phone: string | null;
  company: CustomerCompany | null;
}

export interface AdminCompany extends CustomerCompany {
  customer_id: string;
  customer_name: string;
  customer_email: string;
  created_at: string;
}

export interface AdvisorProductResult {
  reference_notice: string;
  products: Product[];
}

export interface CableSizeResult extends AdvisorProductResult {
  current_a: string;
  recommended_cross_section_mm2: string;
}

export interface BreakerResult extends AdvisorProductResult {
  current_a: string;
  recommended_nominal_a: number | null;
  recommended_curve: string;
  requires_specialist: boolean;
}

export interface LedPowerSupplyResult extends AdvisorProductResult {
  load_w: string;
  recommended_power_w: string;
}

export interface AutonomyResult extends AdvisorProductResult {
  required_energy_wh: string;
  recommended_battery_capacity_ah: string;
  recommended_inverter_power_w: string;
}

export interface BoardEstimate {
  starting_price: string;
  response_sla_hours: number;
  suggested_components: string[];
  reference_notice: string;
}

export interface CustomBoardRequestResult {
  id: string;
  status: BoardRequestStatus;
  starting_price: string;
  response_sla_hours: number;
}

export interface BoardPortfolioItem {
  id: string;
  title: string;
  description: string;
  image_url: string;
  position: number;
}

export interface AdminCustomBoardRequest {
  id: string;
  customer_name: string;
  phone: string;
  email: string | null;
  application: BoardApplication;
  groups_count: number;
  ip_class: string;
  automation_brand: string | null;
  budget: string | null;
  details: string | null;
  estimated_from_price: string;
  status: BoardRequestStatus;
  created_at: string;
}

export interface CatalogAttribute {
  id: string;
  code: string;
  name: string;
  value_type: AttributeValueType;
  unit: string | null;
  is_filterable: boolean;
  position: number;
}

export interface CategoryAttribute {
  id: string;
  attribute: CatalogAttribute;
  is_required: boolean;
  is_primary_filter: boolean;
  position: number;
}

export interface AdminProductReview {
  id: string;
  product_id: string;
  product_name: string;
  author: string;
  email: string | null;
  rating: number;
  text: string;
  status: ReviewStatus;
  is_featured: boolean;
  created_at: string;
}
