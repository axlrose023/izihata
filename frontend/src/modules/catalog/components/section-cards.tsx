import { ArrowUpRight } from "lucide-react";
import { Link } from "react-router-dom";

import { sectionVisual } from "@/modules/catalog/lib/section-presentation";
import type { CatalogSection } from "@/shared/types/api";

export function SectionCards({ sections }: { sections: CatalogSection[] }) {
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
            <img alt={visual.alt} fetchPriority="high" src={visual.image} />
            <div className="section-card__overlay" />
            <div className="section-card__content">
              <span className="section-card__count">
                {section.product_count} товарів
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
