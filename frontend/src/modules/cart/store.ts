import { create } from "zustand";
import { persist } from "zustand/middleware";

import { normalizeCartQuantity } from "./quantity";
import type { Product } from "@/shared/types/api";

export const MAX_CART_LINES = 100;

export interface CartLine {
  product: Product;
  quantity: number;
}

function record(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function storedProduct(value: unknown): value is Product {
  if (!record(value)) return false;
  const strings = [
    "id",
    "sku",
    "slug",
    "name",
    "brand",
    "price",
    "sale_unit",
    "stock_status",
  ];
  return (
    strings.every(
      (key) => typeof value[key] === "string" && value[key] !== "",
    ) &&
    Number.isFinite(Number(value.price)) &&
    Number(value.price) >= 0 &&
    record(value.category) &&
    typeof value.category.slug === "string" &&
    (value.image_url == null || typeof value.image_url === "string") &&
    (value.image_variants == null ||
      (record(value.image_variants) &&
        Object.values(value.image_variants).every(
          (url) => typeof url === "string",
        )))
  );
}

function restoreLines(value: unknown): CartLine[] {
  if (!Array.isArray(value)) return [];
  const lines = new Map<string, CartLine>();
  for (const line of value) {
    if (!record(line) || !storedProduct(line.product)) continue;
    const quantity = normalizeCartQuantity(Number(line.quantity));
    const previous = lines.get(line.product.id);
    lines.set(line.product.id, {
      product: line.product,
      quantity: normalizeCartQuantity((previous?.quantity ?? 0) + quantity),
    });
  }
  return [...lines.values()];
}

interface CartState {
  lines: CartLine[];
  isOpen: boolean;
  error: string | null;
  add: (product: Product, quantity?: number) => boolean;
  addMany: (lines: CartLine[]) => boolean;
  refreshProducts: (products: Product[], requestedIds: string[]) => void;
  remove: (productId: string) => void;
  setQuantity: (productId: string, quantity: number) => void;
  clear: () => void;
  open: () => void;
  close: () => void;
}

export const useCartStore = create<CartState>()(
  persist(
    (set, get) => ({
      lines: [],
      isOpen: false,
      error: null,
      add: (product, quantity = 1) => get().addMany([{ product, quantity }]),
      addMany: (additions) => {
        let accepted = true;
        set((state) => {
          const lines = [...state.lines];
          for (const { product, quantity } of additions) {
            const index = lines.findIndex(
              (line) => line.product.id === product.id,
            );
            if (index >= 0) {
              lines[index] = {
                product,
                quantity: normalizeCartQuantity(
                  lines[index].quantity + normalizeCartQuantity(quantity),
                ),
              };
            } else {
              lines.push({
                product,
                quantity: normalizeCartQuantity(quantity),
              });
            }
          }
          if (lines.length > MAX_CART_LINES) {
            accepted = false;
            return {
              isOpen: true,
              error: `У кошику може бути до ${MAX_CART_LINES} різних товарів. Видаліть зайві позиції.`,
            };
          }
          return { lines, isOpen: true, error: null };
        });
        return accepted;
      },
      refreshProducts: (products, requestedIds) =>
        set((state) => {
          const current = new Map(
            products.map((product) => [product.id, product]),
          );
          const requested = new Set(requestedIds);
          return {
            lines: state.lines.map((line) => {
              const product = requested.has(line.product.id)
                ? current.get(line.product.id)
                : undefined;
              return product ? { ...line, product } : line;
            }),
          };
        }),
      remove: (productId) =>
        set((state) => ({
          lines: state.lines.filter((line) => line.product.id !== productId),
          error: null,
        })),
      setQuantity: (productId, quantity) =>
        set((state) => ({
          lines: state.lines.map((line) =>
            line.product.id === productId
              ? { ...line, quantity: normalizeCartQuantity(quantity) }
              : line,
          ),
        })),
      clear: () => set({ lines: [], isOpen: false, error: null }),
      open: () => set({ isOpen: true }),
      close: () => set({ isOpen: false }),
    }),
    {
      name: "izihata-cart-v1",
      partialize: (state) => ({ lines: state.lines }),
      skipHydration: true,
      merge: (persisted, current) => {
        const saved = record(persisted) ? persisted : undefined;
        return {
          ...current,
          lines: saved ? restoreLines(saved.lines) : current.lines,
        };
      },
    },
  ),
);

export const cartCount = (lines: CartLine[]) =>
  lines.reduce((total, line) => total + line.quantity, 0);

export const cartQuantityOf = (lines: CartLine[], productId: string) =>
  lines.find((line) => line.product.id === productId)?.quantity ?? 0;
