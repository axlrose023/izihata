import { expect, it } from "vitest";
import { fitsPasswordBytes } from "./password";

it("checks UTF-8 bytes without truncating Unicode passwords", () => {
  expect(fitsPasswordBytes("Ж".repeat(36))).toBe(true);
  expect(fitsPasswordBytes("Ж".repeat(40))).toBe(false);
  expect(fitsPasswordBytes("a".repeat(72))).toBe(true);
  expect(fitsPasswordBytes("a".repeat(73))).toBe(false);
});
