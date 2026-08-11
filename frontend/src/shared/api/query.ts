export type QueryValue = string | number | boolean | null | undefined;

export function buildQuery(
  values: Record<string, QueryValue | QueryValue[]>,
): string {
  const query = new URLSearchParams();

  for (const [key, rawValue] of Object.entries(values)) {
    const entries = Array.isArray(rawValue) ? rawValue : [rawValue];
    for (const value of entries) {
      if (value !== null && value !== undefined && value !== "") {
        query.append(key, String(value));
      }
    }
  }

  const result = query.toString();
  return result ? `?${result}` : "";
}
