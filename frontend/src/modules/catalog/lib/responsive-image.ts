const mediaHost = "izihata-product-media.b-cdn.net";

export function responsiveImage(
  src: string,
  sizes: string,
  widths: number[] = [160, 320, 640, 960],
  enabled = import.meta.env.VITE_BUNNY_OPTIMIZER_ENABLED === "true",
  variants?: Record<string, string>,
): { src: string; srcSet?: string; sizes?: string } {
  const generated = Object.entries(variants ?? {})
    .map(([width, url]) => ({ width: Number(width), url }))
    .filter(({ width }) => Number.isFinite(width) && width > 0)
    .sort((a, b) => a.width - b.width);
  if (generated.length) {
    const maximum = Math.max(...widths);
    const capped = generated.filter(({ width }) => width <= maximum);
    const firstLarger = generated.find(({ width }) => width > maximum);
    if (firstLarger && (capped.at(-1)?.width ?? 0) < maximum)
      capped.push(firstLarger);
    return {
      src: capped.at(-1)!.url,
      srcSet: capped.map(({ width, url }) => `${url} ${width}w`).join(", "),
      sizes,
    };
  }
  if (!enabled) return { src };
  let url: URL;
  try {
    url = new URL(src);
  } catch {
    return { src };
  }
  if (url.hostname !== mediaHost) return { src };
  const sized = (width: number) => {
    const variant = new URL(url);
    variant.searchParams.set("width", String(width));
    return variant.toString();
  };
  return {
    src: sized(widths.at(-1)!),
    srcSet: widths.map((width) => `${sized(width)} ${width}w`).join(", "),
    sizes,
  };
}
