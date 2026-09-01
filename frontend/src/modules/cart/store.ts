import { create } from "zustand";
import { persist } from "zustand/middleware";

import type { Product } from "@/shared/types/api";

export interface CartLine {
  product: Product;
  quantity: number;
}

interface CartState {
  lines: CartLine[];
  isOpen: boolean;
  add: (product: Product, quantity?: number) => void;
  remove: (productId: string) => void;
  setQuantity: (productId: string, quantity: number) => void;
  clear: () => void;
  open: () => void;
  close: () => void;
}

export const useCartStore = create<CartState>()(
  persist(
    (set) => ({
      lines: [],
      isOpen: false,
      add: (product, quantity = 1) =>
        set((state) => {
          const existing = state.lines.find(
            (line) => line.product.id === product.id,
          );
          const lines = existing
            ? state.lines.map((line) =>
                line.product.id === product.id
                  ? {
                      ...line,
                      quantity: Math.min(999, line.quantity + quantity),
                    }
                  : line,
              )
            : [...state.lines, { product, quantity: Math.min(999, quantity) }];
          return { lines, isOpen: true };
        }),
      remove: (productId) =>
        set((state) => ({
          lines: state.lines.filter((line) => line.product.id !== productId),
        })),
      setQuantity: (productId, quantity) =>
        set((state) => ({
          lines: state.lines.map((line) =>
            line.product.id === productId
              ? { ...line, quantity: Math.max(1, Math.min(999, quantity)) }
              : line,
          ),
        })),
      clear: () => set({ lines: [], isOpen: false }),
      open: () => set({ isOpen: true }),
      close: () => set({ isOpen: false }),
    }),
    {
      name: "izihata-cart-v1",
      partialize: (state) => ({ lines: state.lines }),
      skipHydration: true,
    },
  ),
);

export const cartCount = (lines: CartLine[]) =>
  lines.reduce((total, line) => total + line.quantity, 0);

export const cartQuantityOf = (lines: CartLine[], productId: string) =>
  lines.find((line) => line.product.id === productId)?.quantity ?? 0;
