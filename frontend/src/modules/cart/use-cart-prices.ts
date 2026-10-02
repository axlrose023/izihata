import { useQuery } from "@tanstack/react-query";
import { useEffect } from "react";
import { fetchProducts } from "@/modules/catalog/api/catalog-api";
import { MAX_CART_LINES, useCartStore } from "./store";

export function useCartPrices() {
  const { lines, isOpen, refreshProducts } = useCartStore();
  const ids = lines.map(({ product }) => product.id).sort();
  const idsKey = JSON.stringify(ids);
  const result = useQuery({
    queryKey: ["cart", "prices", idsKey],
    queryFn: ({ signal }) =>
      fetchProducts(
        { id: ids, page_size: MAX_CART_LINES, include_facets: false },
        signal,
      ),
    enabled: isOpen && ids.length > 0 && ids.length <= MAX_CART_LINES,
  });
  useEffect(() => {
    if (result.data)
      refreshProducts(result.data.items, JSON.parse(idsKey) as string[]);
  }, [result.data, idsKey, refreshProducts]);
  const current = new Map(
    result.data?.items.map((product) => [product.id, product]),
  );
  const unavailable = result.isSuccess
    ? ids.filter(
        (id) =>
          !current.has(id) || current.get(id)?.stock_status === "out_of_stock",
      )
    : [];
  return { ...result, unavailable };
}
