import { lazy, Suspense } from "react";
import { useCartStore } from "../store";
import { useIdlePreload } from "@/shared/lib/use-idle-preload";
import { OverlayLoadingState } from "@/shared/ui/overlay-loading-state";
import { loadCartDrawer } from "./load-cart-drawer";

const CartDrawer = lazy(loadCartDrawer);

export function LazyCartDrawer() {
  useIdlePreload(loadCartDrawer);
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
