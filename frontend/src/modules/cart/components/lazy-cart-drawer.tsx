import { lazy, Suspense } from "react";
import { useCartStore } from "../store";
import { OverlayLoadingState } from "@/shared/ui/overlay-loading-state";

const CartDrawer = lazy(() =>
  import("./cart-drawer").then((module) => ({ default: module.CartDrawer })),
);

export function LazyCartDrawer() {
  const open = useCartStore((state) => state.isOpen);
  const close = useCartStore((state) => state.close);
  if (!open) return null;
  return (
    <Suspense
      fallback={
        <OverlayLoadingState label="Завантажуємо кошик" onClose={close} />
      }
    >
      <CartDrawer />
    </Suspense>
  );
}
