import { useEffect } from "react";
import { matchRoutes, type RouteObject } from "react-router-dom";

import { preloadModule } from "@/shared/lib/module-preload";

export function RoutePreloader({ routes }: { routes: RouteObject[] }) {
  useEffect(() => {
    const prepare = (event: Event) => {
      if (!(event.target instanceof Element)) return;
      const link = event.target.closest("a[href]");
      if (
        !(link instanceof HTMLAnchorElement) ||
        link.hasAttribute("download") ||
        (link.target && link.target !== "_self")
      ) {
        return;
      }
      let url: URL;
      try {
        url = new URL(link.href);
      } catch {
        return;
      }
      if (
        url.origin !== window.location.origin ||
        url.pathname === window.location.pathname
      ) {
        return;
      }
      for (const { route } of matchRoutes(routes, url.pathname) ?? []) {
        // Use the router's own importers. Do not run loaders or render the page.
        if (typeof route.lazy === "function") preloadModule(route.lazy);
      }
    };
    const hover = (event: PointerEvent) => {
      if (event.pointerType === "mouse") prepare(event);
    };

    document.addEventListener("pointerover", hover, { passive: true });
    document.addEventListener("focusin", prepare);
    document.addEventListener("pointerdown", prepare, { passive: true });
    return () => {
      document.removeEventListener("pointerover", hover);
      document.removeEventListener("focusin", prepare);
      document.removeEventListener("pointerdown", prepare);
    };
  }, [routes]);

  return null;
}
