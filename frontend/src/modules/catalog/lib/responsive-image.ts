const mediaHost = "izihata-product-media.b-cdn.net";

export function responsiveImage(
  src: string,
  sizes: string,
  widths: number[] = [160, 320, 640, 960],
  enabled = import.meta.env.VITE_BUNNY_OPTIMIZER_ENABLED === "true",
): { src: string; srcSet?: string; sizes?: string } {
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
