import { useEffect } from "react";

import { preloadModule, type ModuleLoader } from "./module-preload";

export function useIdlePreload(load: ModuleLoader) {
  useEffect(() => {
    let timer: number | undefined;
    let idle: number | undefined;
    const prepare = () => {
      // Let the first screen finish loading before spending bandwidth on overlays.
      timer = window.setTimeout(() => {
        if ("requestIdleCallback" in window) {
          idle = window.requestIdleCallback(() => preloadModule(load));
        } else {
          preloadModule(load);
        }
      }, 1000);
    };

    if (document.readyState === "complete") prepare();
    else window.addEventListener("load", prepare, { once: true });

    return () => {
      window.removeEventListener("load", prepare);
      window.clearTimeout(timer);
      if (idle !== undefined) window.cancelIdleCallback(idle);
    };
  }, [load]);
}
