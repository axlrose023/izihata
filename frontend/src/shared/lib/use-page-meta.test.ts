import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { MemoryRouter, Route, Routes, useNavigate } from "react-router-dom";
import { afterEach, describe, expect, it } from "vitest";
import { createElement } from "react";

import { useDocumentTitle } from "./use-document-title";
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

function TitleOnlyPage() {
  useDocumentTitle("Оформлення замовлення");
  return null;
}

it("replaces product metadata when entering a page with only a title", async () => {
  document.head.insertAdjacentHTML(
    "beforeend",
    '<meta name="robots" content="noindex"><meta property="og:image" content="https://example.com/old.jpg"><script data-page-structured-data="true" type="application/ld+json">{}</script>',
  );
  render(
    createElement(
      MemoryRouter,
      { initialEntries: ["/"] },
      createElement(
        Routes,
        null,
        createElement(Route, { path: "/", element: createElement(MetaProbe) }),
        createElement(Route, {
          path: "/catalog",
          element: createElement(TitleOnlyPage),
        }),
      ),
    ),
  );
  fireEvent.click(screen.getByRole("button", { name: "Next" }));
  await waitFor(() =>
    expect(document.title).toContain("Оформлення замовлення"),
  );
  expect(document.querySelector('meta[name="description"]')).toHaveAttribute(
    "content",
    expect.stringContaining("Каталог електротоварів"),
  );
  expect(document.querySelector('link[rel="canonical"]')).toHaveAttribute(
    "href",
    `${window.location.origin}/catalog?page=2`,
  );
  expect(document.querySelector('meta[property="og:url"]')).toHaveAttribute(
    "content",
    `${window.location.origin}/catalog?page=2`,
  );
  expect(document.querySelector('meta[property="og:image"]')).toBeNull();
  expect(document.querySelector('meta[name="robots"]')).toBeNull();
  expect(
    document.querySelector('script[data-page-structured-data="true"]'),
  ).toBeNull();
});
