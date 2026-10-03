import { type CSSProperties, useState } from "react";
import { Link } from "react-router-dom";

import { pluralizeProducts } from "@/shared/lib/format";
import type { Category } from "@/shared/types/api";
import { CategoryIcon } from "@/shared/ui/category-icon";

export function CategoryDirectory({ categories }: { categories: Category[] }) {
  const [allCategoriesShown, setAllCategoriesShown] = useState(false);
  const visibleCategories = allCategoriesShown
    ? categories
    : categories.slice(0, 6);

  return (
    <>
      <div className="category-grid">
        {visibleCategories.map((category) => (
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
      {categories.length > 6 ? (
        <button
          aria-expanded={allCategoriesShown}
          className="show-all-button"
          onClick={() => setAllCategoriesShown((value) => !value)}
          type="button"
        >
          {allCategoriesShown
            ? "Згорнути"
            : `Показати всі напрями (${categories.length})`}
        </button>
      ) : null}
    </>
  );
}
