import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { productsQuery } from "@/modules/catalog/api/catalog-queries";
import { getUserErrorMessage } from "@/shared/api/errors";
import { formatMoney } from "@/shared/lib/format";
import { useDebouncedValue } from "@/shared/lib/use-debounced-value";
import { ProductVisual } from "./product-visual";

export function ProductSearchSuggestions({
  query,
  onSelect,
}: {
  query: string;
  onSelect: () => void;
}) {
  const debounced = useDebouncedValue(query, 250);
  const result = useQuery({
    ...productsQuery({
      search: debounced,
      page_size: 5,
      sort: "popular",
      include_facets: false,
    }),
    enabled: debounced.length >= 2,
  });
  const suggestions = result.data?.items ?? [];
  return (
    <>
      {result.isPending && debounced.length >= 2 ? (
        <span className="search-suggestions__status">Шукаємо…</span>
      ) : null}
      {result.isError ? (
        <span className="search-suggestions__status" role="alert">
          {getUserErrorMessage(result.error, "Пошук тимчасово недоступний")}
        </span>
      ) : null}
      {!result.isPending && !result.isError && suggestions.length === 0 ? (
        <span className="search-suggestions__status">Нічого не знайдено</span>
      ) : null}
      {suggestions.map((product) => (
        <Link
          key={product.id}
          onClick={onSelect}
          to={`/products/${product.slug}`}
        >
          <span className="search-suggestions__visual">
            <ProductVisual imageSizes="80px" iconSize={24} product={product} />
          </span>
          <span>
            <strong>{product.name}</strong>
            <small>
              {product.brand} · {product.sku}
            </small>
          </span>
          <b>{formatMoney(product.price)}</b>
        </Link>
      ))}
    </>
  );
}
