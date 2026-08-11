import { describe, expect, it } from "vitest";

import { formatDate, formatMoney, pluralizeProducts } from "./format";

describe("format helpers", () => {
  it("formats decimal strings as Ukrainian hryvnia", () => {
    expect(formatMoney("1299.50")).toContain("1 300");
    expect(formatMoney("1299.50")).toContain("₴");
  });

  it("does not expose NaN for malformed values", () => {
    expect(formatMoney("not-a-number")).toBe("—");
  });

  it("formats ISO dates", () => {
    expect(formatDate("2026-08-10T10:30:00Z")).toContain("2026");
  });

  it.each([
    [1, "1 товар"],
    [2, "2 товари"],
    [5, "5 товарів"],
    [11, "11 товарів"],
    [22, "22 товари"],
  ])("uses Ukrainian product plurals for %i", (count, expected) => {
    expect(pluralizeProducts(count)).toBe(expected);
  });
});
