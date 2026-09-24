import { Outlet, ScrollRestoration, useLocation } from "react-router-dom";

import { CartDrawer } from "@/modules/cart/components/cart-drawer";
import { StoreHydrator } from "@/shared/ui/store-hydrator";

import { ActivityTracker } from "./activity-tracker";
import { CheckoutHeader } from "./checkout-header";
import { ScrollToTop } from "./scroll-to-top";
import { SiteFooter } from "./site-footer";
import { SiteHeader } from "./site-header";
import { SupportButton } from "./support-button";

export function StoreShell() {
  const { pathname } = useLocation();
  const checkoutFlow =
    pathname === "/checkout" || pathname.startsWith("/order/success");

  return (
    <>
      <StoreHydrator />
      <ScrollRestoration />
      <ActivityTracker />
      {checkoutFlow ? (
        <CheckoutHeader complete={pathname.startsWith("/order/success")} />
      ) : (
        <SiteHeader />
      )}
      <main>
        <Outlet />
      </main>
      {!checkoutFlow ? <SiteFooter /> : null}
      <CartDrawer />
      {!checkoutFlow ? <SupportButton /> : null}
      {!checkoutFlow ? <ScrollToTop /> : null}
    </>
  );
}
