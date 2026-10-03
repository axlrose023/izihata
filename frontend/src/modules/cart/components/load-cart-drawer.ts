import { preloadModule } from "@/shared/lib/module-preload";

export const loadCartDrawer = () =>
  import("./cart-drawer").then((module) => ({ default: module.CartDrawer }));

export const preloadCartDrawer = () => preloadModule(loadCartDrawer);
