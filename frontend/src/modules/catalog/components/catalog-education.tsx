import type { Category } from "@/shared/types/api";

const genericAdvice =
  "Порівнюйте технічні параметри з умовами монтажу. Якщо не впевнені у виборі, скористайтесь нашими калькуляторами або консультацією менеджера.";

export function CatalogEducation({ category }: { category?: Category }) {
  return (
    <section className="catalog-education">
      <span className="eyebrow">Підказка для вибору</span>
      <h2>
        {category
          ? `Як підібрати товари в категорії «${category.name}»`
          : "Як підібрати електротовари"}
      </h2>
      <p>{genericAdvice}</p>
    </section>
  );
}
