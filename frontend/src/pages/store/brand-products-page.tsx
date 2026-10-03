import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";

import { brandsQuery } from "@/modules/catalog/api/catalog-queries";
import { usePageMeta } from "@/shared/lib/use-page-meta";
import { EmptyState } from "@/shared/ui/empty-state";
import { ErrorNotice } from "@/shared/ui/error-notice";

import { CatalogPage } from "./catalog-page";

export function BrandProductsPage() {
  const { slug = "" } = useParams<{ slug: string }>();
  const result = useQuery(brandsQuery());
  const brand = result.data?.find((item) => item.slug === slug);

  if (result.isPending)
    return <div className="page-loader">Завантажуємо бренд…</div>;
  if (result.isError)
    return (
      <ErrorNotice
        className="container service-notice"
        error={result.error}
        fallback="Не вдалося завантажити бренд."
        onRetry={() => void result.refetch()}
      />
    );
  if (!brand) return <BrandNotFound />;

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

function BrandNotFound() {
  usePageMeta({
    title: "Бренд не знайдено",
    description: "Бренд більше не представлений у каталозі IZI HATA.",
    noindex: true,
  });
  return (
    <EmptyState
      actionHref="/brands"
      actionLabel="Усі виробники"
      description="Бренд не знайдено або він більше не представлений у каталозі."
      title="Бренд не знайдено"
    />
  );
}
