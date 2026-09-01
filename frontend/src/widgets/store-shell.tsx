import { CartDrawer } from "@/modules/cart/components/cart-drawer";
import { StoreHydrator } from "@/shared/ui/store-hydrator";

import { ActivityTracker } from "./activity-tracker";
import { ScrollToTop } from "./scroll-to-top";
import { SiteFooter } from "./site-footer";
import { SiteHeader } from "./site-header";
import { SupportButton } from "./support-button";

export function StoreShell() {
  return (
    <>
      <StoreHydrator />
      <ActivityTracker />
      <SiteHeader />
      <main>
        <Outlet />
      </main>
      <SiteFooter />
      <CartDrawer />
      <SupportButton />
      <ScrollToTop />
    </>
  );
}
import { Outlet } from "react-router-dom";
