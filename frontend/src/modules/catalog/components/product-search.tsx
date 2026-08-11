import { useQuery } from "@tanstack/react-query";
import { Search } from "lucide-react";
import { useState } from "react";
import { Form, Link } from "react-router-dom";

import { productsQuery } from "@/modules/catalog/api/catalog-queries";
import { getUserErrorMessage } from "@/shared/api/errors";
import { formatMoney } from "@/shared/lib/format";
import { useDebouncedValue } from "@/shared/lib/use-debounced-value";

import { ProductVisual } from "./product-visual";

export function ProductSearch() {
  const [query, setQuery] = useState("");
  const [focused, setFocused] = useState(false);
  const normalized = query.trim();
  const debounced = useDebouncedValue(normalized, 250);
  const result = useQuery({
    ...productsQuery({ search: debounced, page_size: 5, sort: "popular" }),
    enabled: debounced.length >= 2,
  });
  const suggestions = result.data?.items ?? [];
  const open = focused && normalized.length >= 2;

  return (
    <Form
      action="/catalog"
      className="header-search"
      onBlur={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget))
          setFocused(false);
      }}
      onFocus={() => setFocused(true)}
      onSubmit={() => setFocused(false)}
      role="search"
    >
      <Search aria-hidden="true" size={19} />
      <input
        aria-autocomplete="list"
        aria-controls="product-search-suggestions"
        aria-expanded={open && suggestions.length > 0}
        aria-label="Пошук товарів"
        role="combobox"
        autoComplete="off"
        minLength={2}
        name="search"
        onChange={(event) => setQuery(event.currentTarget.value)}
        placeholder="Пошук за назвою, брендом або SKU"
        value={query}
      />
      <button type="submit">Знайти</button>
      {open ? (
        <div className="search-suggestions" id="product-search-suggestions">
          {result.isPending && debounced.length >= 2 ? (
            <span className="search-suggestions__status">Шукаємо…</span>
          ) : null}
          {result.isError ? (
            <span className="search-suggestions__status" role="alert">
              {getUserErrorMessage(result.error, "Пошук тимчасово недоступний")}
            </span>
          ) : null}
          {!result.isPending && !result.isError && suggestions.length === 0 ? (
            <span className="search-suggestions__status">
              Нічого не знайдено
            </span>
          ) : null}
          {suggestions.map((product) => (
            <Link
              key={product.id}
              onClick={() => {
                setQuery("");
                setFocused(false);
              }}
              to={`/products/${product.slug}`}
            >
              <span className="search-suggestions__visual">
                <ProductVisual iconSize={24} product={product} />
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
        </div>
      ) : null}
    </Form>
  );
}
