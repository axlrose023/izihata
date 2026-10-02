import { expect, it } from "vitest";
import { responsiveImage } from "./responsive-image";

it("preserves originals when the CDN optimizer is disabled", () => {
  const url = "https://izihata-product-media.b-cdn.net/products/photo.jpg";
  expect(responsiveImage(url, "320px", [160, 320], false)).toEqual({
    src: url,
  });
});
it("uses responsive sizes only on the configured product CDN", () => {
  const url = "https://izihata-product-media.b-cdn.net/products/photo.jpg";
  expect(responsiveImage(url, "80px", [80, 160], true)).toEqual({
    src: `${url}?width=160`,
    srcSet: `${url}?width=80 80w, ${url}?width=160 160w`,
    sizes: "80px",
  });
  expect(
    responsiveImage("/uploads/image.jpg", "80px", [80, 160], true),
  ).toEqual({ src: "/uploads/image.jpg" });
  expect(
    responsiveImage("https://example.com/image.jpg", "80px", [80, 160], true),
  ).toEqual({ src: "https://example.com/image.jpg" });
});

it("uses generated sizes without enabling the paid CDN optimizer", () => {
  expect(
    responsiveImage("original.jpg", "80px", [80, 160], false, {
      "80": "small.webp",
      "160": "medium.webp",
      "320": "large.webp",
    }),
  ).toEqual({
    src: "medium.webp",
    srcSet: "small.webp 80w, medium.webp 160w",
    sizes: "80px",
  });
});
