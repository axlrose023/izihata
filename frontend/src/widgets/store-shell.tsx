import { CartDrawer } from "@/modules/cart/components/cart-drawer";
import { StoreHydrator } from "@/shared/ui/store-hydrator";

import { SiteFooter } from "./site-footer";
import { SiteHeader } from "./site-header";

export function StoreShell() {
  return (
    <>
      <StoreHydrator />
      <SiteHeader />
      <main>
        <Outlet />
      </main>
      <SiteFooter />
      <CartDrawer />
    </>
  );
}
import { Outlet } from "react-router-dom";
