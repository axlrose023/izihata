import { useQuery } from "@tanstack/react-query";
import type { CSSProperties } from "react";
import { Link } from "react-router-dom";

import { categoriesQuery } from "@/modules/catalog/api/catalog-queries";
import { pluralizeProducts } from "@/shared/lib/format";
import { usePageMeta } from "@/shared/lib/use-page-meta";
import { CategoryIcon } from "@/shared/ui/category-icon";
import { ErrorNotice } from "@/shared/ui/error-notice";

export function CatalogDirectoryPage() {
  const result = useQuery(categoriesQuery());

  usePageMeta({
    title: "Каталог товарів",
    description:
      "Категорії електротоварів IZI HATA: автоматика, кабель, освітлення та обладнання для монтажу.",
  });

  if (result.isPending) {
    return <div className="page-loader">Завантажуємо категорії…</div>;
  }

  if (result.isError) {
    return (
      <ErrorNotice
        className="container service-notice"
        error={result.error}
        fallback="Не вдалося завантажити категорії."
        onRetry={() => void result.refetch()}
      />
    );
  }

  return (
    <div className="container catalog-directory-page">
      <nav aria-label="Навігаційний ланцюжок" className="breadcrumbs">
        <Link to="/">Головна</Link>
        <span>/</span>
        <span>Каталог</span>
      </nav>
      <section aria-labelledby="catalog-directory-heading">
        <div className="catalog-title">
          <div>
            <span className="eyebrow">Усі категорії</span>
            <h1 id="catalog-directory-heading">Каталог товарів</h1>
          </div>
          <Link className="catalog-directory-page__products-link" to="/catalog">
            Усі товари →
          </Link>
        </div>
        <div className="category-grid">
          {result.data.map((category) => (
            <Link
              className="category-card"
              key={category.id}
              style={{ "--accent": category.accent } as CSSProperties}
              to={`/catalog/${category.slug}`}
            >
              <CategoryIcon size={38} slug={category.slug} />
              <strong>{category.name}</strong>
              <span>{pluralizeProducts(category.product_count)}</span>
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}
