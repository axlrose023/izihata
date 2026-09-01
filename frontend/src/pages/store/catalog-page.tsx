import { useQueries } from "@tanstack/react-query";
import { LayoutGrid, List, Search } from "lucide-react";
import { Form, Link, useParams, useSearchParams } from "react-router-dom";

import {
  categoriesQuery,
  productsQuery,
} from "@/modules/catalog/api/catalog-queries";
import { CatalogEducation } from "@/modules/catalog/components/catalog-education";
import {
  CatalogFilters,
  type CatalogFilterQuery,
} from "@/modules/catalog/components/catalog-filters";
import { ProductCard } from "@/modules/catalog/components/product-card";
import type { ProductSort } from "@/shared/types/api";
import { useDocumentTitle } from "@/shared/lib/use-document-title";
import { usePageMeta } from "@/shared/lib/use-page-meta";
import { EmptyState } from "@/shared/ui/empty-state";
import { ErrorNotice } from "@/shared/ui/error-notice";

const sorts: Array<{ value: ProductSort; label: string }> = [
  { value: "popular", label: "Популярні" },
  { value: "newest", label: "Новинки" },
  { value: "price_asc", label: "Від дешевих" },
  { value: "price_desc", label: "Від дорогих" },
  { value: "reviews", label: "За відгуками" },
  { value: "availability", label: "За наявністю" },
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
    section: searchParams.get("section") ?? undefined,
    brand: searchParams.getAll("brand"),
    in_stock: searchParams.get("in_stock") ?? undefined,
    availability: searchParams.getAll("availability"),
    sale_unit: searchParams.getAll("sale_unit"),
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
  const initialActiveCategory = categoriesResult.data?.find(
    (item) => item.slug === query.category,
  );
  useDocumentTitle(initialActiveCategory?.name ?? "Каталог");
  usePageMeta({
    title: initialActiveCategory?.name ?? "Каталог",
    description: initialActiveCategory
      ? `Купити ${initialActiveCategory.name.toLocaleLowerCase("uk-UA")} в IZI HATA: технічні параметри, ціни та наявність.`
      : "Каталог електротоварів IZI HATA: перевіряйте характеристики, ціни та наявність.",
  });

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
  const basePath = category ? `/catalog/${category}` : "/catalog";
  const filterQuery: CatalogFilterQuery = query;

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
        <CatalogFilters
          action={basePath}
          activeCategory={activeCategory}
          categories={categories}
          categoryIsRouteParam={Boolean(category)}
          facets={products.facets}
          query={filterQuery}
        />

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
      <CatalogEducation category={activeCategory} />
    </div>
  );
}
