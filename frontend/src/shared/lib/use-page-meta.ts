import { useEffect } from "react";

const APP_NAME = "IZI HATA";
const trackingParameters = new Set(["fbclid", "gclid", "msclkid"]);

function getOrCreateMeta(name: string): HTMLMetaElement {
  const existing = document.head.querySelector<HTMLMetaElement>(
    `meta[name="${name}"]`,
  );
  if (existing) return existing;

  const meta = document.createElement("meta");
  meta.name = name;
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
}: {
  title: string;
  description: string;
  structuredData?: Record<string, unknown>;
}): void {
  useEffect(() => {
    document.title = `${title} | ${APP_NAME}`;
    getOrCreateMeta("description").content = description;
    getOrCreateCanonical().href = canonicalizeUrl(window.location.href);

    const script = document.head.querySelector<HTMLScriptElement>(
      'script[data-page-structured-data="true"]',
    );
    if (!structuredData) {
      script?.remove();
      return;
    }

    const target = script ?? document.createElement("script");
    target.type = "application/ld+json";
    target.dataset.pageStructuredData = "true";
    target.textContent = JSON.stringify(structuredData);
    if (!script) document.head.append(target);
  }, [description, structuredData, title]);
}
