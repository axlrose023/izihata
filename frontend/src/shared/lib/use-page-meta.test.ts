import { describe, expect, it } from "vitest";

import { canonicalizeUrl } from "./use-page-meta";

describe("canonicalizeUrl", () => {
  it("removes tracking parameters without changing meaningful catalog filters", () => {
    expect(
      canonicalizeUrl(
        "https://izihata.example/catalog/sockets?brand=ABB&utm_source=google&gclid=abc#reviews",
      ),
    ).toBe("https://izihata.example/catalog/sockets?brand=ABB");
  });
});
