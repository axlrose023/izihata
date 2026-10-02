import { useState } from "react";

import { responsiveImage } from "@/modules/catalog/lib/responsive-image";
import type { Product } from "@/shared/types/api";
import { CategoryIcon } from "@/shared/ui/category-icon";
import { VisibleImage } from "@/shared/ui/visible-image";

export function ProductVisual({
  product,
  iconSize,
  imageSizes = "(max-width: 820px) 50vw, 400px",
}: {
  product: Product;
  iconSize: number;
  imageSizes?: string;
}) {
  const [failedVariantUrl, setFailedVariantUrl] = useState<string | null>(null);
  const [failedUrl, setFailedUrl] = useState<string | null>(null);

  if (product.image_url && failedUrl !== product.image_url) {
    return (
      <VisibleImage
        alt={product.name}
        className="product-visual__image"
        decoding="async"
        loading="lazy"
        rootMargin="200px"
        onError={() => {
          if (
            Object.values(product.image_variants ?? {}).some(
              (url) => url !== product.image_url,
            ) &&
            failedVariantUrl !== product.image_url
          )
            setFailedVariantUrl(product.image_url);
          else setFailedUrl(product.image_url);
        }}
        {...(failedVariantUrl === product.image_url
          ? { src: product.image_url }
          : responsiveImage(
              product.image_url,
              imageSizes,
              undefined,
              undefined,
              product.image_variants,
            ))}
      />
    );
  }

  return (
    <CategoryIcon
      size={iconSize}
      slug={product.category.slug}
      strokeWidth={1.1}
    />
  );
}
