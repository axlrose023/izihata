import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Grid2x2, Grid3x3, Search } from "lucide-react";
import {
  Form,
  Link,
  useLocation,
  useParams,
  useSearchParams,
} from "react-router-dom";

import {
  categoriesQuery,
  productsQuery,
} from "@/modules/catalog/api/catalog-queries";
import { CatalogEducation } from "@/modules/catalog/components/catalog-education";
import {
  CatalogFilters,
  type CatalogFilterQuery,
} from "@/modules/catalog/components/catalog-filters";
import { catalogHref } from "@/modules/catalog/lib/catalog-href";
import { ActiveFilters } from "@/modules/catalog/components/active-filters";
import { ProductCard } from "@/modules/catalog/components/product-card";
import type { ProductBadge, ProductSort } from "@/shared/types/api";
import { useInView } from "@/shared/lib/use-in-view";
import { usePageMeta } from "@/shared/lib/use-page-meta";
import { EmptyState } from "@/shared/ui/empty-state";
import { ErrorNotice } from "@/shared/ui/error-notice";
import {
  pluralizePositions,
  pluralizeSubcategories,
} from "@/shared/lib/format";

const sorts: Array<{ value: ProductSort; label: string }> = [
  { value: "popular", label: "Популярні" },
  { value: "newest", label: "Новинки" },
  { value: "price_asc", label: "Від дешевих" },
  { value: "price_desc", label: "Від дорогих" },
  { value: "reviews", label: "За відгуками" },
  { value: "availability", label: "За наявністю" },
];

const saleBadges: ProductBadge[] = ["sale", "promotion", "clearance"];

export function SalePage() {
  return (
    <CatalogPage
      presetBadges={saleBadges}
      presetTitle="Акції та знижки"
      presetDescription="Товари зі зниженою ціною. Стару ціну видно поруч з новою."
    />
  );
}

export function NewArrivalsPage() {
  return (
    <CatalogPage
      presetBadges={["new"]}
      presetTitle="Новинки"
      presetDescription="Позиції, які нещодавно з’явилися в каталозі."
    />
  );
}

export function CatalogPage({
  presetBadges,
  presetBrand,
  presetTitle,
  presetDescription,
}: {
  presetBadges?: ProductBadge[];
  presetBrand?: string;
  presetTitle?: string;
  presetDescription?: string;
} = {}) {
  const { pathname } = useLocation();
  const { category } = useParams<{ category?: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const view = searchParams.get("view") === "large" ? "large" : "grid";
  const query = {
    search: searchParams.get("search") ?? undefined,
    category: category ?? searchParams.get("category") ?? undefined,
    subcategory: searchParams.get("subcategory") ?? undefined,
    section: searchParams.get("section") ?? undefined,
    brand: presetBrand ? [presetBrand] : searchParams.getAll("brand"),
    in_stock: searchParams.get("in_stock") ?? undefined,
    availability: searchParams.getAll("availability"),
    sale_unit: searchParams.getAll("sale_unit"),
    min_price: searchParams.get("min_price") ?? undefined,
    max_price: searchParams.get("max_price") ?? undefined,
    spec: searchParams.getAll("spec"),
    badge: presetBadges ?? searchParams.getAll("badge"),
    sort: searchParams.get("sort") ?? "popular",
    page: searchParams.get("page") ?? "1",
    page_size: 12,
    include_facets: false,
  };
  const [allSubcategoriesShown, setAllSubcategoriesShown] = useState(false);
  const categoriesResult = useQuery(categoriesQuery());
  const productsResult = useQuery(productsQuery(query));
  const initialActiveCategory = categoriesResult.data?.find(
    (item) => item.slug === query.category,
  );
  // Порожні підкатегорії нічого не дають, а решту показуємо за спаданням —
  // артборд Catalog показує кілька найбільших і ховає хвіст за «ще N».
  const rankedSubcategories = [...(initialActiveCategory?.subcategories ?? [])]
    .filter((item) => item.product_count > 0)
    .sort((a, b) => b.product_count - a.product_count);
  const visibleSubcategories = allSubcategoriesShown
    ? rankedSubcategories
    : rankedSubcategories.slice(0, 6);
  const hiddenSubcategories =
    rankedSubcategories.length - visibleSubcategories.length;
  // Інші товари запитуємо лише коли користувач наближається до блоку.
  const { ref: recommendationsRef, isVisible: recommendationsVisible } =
    useInView<HTMLDivElement>();
  const alsoBoughtResult = useQuery({
    ...productsQuery({
      category: query.category,
      sort: "popular",
      page: "1",
      page_size: 20,
      include_facets: false,
    }),
    enabled:
      Boolean(query.category) &&
      recommendationsVisible &&
      productsResult.isSuccess &&
      !productsResult.isPlaceholderData,
  });
  // Беремо ширшу вибірку, бо найпопулярніше зазвичай уже стоїть у сітці —
  // показуємо чотири позиції, яких на екрані ще немає.
  const alsoBought = (alsoBoughtResult.data?.items ?? [])
    .filter(
      (item) =>
        !productsResult.data?.items.some((shown) => shown.id === item.id),
    )
    .slice(0, 4);
  const shownCount = Math.min(
    Number(query.page) * query.page_size,
    productsResult.data?.total ?? 0,
  );
  const pageTitle = presetTitle ?? initialActiveCategory?.name ?? "Каталог";
  usePageMeta({
    title: pageTitle,
    description:
      presetDescription ??
      (initialActiveCategory
        ? `Купити ${initialActiveCategory.name.toLocaleLowerCase("uk-UA")} в IZI HATA: технічні параметри, ціни та наявність.`
        : "Каталог електротоварів IZI HATA: перевіряйте характеристики, ціни та наявність."),
  });

  const categories = categoriesResult.data;
  const products = productsResult.data;
  if (!categories || !products) {
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
    return <div className="page-loader">Завантажуємо каталог…</div>;
  }
  const activeCategory = categories.find(
    (item) => item.slug === query.category,
  );
  const basePath = pathname;
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
          <h1>{presetTitle ?? activeCategory?.name ?? "Усі товари"}</h1>
          <p>{pluralizePositions(products.total)} за поточними умовами</p>
        </div>
      </div>
      {visibleSubcategories.length ? (
        <nav aria-label="Підкатегорії" className="subcategory-chips">
          {visibleSubcategories.map((item) => (
            <Link
              data-active={query.subcategory === item.slug ? "true" : undefined}
              key={item.id}
              to={catalogHref(pathname, searchParams, {
                subcategory: query.subcategory === item.slug ? null : item.slug,
              })}
            >
              {item.name}
              <small>{item.product_count}</small>
            </Link>
          ))}
          {hiddenSubcategories ? (
            <button
              aria-expanded={allSubcategoriesShown}
              onClick={() => setAllSubcategoriesShown((value) => !value)}
              type="button"
            >
              {allSubcategoriesShown
                ? "Згорнути"
                : `Ще ${pluralizeSubcategories(hiddenSubcategories)}`}
            </button>
          ) : null}
        </nav>
      ) : null}

      <Form action={basePath} className="catalog-mobile-search" method="get">
        <Search size={18} />
        {[...searchParams.entries()]
          .filter(([name]) => name !== "search" && name !== "page")
          .map(([name, value], index) => (
            <input
              type="hidden"
              name={name}
              value={value}
              key={`${name}-${index}`}
            />
          ))}
        <input
          aria-label="Пошук у каталозі"
          defaultValue={query.search}
          key={query.search}
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
          params={query}
          query={filterQuery}
          total={products.total}
        />

        <section
          className="catalog-results"
          aria-busy={productsResult.isFetching}
        >
          <div className="catalog-toolbar">
            <span>Знайдено: {products.total}</span>
            <label>
              <span>Сортування</span>
              <select
                aria-label="Сортування"
                onChange={(event) => {
                  const next = new URLSearchParams(searchParams);
                  next.set("sort", event.target.value);
                  next.delete("page");
                  setSearchParams(next, { replace: true });
                }}
                value={query.sort}
              >
                {sorts.map((sort) => (
                  <option key={sort.value} value={sort.value}>
                    {sort.label}
                  </option>
                ))}
              </select>
            </label>
            <div aria-label="Вигляд каталогу" className="catalog-view-toggle">
              <Link
                aria-label="Дрібніша сітка"
                aria-current={view === "grid" ? "true" : undefined}
                to={catalogHref(pathname, searchParams, { view: null })}
              >
                <Grid3x3 size={17} />
              </Link>
              <Link
                aria-label="Більша сітка"
                aria-current={view === "large" ? "true" : undefined}
                to={catalogHref(pathname, searchParams, { view: "large" })}
              >
                <Grid2x2 size={17} />
              </Link>
            </div>
          </div>
          <ActiveFilters resetHref={basePath} />
          {productsResult.isFetching ? (
            <p className="inline-note" role="status">
              Оновлюємо товари за обраними умовами…
            </p>
          ) : null}
          {productsResult.isError ? (
            <ErrorNotice
              error={productsResult.error}
              fallback="Не вдалося оновити товари."
              onRetry={() => void productsResult.refetch()}
            />
          ) : null}
          {products.items.length ? (
            <div
              className="product-grid product-grid--catalog"
              data-view={view}
            >
              {products.items.map((product) => (
                <ProductCard key={product.id} product={product} />
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
          {products.items.length ? (
            <div className="catalog-progress">
              <span>
                Показано {shownCount} з {products.total}
              </span>
              <span
                aria-hidden="true"
                className="catalog-progress__bar"
                style={{
                  ["--progress" as string]: `${Math.round(
                    (shownCount / Math.max(products.total, 1)) * 100,
                  )}%`,
                }}
              />
            </div>
          ) : null}
          {products.total_pages > 1 ? (
            <nav aria-label="Сторінки каталогу" className="pagination">
              {products.has_prev ? (
                <Link
                  to={catalogHref(pathname, searchParams, {
                    page: String(products.page - 1),
                  })}
                >
                  ← Назад
                </Link>
              ) : null}
              <span>
                {products.page} / {products.total_pages}
              </span>
              {products.has_next ? (
                <Link
                  to={catalogHref(pathname, searchParams, {
                    page: String(products.page + 1),
                  })}
                >
                  Далі →
                </Link>
              ) : null}
            </nav>
          ) : null}
        </section>
      </div>
      {query.category ? (
        <div ref={recommendationsRef} aria-hidden="true" />
      ) : null}
      {alsoBought.length ? (
        <section className="also-bought">
          <div className="section-heading">
            <div>
              <span className="eyebrow">Інші товари</span>
              <h2>Інші товари цієї категорії</h2>
            </div>
          </div>
          <div className="product-grid">
            {alsoBought.map((item) => (
              <ProductCard key={item.id} product={item} />
            ))}
          </div>
        </section>
      ) : null}
      <CatalogEducation category={activeCategory} />
    </div>
  );
}
