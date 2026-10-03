import { expect, it } from "vitest";
import { formatMoney } from "./format";

it("keeps kopecks while displaying whole prices compactly", () => {
  expect(formatMoney("96.12")).toContain("96,12");
  expect(formatMoney("0.01")).toContain("0,01");
  expect(formatMoney("100.00")).not.toContain(",00");
  expect(formatMoney("NaN")).toBe("—");
});
