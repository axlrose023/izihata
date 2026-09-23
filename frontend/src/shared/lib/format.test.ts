import { describe, expect, it } from "vitest";

import {
  formatDate,
  formatMoney,
  pluralizePositions,
  pluralizeProducts,
  pluralizeReviews,
} from "./format";

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

  it.each([
    [0, "0 позицій"],
    [1, "1 позиція"],
    [3, "3 позиції"],
    [5, "5 позицій"],
    [11, "11 позицій"],
    [13, "13 позицій"],
    [21, "21 позиція"],
    [104, "104 позиції"],
  ])("uses Ukrainian position plurals for %i", (count, expected) => {
    expect(pluralizePositions(count)).toBe(expected);
  });

  it.each([
    [1, "1 відгук"],
    [4, "4 відгуки"],
    [12, "12 відгуків"],
    [101, "101 відгук"],
  ])("uses Ukrainian review plurals for %i", (count, expected) => {
    expect(pluralizeReviews(count)).toBe(expected);
  });

  it.each([0, 1, 5, 11, 14, 21, 111])(
    "never leaves a bare number for %i",
    (count) => {
      for (const text of [
        pluralizeProducts(count),
        pluralizePositions(count),
        pluralizeReviews(count),
      ]) {
        expect(text).toMatch(/^\d+ \S+$/);
      }
    },
  );
});
