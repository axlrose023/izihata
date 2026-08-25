import { useQuery } from "@tanstack/react-query";
import { ArrowRight, Wrench } from "lucide-react";
import { Link, useParams } from "react-router-dom";

import { sectionsQuery } from "@/modules/catalog/api/catalog-queries";
import { sectionVisual } from "@/modules/catalog/lib/section-presentation";
import { useDocumentTitle } from "@/shared/lib/use-document-title";
import { EmptyState } from "@/shared/ui/empty-state";
import { ErrorNotice } from "@/shared/ui/error-notice";

export function SectionPage() {
  const { section: sectionSlug = "" } = useParams<{ section: string }>();
  const result = useQuery(sectionsQuery());
  const section = result.data?.find((item) => item.slug === sectionSlug);
  useDocumentTitle(section?.name ?? "Розділ каталогу");

  if (result.isPending) {
    return <div className="page-loader">Завантажуємо розділ…</div>;
  }
  if (result.isError) {
    return (
      <ErrorNotice
        className="container service-notice"
        error={result.error}
        fallback="Не вдалося завантажити розділ каталогу."
        onRetry={() => void result.refetch()}
      />
    );
  }
  if (!section) {
    return (
      <EmptyState
        actionHref="/catalog"
        actionLabel="Відкрити каталог"
        description="Можливо, посилання застаріло або розділ тимчасово недоступний."
        title="Розділ не знайдено"
      />
    );
  }

  const visual = sectionVisual(section);
  return (
    <div className="section-hub">
      <nav aria-label="Навігаційний ланцюжок" className="container breadcrumbs">
        <Link to="/">Головна</Link>
        <span>/</span>
        <Link to="/catalog">Каталог</Link>
        <span>/</span>
        <span>{section.name}</span>
      </nav>
      <section className="section-hub__hero">
        <img alt={visual.alt} fetchPriority="high" src={visual.image} />
        <div className="section-hub__hero-overlay" />
        <div className="container section-hub__hero-content">
          <span className="eyebrow">Напрям каталогу</span>
          <h1>{section.name}</h1>
          <p>{visual.subtitle}</p>
          <Link
            className="button button--light"
            to={`/catalog?section=${section.slug}`}
          >
            Усі товари розділу <ArrowRight aria-hidden="true" size={18} />
          </Link>
        </div>
      </section>
      <section className="section container section-hub__categories">
        <div className="section-heading">
          <div>
            <span className="eyebrow">Оберіть категорію</span>
            <h2>Товари за завданням</h2>
          </div>
          <span>{section.product_count} позицій</span>
        </div>
        <div className="section-hub__category-grid">
          {section.categories.map((category) => (
            <article key={category.id}>
              <Wrench aria-hidden="true" size={24} />
              <h3>{category.name}</h3>
              <p>{category.product_count} товарів</p>
              {category.subcategories.length ? (
                <ul>
                  {category.subcategories.map((subcategory) => (
                    <li key={subcategory.id}>
                      <Link
                        to={`/catalog/${category.slug}?subcategory=${encodeURIComponent(subcategory.slug)}`}
                      >
                        {subcategory.name}{" "}
                        <small>({subcategory.product_count})</small>
                      </Link>
                    </li>
                  ))}
                </ul>
              ) : null}
              <Link
                className="section-hub__category-link"
                to={`/catalog/${category.slug}`}
              >
                Переглянути товари <ArrowRight aria-hidden="true" size={17} />
              </Link>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}
