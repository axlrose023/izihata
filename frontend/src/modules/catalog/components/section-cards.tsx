import { ArrowUpRight } from "lucide-react";
import { Link } from "react-router-dom";

import { sectionVisual } from "@/modules/catalog/lib/section-presentation";
import type { CatalogSection } from "@/shared/types/api";
import { pluralizeProducts } from "@/shared/lib/format";
import { VisibleImage } from "@/shared/ui/visible-image";

export function SectionCards({
  sections,
  loading = false,
}: {
  sections: CatalogSection[];
  loading?: boolean;
}) {
  if (loading)
    return (
      <div className="section-card-grid" aria-busy="true">
        <span className="sr-only" role="status">
          Завантажуємо напрями каталогу…
        </span>
        {Array.from({ length: 3 }, (_, index) => (
          <div
            aria-hidden="true"
            className="section-card section-card--skeleton"
            key={index}
          />
        ))}
      </div>
    );
  return (
    <div className="section-card-grid">
      {sections.map((section) => {
        const visual = sectionVisual(section);
        return (
          // The whole card is the link, so the picture is clickable too. The
          // call to action is plain text: an anchor inside an anchor is invalid.
          <Link
            className="section-card"
            key={section.id}
            to={`/sections/${section.slug}`}
          >
            <VisibleImage alt={visual.alt} src={visual.image} />
            <div className="section-card__overlay" />
            <div className="section-card__content">
              <span className="section-card__count">
                {pluralizeProducts(section.product_count)}
              </span>
              <h3>{section.name}</h3>
              <p>{visual.subtitle}</p>
              <span className="section-card__cta">
                Перейти <ArrowUpRight aria-hidden="true" size={18} />
              </span>
            </div>
          </Link>
        );
      })}
    </div>
  );
}
