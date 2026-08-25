import type { CatalogSection } from "@/shared/types/api";

const sectionPresentation: Record<
  string,
  { image: string; alt: string; subtitle: string }
> = {
  "home-repair": {
    image: "/section-banners/home-repair.webp",
    alt: "Монтаж розетки під час ремонту квартири",
    subtitle: "Все для проводки та ремонту квартири чи будинку.",
  },
  "business-objects": {
    image: "/section-banners/business-objects.webp",
    alt: "Кабельні бухти та промисловий електричний щит",
    subtitle: "Рішення для підрядників, електриків і комерційних об’єктів.",
  },
  "energy-independence": {
    image: "/section-banners/energy-independence.webp",
    alt: "Домашній інвертор і акумулятор для резервного живлення",
    subtitle: "Резервне та автономне живлення для дому і бізнесу.",
  },
};

export function sectionVisual(section: CatalogSection) {
  const presentation = sectionPresentation[section.slug];
  return {
    image:
      section.image_url ?? presentation?.image ?? "/product-images/power.svg",
    alt: presentation?.alt ?? `Розділ каталогу ${section.name}`,
    subtitle:
      section.description ??
      presentation?.subtitle ??
      "Добір товарів за призначенням.",
  };
}
