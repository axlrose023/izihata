import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { MemoryRouter, useNavigate } from "react-router-dom";
import { afterEach, describe, expect, it } from "vitest";
import { createElement } from "react";

import { canonicalizeUrl, usePageMeta } from "./use-page-meta";

describe("canonicalizeUrl", () => {
  it("removes tracking parameters without changing meaningful catalog filters", () => {
    expect(
      canonicalizeUrl(
        "https://izihata.example/catalog/sockets?brand=ABB&utm_source=google&gclid=abc#reviews",
      ),
    ).toBe("https://izihata.example/catalog/sockets?brand=ABB");
  });
});

afterEach(cleanup);

function MetaProbe() {
  usePageMeta({ title: "Каталог", description: "Електротовари" });
  const navigate = useNavigate();
  return createElement(
    "button",
    { onClick: () => navigate("/catalog?page=2&utm_source=test") },
    "Next",
  );
}

it("updates canonical on URL-only navigation", async () => {
  render(
    createElement(
      MemoryRouter,
      { initialEntries: ["/catalog?page=1"] },
      createElement(MetaProbe),
    ),
  );
  expect(document.querySelector('link[rel="canonical"]')).toHaveAttribute(
    "href",
    `${window.location.origin}/catalog?page=1`,
  );
  fireEvent.click(screen.getByRole("button", { name: "Next" }));
  await waitFor(() =>
    expect(document.querySelector('link[rel="canonical"]')).toHaveAttribute(
      "href",
      `${window.location.origin}/catalog?page=2`,
    ),
  );
});
