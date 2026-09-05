import { useInfiniteQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { fetchProducts } from "@/modules/catalog/api/catalog-api";
import { catalogKeys } from "@/modules/catalog/api/catalog-queries";
import { ProductCard } from "@/modules/catalog/components/product-card";
import { Carousel } from "@/shared/ui/carousel";

const PAGE_SIZE = 5;

export function PopularProducts() {
  // "Показати ще" appends the next page to the rail instead of replacing it.
  const result = useInfiniteQuery({
    queryKey: [...catalogKeys.all, "popular-rail"],
    initialPageParam: 1,
    queryFn: ({ pageParam }) =>
      fetchProducts({
        is_popular: true,
        sort: "popular",
        page: pageParam,
        page_size: PAGE_SIZE,
      }),
    getNextPageParam: (last) => (last.has_next ? last.page + 1 : undefined),
    staleTime: 60_000,
  });
  const items = result.data?.pages.flatMap((page) => page.items) ?? [];

  if (result.isError) return null;
  if (!items.length && result.isPending) {
    return <div className="page-loader">Завантажуємо популярні товари…</div>;
  }
  if (!items.length) return null;

  const hasMore = result.hasNextPage;

  return (
    <section className="section section--tint popular-products">
      <div className="container">
        <div className="section-heading">
          <div>
            <span className="eyebrow">Вибір покупців</span>
            <h2>Популярні товари</h2>
          </div>
          <Link to="/catalog?sort=popular">Увесь каталог →</Link>
        </div>
        <Carousel ariaLabel="Популярні товари" autoplayMs={10_000}>
          {items.map((product) => (
            <div className="carousel__item" key={product.id}>
              <ProductCard product={product} />
            </div>
          ))}
        </Carousel>
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
