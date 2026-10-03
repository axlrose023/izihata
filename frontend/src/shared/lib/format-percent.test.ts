import { expect, it } from "vitest";
import { formatPercent } from "./format";

it("preserves the supported discount precision", () => {
  expect(formatPercent("0.0150")).toContain("1,5");
  expect(formatPercent("0.0001")).toContain("0,01");
  expect(formatPercent("0")).toContain("0");
});
