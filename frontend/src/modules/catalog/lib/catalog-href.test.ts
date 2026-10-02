import { describe, expect, it } from "vitest";

import { catalogHref } from "./catalog-href";

describe("catalog navigation", () => {
  it.each([
    "/brands/hager",
    "/catalog/sale",
    "/catalog/new",
    "/catalog/tools",
    "/catalog",
  ])("keeps the route and repeated filters on %s", (pathname) => {
    const params = new URLSearchParams(
      "category=tools&brand=Hager&brand=ETI&spec=Полюси:1P&page=1",
    );
    const href = new URL(
      catalogHref(pathname, params, { page: "2" }),
      "https://example.com",
    );
    expect(href.pathname).toBe(pathname);
    expect(href.searchParams.get("category")).toBe("tools");
    expect(href.searchParams.getAll("brand")).toEqual(["Hager", "ETI"]);
    expect(href.searchParams.get("spec")).toBe("Полюси:1P");
    expect(href.searchParams.get("page")).toBe("2");
    expect(params.get("page")).toBe("1");
  });

  it("resets pagination when changing view or subcategory", () => {
    const params = new URLSearchParams("category=tools&page=9&view=large");
    expect(catalogHref("/catalog", params, { view: null })).toBe(
      "/catalog?category=tools",
    );
    expect(catalogHref("/catalog", params, { subcategory: "drills" })).toBe(
      "/catalog?category=tools&view=large&subcategory=drills",
    );
  });
});
