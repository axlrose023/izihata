import { describe, expect, it } from "vitest";

import { buildQuery } from "./query";

describe("buildQuery", () => {
  it("repeats array parameters and omits empty values", () => {
    const result = buildQuery({
      brand: ["Bosch", "Makita"],
      page: 2,
      in_stock: true,
      search: "",
      unused: null,
    });

    expect(result).toBe("?brand=Bosch&brand=Makita&page=2&in_stock=true");
  });

  it("returns an empty string when no values are present", () => {
    expect(buildQuery({ value: undefined })).toBe("");
  });
});
