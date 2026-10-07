import { expect, it } from "vitest";

import { prioritizeSubcategories } from "./subcategory-order";

it("shows the four low-voltage breaker types before the other subcategories", () => {
  const ordered = prioritizeSubcategories("lowvoltage", [
    { name: "Запобіжники та тримачі" },
    { name: "Повітряні автоматичні вимикачі" },
    { name: "Модульні автоматичні вимикачі" },
    { name: "Автоматичні вимикачі захисту двигуна" },
    { name: "Силові автоматичні вимикачі" },
  ]);

  expect(ordered.map((item) => item.name)).toEqual([
    "Модульні автоматичні вимикачі",
    "Силові автоматичні вимикачі",
    "Повітряні автоматичні вимикачі",
    "Автоматичні вимикачі захисту двигуна",
    "Запобіжники та тримачі",
  ]);
});

it("leaves other categories in their existing order", () => {
  const input = [{ name: "ЯТП" }, { name: "АВР" }];
  expect(prioritizeSubcategories("panels", input)).toBe(input);
});
