import { useInfiniteQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";

import { fetchProducts } from "@/modules/catalog/api/catalog-api";
import { catalogKeys } from "@/modules/catalog/api/catalog-queries";
import { ProductCard } from "@/modules/catalog/components/product-card";
import { Carousel } from "@/shared/ui/carousel";

const PAGE_SIZE = 5;

// Три добірки під одним заголовком, як на артборді Main.
const rails = [
  {
    id: "popular",
    label: "Популярне",
    href: "/catalog?sort=popular",
    params: { is_popular: true, sort: "popular" as const },
  },
  {
    id: "new",
    label: "Новинки",
    href: "/catalog/new",
    params: { badge: ["new"], sort: "newest" as const },
  },
  {
    id: "sale",
    label: "Акції",
    href: "/catalog/sale",
    params: {
      badge: ["sale", "promotion", "clearance"],
      sort: "popular" as const,
    },
  },
];

export function PopularProducts() {
  const [activeRail, setActiveRail] = useState(rails[0].id);
  const rail = rails.find((item) => item.id === activeRail) ?? rails[0];
  // "Показати ще" appends the next page to the rail instead of replacing it.
  const result = useInfiniteQuery({
    queryKey: [...catalogKeys.all, "home-rail", rail.id],
    initialPageParam: 1,
    queryFn: ({ pageParam }) =>
      fetchProducts({
        ...rail.params,
        page: pageParam,
        page_size: PAGE_SIZE,
      }),
    getNextPageParam: (last) => (last.has_next ? last.page + 1 : undefined),
    staleTime: 60_000,
  });
  const items = result.data?.pages.flatMap((page) => page.items) ?? [];

  const hasMore = result.hasNextPage;

  return (
    <section className="section section--tint popular-products">
      <div className="container">
        <div className="section-heading">
          <div>
            <span className="eyebrow">Вибір покупців</span>
            <h2>Часто купують</h2>
          </div>
          <div className="home-rail-tabs" role="tablist">
            {rails.map((item) => (
              <button
                aria-selected={item.id === rail.id}
                key={item.id}
                onClick={() => setActiveRail(item.id)}
                role="tab"
                type="button"
              >
                {item.label}
              </button>
            ))}
          </div>
          <Link to={rail.href}>Увесь каталог →</Link>
        </div>
        {result.isError || (!items.length && !result.isPending) ? (
          <p className="home-rail-empty">У цій добірці поки порожньо.</p>
        ) : !items.length ? (
          <div className="page-loader">Завантажуємо товари…</div>
        ) : (
          <Carousel ariaLabel={rail.label} autoplayMs={10_000} key={rail.id}>
            {items.map((product) => (
              <div
                className="carousel__item carousel__item--product"
                key={product.id}
              >
                <ProductCard product={product} />
              </div>
            ))}
          </Carousel>
        )}
        {hasMore ? (
          <button
            className="show-all-button"
            disabled={result.isFetchingNextPage}
            onClick={() => void result.fetchNextPage()}
            type="button"
          >
            {result.isFetchingNextPage ? "Завантажуємо…" : "Показати ще"}
          </button>
        ) : null}
      </div>
    </section>
  );
}
