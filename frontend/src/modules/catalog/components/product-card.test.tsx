import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { MemoryRouter } from "react-router-dom";

import { useCartStore } from "@/modules/cart/store";
import { useCollectionStore } from "@/modules/collections/store";
import type { Product } from "@/shared/types/api";

import { ProductCard } from "./product-card";

const product: Product = {
  id: "c4a06a4b-6d5b-4c13-b9b4-700f2e266466",
  sku: "TEST-1",
  slug: "test-product",
  name: "Дриль тестовий",
  brand: "Test",
  image_url: "/product-images/automation.svg",
  price: "1000.00",
  old_price: "1200.00",
  badge: "sale",
  stock_status: "in_stock",
  rating: "4.8",
  reviews_count: 4,
  category: { id: "cat", slug: "tools", name: "Інструмент" },
  subcategory: null,
  specs: {},
};

describe("ProductCard", () => {
  beforeEach(() => {
    useCartStore.setState({ lines: [], isOpen: false });
    useCollectionStore.setState({ favorites: [], compare: [] });
  });
  afterEach(cleanup);

  it("links to the product and updates anonymous browser state", () => {
    render(
      <MemoryRouter>
        <ProductCard product={product} />
      </MemoryRouter>,
    );

    expect(screen.getByRole("link", { name: product.name })).toHaveAttribute(
      "href",
      "/products/test-product",
    );
    fireEvent.click(screen.getByRole("button", { name: "Додати в обране" }));
    fireEvent.click(screen.getByRole("button", { name: "Додати в кошик" }));

    expect(useCollectionStore.getState().favorites).toEqual([product.id]);
    expect(useCartStore.getState().lines[0].product.id).toBe(product.id);
    expect(screen.getByRole("img", { name: product.name })).toHaveAttribute(
      "src",
      product.image_url,
    );
    expect(screen.getByLabelText(/Рейтинг 4.8 з 5/)).toBeInTheDocument();
  });

  it("falls back to a category illustration when an image fails", () => {
    render(
      <MemoryRouter>
        <ProductCard product={product} />
      </MemoryRouter>,
    );

    fireEvent.error(screen.getByRole("img", { name: product.name }));

    expect(
      screen.queryByRole("img", { name: product.name }),
    ).not.toBeInTheDocument();
  });
});
