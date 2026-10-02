export function catalogHref(
  pathname: string,
  params: URLSearchParams,
  changes: Record<string, string | null>,
) {
  const next = new URLSearchParams(params);
  next.delete("page");
  for (const [key, value] of Object.entries(changes)) {
    if (value === null) next.delete(key);
    else next.set(key, value);
  }
  const search = next.toString();
  return `${pathname}${search ? `?${search}` : ""}`;
}
