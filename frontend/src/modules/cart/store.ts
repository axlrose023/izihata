import { create } from "zustand";
import { persist } from "zustand/middleware";

import { normalizeCartQuantity } from "./quantity";
import type { Product } from "@/shared/types/api";

export const MAX_CART_LINES = 100;

export interface CartLine {
  product: Product;
  quantity: number;
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
        const saved = persisted as Partial<CartState> | undefined;
        return {
          ...current,
          lines: Array.isArray(saved?.lines)
            ? saved.lines.map((line) => ({
                ...line,
                quantity: normalizeCartQuantity(line.quantity),
              }))
            : current.lines,
        };
      },
    },
  ),
);

export const cartCount = (lines: CartLine[]) =>
  lines.reduce((total, line) => total + line.quantity, 0);

export const cartQuantityOf = (lines: CartLine[], productId: string) =>
  lines.find((line) => line.product.id === productId)?.quantity ?? 0;
