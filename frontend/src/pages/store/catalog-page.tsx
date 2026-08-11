import { useQueries } from "@tanstack/react-query";
import { Filter, LayoutGrid, List, Search } from "lucide-react";
import { Form, Link, useParams, useSearchParams } from "react-router-dom";

import {
  categoriesQuery,
  productsQuery,
} from "@/modules/catalog/api/catalog-queries";
import { ProductCard } from "@/modules/catalog/components/product-card";
import type { ProductSort } from "@/shared/types/api";
import { useDocumentTitle } from "@/shared/lib/use-document-title";
import { EmptyState } from "@/shared/ui/empty-state";
import { ErrorNotice } from "@/shared/ui/error-notice";

const sorts: Array<{ value: ProductSort; label: string }> = [
  { value: "popular", label: "Популярні" },
  { value: "newest", label: "Новинки" },
  { value: "price_asc", label: "Від дешевих" },
  { value: "price_desc", label: "Від дорогих" },
];

function pageHref(params: URLSearchParams, page: number, category?: string) {
  const next = new URLSearchParams(params);
  next.set("page", String(page));
  next.delete("category");
  return `${category ? `/catalog/${category}` : "/catalog"}?${next}`;
}

function viewHref(
  params: URLSearchParams,
  view: "grid" | "list",
  category?: string,
) {
  const next = new URLSearchParams(params);
  next.delete("page");
  if (view === "grid") next.delete("view");
  else next.set("view", view);
  const query = next.toString();
  return `${category ? `/catalog/${category}` : "/catalog"}${query ? `?${query}` : ""}`;
}

export function CatalogPage() {
  const { category } = useParams<{ category?: string }>();
  const [searchParams] = useSearchParams();
  const view = searchParams.get("view") === "list" ? "list" : "grid";
  const query = {
    search: searchParams.get("search") ?? undefined,
    category: category ?? searchParams.get("category") ?? undefined,
    subcategory: searchParams.get("subcategory") ?? undefined,
    brand: searchParams.getAll("brand"),
    in_stock: searchParams.get("in_stock") ?? undefined,
    min_price: searchParams.get("min_price") ?? undefined,
    max_price: searchParams.get("max_price") ?? undefined,
    spec: searchParams.getAll("spec"),
    sort: searchParams.get("sort") ?? "popular",
    page: searchParams.get("page") ?? "1",
    page_size: 12,
  };
  const [categoriesResult, productsResult] = useQueries({
    queries: [categoriesQuery(), productsQuery(query)],
  });
  useDocumentTitle(
    categoriesResult.data?.find((item) => item.slug === query.category)?.name ??
      "Каталог",
  );

  if (categoriesResult.isPending || productsResult.isPending) {
    return <div className="page-loader">Завантажуємо каталог…</div>;
  }
  if (categoriesResult.isError || productsResult.isError) {
    return (
      <ErrorNotice
        className="container service-notice"
        error={categoriesResult.error ?? productsResult.error}
        fallback="Не вдалося завантажити каталог."
        onRetry={() => {
          void categoriesResult.refetch();
          void productsResult.refetch();
        }}
      />
    );
  }

  const categories = categoriesResult.data;
  const products = productsResult.data;
  const activeCategory = categories.find(
    (item) => item.slug === query.category,
  );
  const activeBrands = new Set(query.brand);
  const activeSpecs = new Set(query.spec);
  const basePath = category ? `/catalog/${category}` : "/catalog";

  return (
    <div className="container catalog-page">
      <nav aria-label="Навігаційний ланцюжок" className="breadcrumbs">
        <Link to="/">Головна</Link>
        <span>/</span>
        <Link to="/catalog">Каталог</Link>
        {activeCategory ? (
          <>
            <span>/</span>
            <span>{activeCategory.name}</span>
          </>
        ) : null}
      </nav>
      <div className="catalog-title">
        <div>
          <span className="eyebrow">Каталог</span>
          <h1>{activeCategory?.name ?? "Усі товари"}</h1>
          <p>{products.total} позицій за поточними умовами</p>
        </div>
      </div>

      <Form action={basePath} className="catalog-mobile-search" method="get">
        <Search size={18} />
        <input
          aria-label="Пошук у каталозі"
          defaultValue={query.search}
          minLength={2}
          name="search"
          placeholder="Знайти товар"
        />
        <button type="submit">Знайти</button>
      </Form>

      <div className="catalog-layout">
        <aside className="filters">
          <input
            aria-controls="catalog-filter-form"
            aria-label="Показати фільтри"
            className="filters__toggle"
            id="catalog-filter-toggle"
            type="checkbox"
          />
          <label className="filters__summary" htmlFor="catalog-filter-toggle">
            <Filter size={18} />
            <strong>Фільтри</strong>
            <span />
          </label>
          <div className="filters__title">
            <Filter size={18} />
            <strong>Фільтри</strong>
            <Link to={basePath}>Скинути</Link>
          </div>
          <Form action={basePath} id="catalog-filter-form" method="get">
            {query.search ? (
              <input name="search" type="hidden" value={query.search} />
            ) : null}
            <fieldset>
              <legend>Категорія</legend>
              <select
                aria-label="Категорія"
                defaultValue={activeCategory?.slug ?? ""}
                disabled={Boolean(category)}
                name="category"
              >
                <option value="">Усі категорії</option>
                {categories.map((item) => (
                  <option key={item.id} value={item.slug}>
                    {item.name} ({item.product_count})
                  </option>
                ))}
              </select>
            </fieldset>
            {activeCategory?.subcategories.length ? (
              <fieldset>
                <legend>Підкатегорія</legend>
                <select
                  aria-label="Підкатегорія"
                  defaultValue={query.subcategory ?? ""}
                  name="subcategory"
                >
                  <option value="">Усі</option>
                  {activeCategory.subcategories.map((item) => (
                    <option key={item.id} value={item.slug}>
                      {item.name} ({item.product_count})
                    </option>
                  ))}
                </select>
              </fieldset>
            ) : null}
            <fieldset>
              <legend>Ціна, ₴</legend>
              <div className="price-filter">
                <input
                  aria-label="Мінімальна ціна"
                  defaultValue={query.min_price}
                  inputMode="decimal"
                  min="0"
                  name="min_price"
                  placeholder={products.facets.price.minimum ?? "від"}
                  type="number"
                />
                <input
                  aria-label="Максимальна ціна"
                  defaultValue={query.max_price}
                  inputMode="decimal"
                  min="0"
                  name="max_price"
                  placeholder={products.facets.price.maximum ?? "до"}
                  type="number"
                />
              </div>
            </fieldset>
            {products.facets.brands.length ? (
              <fieldset>
                <legend>Бренд</legend>
                <div className="filter-options">
                  {products.facets.brands.map((brand) => (
                    <label key={brand.value}>
                      <input
                        defaultChecked={activeBrands.has(brand.value)}
                        name="brand"
                        type="checkbox"
                        value={brand.value}
                      />
                      <span>{brand.value}</span>
                      <small>{brand.count}</small>
                    </label>
                  ))}
                </div>
              </fieldset>
            ) : null}
            {Object.entries(products.facets.specs)
              .slice(0, 4)
              .map(([key, options]) => (
                <fieldset key={key}>
                  <legend>{key}</legend>
                  <div className="filter-options">
                    {options.slice(0, 8).map((option) => {
                      const value = `${key}:${option.value}`;
                      return (
                        <label key={value}>
                          <input
                            defaultChecked={activeSpecs.has(value)}
                            name="spec"
                            type="checkbox"
                            value={value}
                          />
                          <span>{option.value}</span>
                          <small>{option.count}</small>
                        </label>
                      );
                    })}
                  </div>
                </fieldset>
              ))}
            <label className="stock-filter">
              <input
                defaultChecked={query.in_stock === "true"}
                name="in_stock"
                type="checkbox"
                value="true"
              />
              Лише в наявності
            </label>
            <button
              className="button button--primary button--wide"
              type="submit"
            >
              Застосувати
            </button>
          </Form>
        </aside>

        <section className="catalog-results">
          <Form action={basePath} className="catalog-toolbar" method="get">
            {[...searchParams.entries()].flatMap(([key, value]) =>
              key === "sort" || key === "page"
                ? []
                : [
                    <input
                      key={`${key}-${value}`}
                      name={key}
                      type="hidden"
                      value={value}
                    />,
                  ],
            )}
            <span>Знайдено: {products.total}</span>
            <label>
              <span>Сортування</span>
              <select
                aria-label="Сортування"
                defaultValue={query.sort}
                name="sort"
              >
                {sorts.map((sort) => (
                  <option key={sort.value} value={sort.value}>
                    {sort.label}
                  </option>
                ))}
              </select>
            </label>
            <button type="submit">Оновити</button>
            <div aria-label="Вигляд каталогу" className="catalog-view-toggle">
              <Link
                aria-label="Показати плиткою"
                aria-current={view === "grid" ? "true" : undefined}
                to={viewHref(searchParams, "grid", category)}
              >
                <LayoutGrid size={17} />
              </Link>
              <Link
                aria-label="Показати списком"
                aria-current={view === "list" ? "true" : undefined}
                to={viewHref(searchParams, "list", category)}
              >
                <List size={18} />
              </Link>
            </div>
          </Form>
          {products.items.length ? (
            <div
              className="product-grid product-grid--catalog"
              data-view={view}
            >
              {products.items.map((product) => (
                <ProductCard key={product.id} layout={view} product={product} />
              ))}
            </div>
          ) : (
            <EmptyState
              actionHref={basePath}
              actionLabel="Скинути фільтри"
              description="Змініть фільтри або пошуковий запит."
              title="Товарів не знайдено"
            />
          )}
          {products.total_pages > 1 ? (
            <nav aria-label="Сторінки каталогу" className="pagination">
              {products.has_prev ? (
                <Link to={pageHref(searchParams, products.page - 1, category)}>
                  ← Назад
                </Link>
              ) : null}
              <span>
                {products.page} / {products.total_pages}
              </span>
              {products.has_next ? (
                <Link to={pageHref(searchParams, products.page + 1, category)}>
                  Далі →
                </Link>
              ) : null}
            </nav>
          ) : null}
        </section>
      </div>
    </div>
  );
}
