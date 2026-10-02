import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import { productDetailFixture } from "@/tests/product-fixture";
import { ProductMediaGallery } from "./product-media-gallery";
afterEach(cleanup);
it("keeps an image after navigating from a larger cached gallery or shrinking media", () => {
  const original = productDetailFixture({
    image_url: "primary.jpg",
    media: [
      { id: "two", url: "two.jpg", alt: "Second", position: 1 },
      { id: "three", url: "three.jpg", alt: "Third", position: 2 },
    ],
  });
  const { rerender } = render(<ProductMediaGallery product={original} />);
  fireEvent.click(screen.getByRole("button", { name: "Показати: Third" }));
  expect(screen.getByAltText("Third")).toHaveAttribute("src", "three.jpg");
  rerender(<ProductMediaGallery product={{ ...original, media: [] }} />);
  expect(screen.getByAltText(original.name)).toHaveAttribute(
    "src",
    "primary.jpg",
  );
  rerender(
    <ProductMediaGallery
      product={productDetailFixture({ image_url: "next.jpg" })}
    />,
  );
  expect(screen.getByAltText(original.name)).toHaveAttribute("src", "next.jpg");
});
it("falls back from a failed variant to the original and handles a failed original", () => {
  const product = productDetailFixture({
    image_url: "original.jpg",
    image_variants: { "320": "variant.webp" },
  });
  render(<ProductMediaGallery product={product} />);
  fireEvent.error(screen.getByAltText(product.name));
  expect(screen.getByAltText(product.name)).toHaveAttribute(
    "src",
    "original.jpg",
  );
  fireEvent.error(screen.getByAltText(product.name));
  expect(screen.queryByAltText(product.name)).not.toBeInTheDocument();
});
