import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { brandsQuery } from "@/modules/catalog/api/catalog-queries";
import { Carousel } from "@/shared/ui/carousel";
import { pluralizeProducts } from "@/shared/lib/format";

export function BrandRail() {
  const brands = useQuery(brandsQuery()).data ?? [];
  if (!brands.length) return null;

  return (
    <section className="section container brands-section">
      <div className="section-heading">
        <div>
          <span className="eyebrow">Перевірені виробники</span>
          <h2>Виробники</h2>
        </div>
        <Link to="/brands">Усі бренди →</Link>
      </div>
      <Carousel ariaLabel="Виробники" autoplayMs={10_000}>
        {brands.map((brand) => (
          <Link
            className="carousel__item brand-tile"
            key={brand.id}
            title={`${brand.name} · ${pluralizeProducts(brand.product_count)}`}
            to={`/brands/${brand.slug}`}
          >
            {brand.logo_url ? (
              <img
                alt={brand.name}
                decoding="async"
                loading="lazy"
                src={brand.logo_url}
              />
            ) : (
              <span className="brand-tile__fallback">{brand.name}</span>
            )}
            <small>{pluralizeProducts(brand.product_count)}</small>
          </Link>
        ))}
      </Carousel>
    </section>
  );
}
