import { lazy, Suspense } from "react";
import { useCartStore } from "../store";

const CartDrawer = lazy(() =>
  import("./cart-drawer").then((module) => ({ default: module.CartDrawer })),
);

export function LazyCartDrawer() {
  const open = useCartStore((state) => state.isOpen);
  if (!open) return null;
  return (
    <Suspense fallback={<p role="status">Завантажуємо кошик…</p>}>
      <CartDrawer />
    </Suspense>
  );
}
