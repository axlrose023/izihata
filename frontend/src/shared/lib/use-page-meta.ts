import { useEffect } from "react";
import { useLocation } from "react-router-dom";

const APP_NAME = "IZI HATA";
const trackingParameters = new Set(["fbclid", "gclid", "msclkid"]);

function getOrCreateMeta(
  name: string,
  attribute: "name" | "property" = "name",
): HTMLMetaElement {
  const existing = document.head.querySelector<HTMLMetaElement>(
    `meta[${attribute}="${name}"]`,
  );
  if (existing) return existing;

  const meta = document.createElement("meta");
  meta.setAttribute(attribute, name);
  document.head.append(meta);
  return meta;
}

function getOrCreateCanonical(): HTMLLinkElement {
  const existing = document.head.querySelector<HTMLLinkElement>(
    'link[rel="canonical"]',
  );
  if (existing) return existing;

  const link = document.createElement("link");
  link.rel = "canonical";
  document.head.append(link);
  return link;
}

export function canonicalizeUrl(href: string): string {
  const url = new URL(href);
  for (const parameter of [...url.searchParams.keys()]) {
    if (parameter.startsWith("utm_") || trackingParameters.has(parameter)) {
      url.searchParams.delete(parameter);
    }
  }
  url.hash = "";
  return url.toString();
}

export function usePageMeta({
  title,
  description,
  structuredData,
  noindex = false,
}: {
  title: string;
  description: string;
  structuredData?: Record<string, unknown>;
  noindex?: boolean;
}): void {
  const { pathname, search } = useLocation();
  useEffect(() => {
    document.title = `${title} | ${APP_NAME}`;
    getOrCreateMeta("description").content = description;
    getOrCreateCanonical().href = canonicalizeUrl(
      new URL(`${pathname}${search}`, window.location.origin).href,
    );

    if (noindex) getOrCreateMeta("robots").content = "noindex";
    else document.querySelector('meta[name="robots"]')?.remove();

    const canonical = getOrCreateCanonical().href;
    getOrCreateMeta("og:title", "property").content = document.title;
    getOrCreateMeta("og:description", "property").content = description;
    getOrCreateMeta("og:url", "property").content = canonical;
    getOrCreateMeta("og:type", "property").content =
      structuredData?.["@type"] === "Product" ? "product" : "website";
    const rawImage = structuredData?.image;
    const image = Array.isArray(rawImage) ? rawImage[0] : rawImage;
    if (typeof image === "string")
      getOrCreateMeta("og:image", "property").content = new URL(
        image,
        window.location.origin,
      ).href;
    else document.querySelector('meta[property="og:image"]')?.remove();
    getOrCreateMeta("twitter:card").content =
      typeof image === "string" ? "summary_large_image" : "summary";

    const script = document.head.querySelector<HTMLScriptElement>(
      'script[data-page-structured-data="true"]',
    );
    if (!structuredData) {
      script?.remove();
      return;
    }

    const target = script ?? document.createElement("script");
    const content = JSON.stringify(structuredData);
    target.type = "application/ld+json";
    target.dataset.pageStructuredData = "true";
    target.textContent = content;
    if (!script) document.head.append(target);

    return () => {
      const current = document.head.querySelector<HTMLScriptElement>(
        'script[data-page-structured-data="true"]',
      );
      if (current === target && current.textContent === content)
        current.remove();
    };
  }, [description, noindex, pathname, search, structuredData, title]);
}
