// The server sends only the public resources used by the initial page.
let source: HTMLElement | null = null;
let values: Map<string, unknown> = new Map();
let receivedAt = 0;
function canonicalPath(path: string): string {
  const url = new URL(path, window.location.origin);
  url.searchParams.sort();
  return url.pathname + url.search;
}
export function publicCatalogSeed<T>(path: string): {
  initialData?: T;
  initialDataUpdatedAt?: number;
} {
  const script = document.getElementById("public-catalog-data");
  if (script !== source) {
    source = script;
    values = new Map();
    receivedAt = Date.now();
    if (script) {
      try {
        const data: unknown = JSON.parse(script.textContent ?? "{}");
        if (data && typeof data === "object" && !Array.isArray(data))
          for (const [key, value] of Object.entries(data))
            if (
              key.startsWith("/catalog/") &&
              canonicalPath(key).startsWith("/catalog/")
            )
              values.set(canonicalPath(key), value);
      } catch {
        /* An invalid seed falls back to the normal public API. */
      }
    }
  }
  const data = values.get(canonicalPath(path));
  return data === undefined
    ? {}
    : { initialData: data as T, initialDataUpdatedAt: receivedAt };
}
