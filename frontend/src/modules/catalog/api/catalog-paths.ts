import { buildQuery, type QueryValue } from "@/shared/api/query";
export const catalogPaths = {
  categories: "/catalog/categories",
  sections: "/catalog/sections",
  brands: "/catalog/brands",
  product: (slug: string) => `/catalog/products/${encodeURIComponent(slug)}`,
  products: (params: Record<string, QueryValue | QueryValue[]>) =>
    `/catalog/products${buildQuery(params)}`,
};
