import { describe, expect, it } from "vitest";

import { decodeSpecFilter, encodeSpecFilter } from "./spec-filter";

describe("specification URL filters", () => {
  it.each([
    ["Тип: розетка/вилка", "розетка: 230 В"],
    ['Розмір "A"', "[10:20]"],
  ])("round-trips punctuation in %s", (key, value) => {
    expect(decodeSpecFilter(encodeSpecFilter(key, value))).toEqual([
      key,
      value,
    ]);
  });
  it("accepts existing links", () => {
    expect(decodeSpecFilter("Полюси:1P")).toEqual(["Полюси", "1P"]);
  });
  it.each(['["a"]', '["a",5]', "invalid", ":value", "key:"])(
    "rejects malformed filters: %s",
    (raw) => expect(decodeSpecFilter(raw)).toBeNull(),
  );
});
