import { useQuery } from "@tanstack/react-query";
import { CreditCard, RotateCcw, ShieldCheck, Truck } from "lucide-react";
import { Link, useParams } from "react-router-dom";

import {
  productQuery,
  productsQuery,
} from "@/modules/catalog/api/catalog-queries";
import { ProductActions } from "@/modules/catalog/components/product-actions";
import { ProductCard } from "@/modules/catalog/components/product-card";
import { ProductVisual } from "@/modules/catalog/components/product-visual";
import { ApiError } from "@/shared/api/errors";
import { formatMoney } from "@/shared/lib/format";
import { useDocumentTitle } from "@/shared/lib/use-document-title";
import { ProductRating } from "@/shared/ui/product-rating";
import { ErrorNotice } from "@/shared/ui/error-notice";
import { StatusBadge } from "@/shared/ui/status-badge";
import { ProductReviews } from "@/modules/reviews/components/product-reviews";

export function ProductPage() {
  const { slug = "" } = useParams<{ slug: string }>();
  const productResult = useQuery(productQuery(slug));
  const product = productResult.data;
  const relatedResult = useQuery({
    ...productsQuery({
      category: product?.category.slug,
      page_size: 5,
      sort: "popular",
    }),
    enabled: Boolean(product),
  });
  useDocumentTitle(product?.name ?? "Товар");

  if (productResult.isPending)
    return <div className="page-loader">Завантажуємо товар…</div>;
  if (
    productResult.error instanceof ApiError &&
    productResult.error.status === 404
  ) {
    return <ProductNotFound />;
  }
  if (productResult.isError || !product) {
    return (
      <ErrorNotice
        className="container service-notice"
        error={productResult.error}
        fallback="Не вдалося завантажити товар."
        onRetry={() => void productResult.refetch()}
      />
    );
  }

  const relatedProducts = (relatedResult.data?.items ?? [])
    .filter((item) => item.id !== product.id)
    .slice(0, 4);
  const quickSpecs = Object.entries(product.specs).slice(0, 4);

  return (
    <div className="container product-page">
      <nav aria-label="Навігаційний ланцюжок" className="breadcrumbs">
        <Link to="/">Головна</Link>
        <span>/</span>
        <Link to="/catalog">Каталог</Link>
        <span>/</span>
        <Link to={`/catalog/${product.category.slug}`}>
          {product.category.name}
        </Link>
        <span>/</span>
        <span>{product.name}</span>
      </nav>
      <div className="product-detail">
        <div className="product-detail__visual">
          {product.badge ? (
            <span data-badge={product.badge}>{product.badge}</span>
          ) : null}
          <ProductVisual iconSize={170} product={product} />
        </div>
        <div className="product-detail__content">
          <span className="eyebrow">
            {product.brand} · SKU {product.sku}
          </span>
          <h1>{product.name}</h1>
          <div className="product-detail__meta">
            <StatusBadge status={product.stock_status} />
            <ProductRating
              rating={product.rating}
              reviews={product.reviews_count}
            />
          </div>
          <div className="product-detail__price">
            <strong>{formatMoney(product.price)}</strong>
            {product.old_price ? (
              <del>{formatMoney(product.old_price)}</del>
            ) : null}
          </div>
          {quickSpecs.length ? (
            <dl className="product-quick-specs">
              {quickSpecs.map(([key, value]) => (
                <div key={key}>
                  <dt>{key}</dt>
                  <dd>{value}</dd>
                </div>
              ))}
            </dl>
          ) : null}
          <ProductActions product={product} />
          <div className="product-detail__benefits">
            <span>
              <ShieldCheck /> Ціна перевіряється перед створенням замовлення
            </span>
            <span>
              <Truck /> Доступні Нова пошта та самовивіз
            </span>
            <span>
              <CreditCard /> Картка, післяплата або рахунок для компанії
            </span>
            <span>
              <RotateCcw /> Офіційна гарантія та повернення протягом 14 днів
            </span>
          </div>
        </div>
      </div>
      <section className="specification-section">
        <div>
          <span className="eyebrow">Технічні дані</span>
          <h2>Характеристики</h2>
        </div>
        <dl className="specification-list">
          {Object.entries(product.specs).map(([key, value]) => (
            <div key={key}>
              <dt>{key}</dt>
              <dd>{value}</dd>
            </div>
          ))}
        </dl>
      </section>
      {relatedProducts.length ? (
        <section className="related-products">
          <div className="section-heading">
            <div>
              <span className="eyebrow">Той самий напрям</span>
              <h2>Схожі товари</h2>
            </div>
            <Link to={`/catalog/${product.category.slug}`}>
              Усі в категорії →
            </Link>
          </div>
          <div className="product-grid">
            {relatedProducts.map((item) => (
              <ProductCard key={item.id} product={item} />
            ))}
          </div>
        </section>
      ) : null}
      <ProductReviews reviews={product.reviews} />
    </div>
  );
}

function ProductNotFound() {
  useDocumentTitle("Товар не знайдено");
  return (
    <div className="container empty-state">
      <div className="empty-state__icon" aria-hidden="true">
        ✦
      </div>
      <h1>Товар не знайдено</h1>
      <p>Посилання застаріло або товар більше не доступний.</p>
      <Link className="button button--primary" to="/catalog">
        До каталогу
      </Link>
    </div>
  );
}
