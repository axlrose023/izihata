import { useMemo, useState } from "react";

import { VisibleImage } from "@/shared/ui/visible-image";
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
  const [selectedUrl, setSelectedUrl] = useState<string | null>(null);
  const [failedVariantUrl, setFailedVariantUrl] = useState<string | null>(null);
  const [failedOriginalUrl, setFailedOriginalUrl] = useState<string | null>(
    null,
  );
  const selected =
    media.find((item) => item.url === selectedUrl) ?? media[0] ?? null;

  if (!selected) {
    return (
      <div className="product-detail__visual product-media-gallery__fallback">
        <ProductVisual
          iconSize={170}
          product={{ ...product, image_url: null }}
        />
      </div>
    );
  }

  return (
    <div className="product-media-gallery">
      <div className="product-detail__visual">
        {failedOriginalUrl === selected.url ? (
          <ProductVisual
            iconSize={170}
            product={{ ...product, image_url: null }}
          />
        ) : (
          <img
            alt={selected.alt}
            decoding="async"
            fetchPriority="high"
            onError={() => {
              if (
                Object.values(selected.image_variants ?? {}).some(
                  (url) => url !== selected.url,
                ) &&
                failedVariantUrl !== selected.url
              )
                setFailedVariantUrl(selected.url);
              else setFailedOriginalUrl(selected.url);
            }}
            {...(failedVariantUrl === selected.url
              ? { src: selected.url }
              : responsiveImage(
                  selected.url,
                  "(max-width: 820px) 100vw, 50vw",
                  [480, 960, 1600],
                  undefined,
                  selected.image_variants,
                ))}
          />
        )}
      </div>
      {media.length > 1 ? (
        <div
          aria-label="Зображення товару"
          className="product-media-gallery__thumbnails"
        >
          {media.map((item) => (
            <button
              aria-label={`Показати: ${item.alt}`}
              aria-pressed={item.url === selected.url}
              key={item.id}
              onClick={() => {
                setSelectedUrl(item.url);
                setFailedOriginalUrl(null);
              }}
              type="button"
            >
              <VisibleImage
                width={80}
                height={80}
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
