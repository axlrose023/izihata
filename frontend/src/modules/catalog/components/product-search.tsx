import { Search } from "lucide-react";
import { lazy, Suspense, useState } from "react";
import { Form } from "react-router-dom";

const ProductSearchSuggestions = lazy(() =>
  import("./product-search-suggestions").then((module) => ({
    default: module.ProductSearchSuggestions,
  })),
);

export function ProductSearch() {
  const [query, setQuery] = useState("");
  const [focused, setFocused] = useState(false);
  const normalized = query.trim();
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
        aria-expanded={open}
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
          <Suspense
            fallback={
              <span className="search-suggestions__status">Шукаємо…</span>
            }
          >
            <ProductSearchSuggestions
              query={normalized}
              onSelect={() => {
                setQuery("");
                setFocused(false);
              }}
            />
          </Suspense>
        </div>
      ) : null}
    </Form>
  );
}
