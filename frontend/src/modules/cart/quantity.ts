export const MAX_CART_QUANTITY = 999;

export function normalizeCartQuantity(value: number): number {
  return Number.isFinite(value)
    ? Math.max(1, Math.min(MAX_CART_QUANTITY, Math.floor(value)))
    : 1;
}
