import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { brandsQuery } from "@/modules/catalog/api/catalog-queries";
import { useDocumentTitle } from "@/shared/lib/use-document-title";
import { usePageMeta } from "@/shared/lib/use-page-meta";
import { EmptyState } from "@/shared/ui/empty-state";
import { ErrorNotice } from "@/shared/ui/error-notice";

import { CatalogPage } from "./catalog-page";

export function BrandsPage() {
  const result = useQuery(brandsQuery());
  useDocumentTitle("Виробники");
  usePageMeta({
    title: "Виробники",
    description:
      "Бренди електротоварів у каталозі IZI HATA з кількістю позицій кожного виробника.",
  });

  if (result.isPending)
    return <div className="page-loader">Завантажуємо виробників…</div>;
  if (result.isError)
    return (
      <ErrorNotice
        className="container service-notice"
        error={result.error}
        fallback="Не вдалося завантажити виробників."
        onRetry={() => void result.refetch()}
      />
    );

  return (
    <div className="container brands-page">
      <nav aria-label="Навігаційний ланцюжок" className="breadcrumbs">
        <Link to="/">Головна</Link>
        <span>/</span>
        <span>Виробники</span>
      </nav>
      <div className="catalog-title">
        <div>
          <span className="eyebrow">Каталог</span>
          <h1>Виробники</h1>
          <p>{result.data.length} брендів у каталозі</p>
        </div>
      </div>
      <div className="brand-grid">
        {result.data.map((brand) => (
          <Link
            className="brand-tile"
            key={brand.id}
            to={`/brands/${brand.slug}`}
          >
            {brand.logo_url ? (
              <img alt={brand.name} loading="lazy" src={brand.logo_url} />
            ) : (
              <span className="brand-tile__fallback">{brand.name}</span>
            )}
            <small>{brand.product_count} товарів</small>
          </Link>
        ))}
      </div>
    </div>
  );
}

export function BrandProductsPage() {
  const { slug = "" } = useParams<{ slug: string }>();
  const result = useQuery(brandsQuery());
  const brand = result.data?.find((item) => item.slug === slug);

  if (result.isPending)
    return <div className="page-loader">Завантажуємо бренд…</div>;
  if (!brand)
    return (
      <EmptyState
        actionHref="/brands"
        actionLabel="Усі виробники"
        description="Бренд не знайдено або він більше не представлений у каталозі."
        title="Бренд не знайдено"
      />
    );

  return (
    <CatalogPage
      presetBrand={brand.name}
      presetDescription={
        brand.description ??
        `Товари бренду ${brand.name} у каталозі IZI HATA: ціни, наявність і характеристики.`
      }
      presetTitle={brand.name}
    />
  );
}
