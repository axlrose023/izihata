import type { Subcategory } from "@/shared/types/api";

const lowVoltageBreakerOrder = [
  "Модульні автоматичні вимикачі",
  "Силові автоматичні вимикачі",
  "Повітряні автоматичні вимикачі",
  "Автоматичні вимикачі захисту двигуна",
];

export function prioritizeSubcategories<T extends Pick<Subcategory, "name">>(
  categorySlug: string | undefined,
  subcategories: T[],
): T[] {
  if (categorySlug !== "lowvoltage") return subcategories;

  const priority = new Map(lowVoltageBreakerOrder.map((name, index) => [name, index]));
  return subcategories
    .map((subcategory, index) => ({ subcategory, index }))
    .sort((left, right) => {
      const leftRank = priority.get(left.subcategory.name);
      const rightRank = priority.get(right.subcategory.name);
      if (leftRank !== undefined || rightRank !== undefined) {
        return (leftRank ?? Infinity) - (rightRank ?? Infinity);
      }
      return left.index - right.index;
    })
    .map(({ subcategory }) => subcategory);
}
