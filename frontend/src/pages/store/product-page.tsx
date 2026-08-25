import { useQuery } from "@tanstack/react-query";
import {
  CreditCard,
  ExternalLink,
  FileCheck2,
  RotateCcw,
  ShieldCheck,
  Truck,
} from "lucide-react";
import { Link, useParams } from "react-router-dom";

import { productQuery } from "@/modules/catalog/api/catalog-queries";
import { ProductActions } from "@/modules/catalog/components/product-actions";
import { ProductCard } from "@/modules/catalog/components/product-card";
import { ProductMediaGallery } from "@/modules/catalog/components/product-media-gallery";
import { ApiError } from "@/shared/api/errors";
import { formatMoney } from "@/shared/lib/format";
import { useDocumentTitle } from "@/shared/lib/use-document-title";
import { usePageMeta } from "@/shared/lib/use-page-meta";
import { ProductRating } from "@/shared/ui/product-rating";
import { ErrorNotice } from "@/shared/ui/error-notice";
import { StatusBadge } from "@/shared/ui/status-badge";
import { ProductReviews } from "@/modules/reviews/components/product-reviews";

export function ProductPage() {
  const { slug = "" } = useParams<{ slug: string }>();
  const productResult = useQuery(productQuery(slug));
  const product = productResult.data;
  useDocumentTitle(product?.name ?? "Товар");
  usePageMeta({
    title: product?.name ?? "Товар",
    description:
      product?.short_description ??
      product?.description ??
      "Технічні характеристики, наявність та ціна в IZI HATA.",
    structuredData: product ? productStructuredData(product) : undefined,
  });

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

  const quickSpecs = Object.entries(product.specs).slice(0, 4);
  const availabilityText = getAvailabilityText(product);
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
        <ProductMediaGallery product={product} />
        <div className="product-detail__content">
          <span className="eyebrow">
            {product.brand} · SKU {product.sku}
          </span>
          <h1>{product.name}</h1>
          <div className="product-detail__meta">
            <StatusBadge status={product.stock_status} />
            <span className="product-availability-text">
              {availabilityText}
            </span>
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
          <p className="product-sale-unit">
            Ціна за {saleUnitLabel(product.sale_unit)}.{" "}
            {product.wholesale_min_quantity
              ? `Гуртові умови — від ${product.wholesale_min_quantity} од.`
              : "Гуртові умови доступні компаніям після підтвердження."}
          </p>
          {product.short_description ? (
            <p className="product-detail__description">
              {product.short_description}
            </p>
          ) : null}
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
      {product.description ? (
        <section className="product-description-section">
          <span className="eyebrow">Про товар</span>
          <p>{product.description}</p>
        </section>
      ) : null}
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
      <section className="product-origin-section">
        <div>
          <span>Бренд зареєстровано</span>
          <strong>{product.brand_country ?? "Не вказано"}</strong>
        </div>
        <div>
          <span>Країна виробництва</span>
          <strong>{product.production_country ?? "Не вказано"}</strong>
        </div>
      </section>
      {product.documents.length ? (
        <section className="product-documents">
          <div>
            <span className="eyebrow">Документи</span>
            <h2>Сертифікати та інструкції</h2>
          </div>
          <ul>
            {product.documents.map((document) => (
              <li key={document.id}>
                <FileCheck2 aria-hidden="true" size={19} />
                <a href={document.url} rel="noreferrer" target="_blank">
                  {document.title} <ExternalLink aria-hidden="true" size={14} />
                </a>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
      <ProductRelationSection
        eyebrow="Той самий напрям"
        products={product.related}
        title="Схожі товари"
      />
      <ProductRelationSection
        eyebrow="Альтернатива"
        products={product.alternatives}
        title="Аналоги"
      />
      <ProductRelationSection
        eyebrow="Доповнюють товар"
        products={product.bought_together}
        title="З цим купують"
      />
      <ProductReviews productSlug={product.slug} reviews={product.reviews} />
    </div>
  );
}

function ProductRelationSection({
  eyebrow,
  title,
  products,
}: {
  eyebrow: string;
  title: string;
  products: import("@/shared/types/api").Product[];
}) {
  if (!products.length) return null;
  return (
    <section className="related-products">
      <div className="section-heading">
        <div>
          <span className="eyebrow">{eyebrow}</span>
          <h2>{title}</h2>
        </div>
      </div>
      <div className="product-grid">
        {products.map((item) => (
          <ProductCard key={item.id} product={item} />
        ))}
      </div>
    </section>
  );
}

function getAvailabilityText(
  product: import("@/shared/types/api").ProductDetail,
) {
  if (product.availability.dispatch_cutoff_hour) {
    return `Замовте до ${product.availability.dispatch_cutoff_hour}:00 — відправимо сьогодні`;
  }
  if (product.availability.lead_time_days) {
    return `Орієнтовний строк: ${product.availability.lead_time_days} дн.`;
  }
  return product.stock_status === "in_stock"
    ? "Готовий до відвантаження"
    : "Уточніть строк у менеджера";
}

function saleUnitLabel(unit: import("@/shared/types/api").SaleUnit): string {
  return { piece: "одиницю", meter: "метр", coil: "бухту" }[unit];
}

function productStructuredData(
  product: import("@/shared/types/api").ProductDetail,
) {
  return {
    "@context": "https://schema.org",
    "@type": "Product",
    name: product.name,
    sku: product.sku,
    brand: { "@type": "Brand", name: product.brand },
    image: [product.image_url, ...product.media.map((item) => item.url)].filter(
      Boolean,
    ),
    description: product.short_description ?? product.description ?? undefined,
    aggregateRating:
      product.reviews_count > 0
        ? {
            "@type": "AggregateRating",
            ratingValue: product.rating,
            reviewCount: product.reviews_count,
          }
        : undefined,
    offers: {
      "@type": "Offer",
      priceCurrency: "UAH",
      price: product.price,
      availability:
        product.stock_status === "out_of_stock"
          ? "https://schema.org/OutOfStock"
          : "https://schema.org/InStock",
    },
  };
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
