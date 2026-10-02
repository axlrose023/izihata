import { useMemo, useState } from "react";

import { responsiveImage } from "@/modules/catalog/lib/responsive-image";
import type { ProductDetail, ProductMedia } from "@/shared/types/api";

import { ProductVisual } from "./product-visual";

export function ProductMediaGallery({ product }: { product: ProductDetail }) {
  const media = useMemo<ProductMedia[]>(() => {
    const primary = product.image_url
      ? [
          {
            id: "primary",
            url: product.image_url,
            alt: product.name,
            position: -1,
            image_variants: product.image_variants,
          },
        ]
      : [];
    return [...primary, ...product.media].filter(
      (item, index, items) =>
        items.findIndex((candidate) => candidate.url === item.url) === index,
    );
  }, [product.image_url, product.image_variants, product.media, product.name]);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const selected = media[selectedIndex] ?? null;

  if (!selected) {
    return (
      <div className="product-detail__visual product-media-gallery__fallback">
        <ProductVisual iconSize={170} product={product} />
      </div>
    );
  }

  return (
    <div className="product-media-gallery">
      <div className="product-detail__visual">
        <img
          alt={selected.alt}
          decoding="async"
          fetchPriority="high"
          {...responsiveImage(
            selected.url,
            "(max-width: 820px) 100vw, 50vw",
            [480, 960, 1600],
            undefined,
            selected.image_variants,
          )}
        />
      </div>
      {media.length > 1 ? (
        <div
          aria-label="Зображення товару"
          className="product-media-gallery__thumbnails"
        >
          {media.map((item, index) => (
            <button
              aria-label={`Показати: ${item.alt}`}
              aria-pressed={index === selectedIndex}
              key={item.id}
              onClick={() => setSelectedIndex(index)}
              type="button"
            >
              <img
                alt=""
                decoding="async"
                loading="lazy"
                {...responsiveImage(
                  item.url,
                  "80px",
                  [80, 160],
                  undefined,
                  item.image_variants,
                )}
              />
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}
