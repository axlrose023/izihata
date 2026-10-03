import { Outlet, ScrollRestoration } from "react-router-dom";

import { LazyCartDrawer } from "@/modules/cart/components/lazy-cart-drawer";
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
      <ScrollRestoration />
      <ActivityTracker />
      <SiteHeader />
      <main>
        <Outlet />
      </main>
      <SiteFooter />
      <LazyCartDrawer />
      <SupportButton />
      <ScrollToTop />
    </>
  );
}
