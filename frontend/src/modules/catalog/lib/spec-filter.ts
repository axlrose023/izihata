export function encodeSpecFilter(key: string, value: string): string {
  return JSON.stringify([key, value]);
}

export function decodeSpecFilter(raw: string): [string, string] | null {
  if (raw.startsWith("[")) {
    try {
      const pair: unknown = JSON.parse(raw);
      if (
        Array.isArray(pair) &&
        pair.length === 2 &&
        pair.every((part) => typeof part === "string" && part.trim())
      ) {
        return [pair[0].trim(), pair[1].trim()];
      }
    } catch {
      return null;
    }
    return null;
  }
  const at = raw.indexOf(":");
  const key = raw.slice(0, at).trim();
  const value = raw.slice(at + 1).trim();
  return at > 0 && key && value ? [key, value] : null;
}
