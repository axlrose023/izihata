import { useState } from "react";

import type { Product } from "@/shared/types/api";
import { CategoryIcon } from "@/shared/ui/category-icon";

export function ProductVisual({
  product,
  iconSize,
}: {
  product: Product;
  iconSize: number;
}) {
  const [failedUrl, setFailedUrl] = useState<string | null>(null);

  if (product.image_url && failedUrl !== product.image_url) {
    return (
      <img
        alt={product.name}
        className="product-visual__image"
        decoding="async"
        loading="lazy"
        onError={() => setFailedUrl(product.image_url)}
        src={product.image_url}
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
