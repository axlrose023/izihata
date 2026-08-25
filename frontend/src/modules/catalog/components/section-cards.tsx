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
          <article className="section-card" key={section.id}>
            <img alt={visual.alt} fetchPriority="high" src={visual.image} />
            <div className="section-card__overlay" />
            <div className="section-card__content">
              <span>{section.product_count} товарів</span>
              <h3>{section.name}</h3>
              <p>{visual.subtitle}</p>
              <Link to={`/sections/${section.slug}`}>
                Перейти <ArrowUpRight aria-hidden="true" size={18} />
              </Link>
            </div>
          </article>
        );
      })}
    </div>
  );
}
