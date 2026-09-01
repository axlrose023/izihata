import { useEffect, useRef } from "react";
import { useLocation } from "react-router-dom";

import { apiFetch } from "@/shared/api/client";

/**
 * Reports one page view per route change so staff can see who is on the site.
 * Failures are ignored on purpose — tracking must never disturb browsing.
 */
export function ActivityTracker() {
  const { pathname } = useLocation();
  const lastReported = useRef<string | null>(null);

  useEffect(() => {
    if (lastReported.current === pathname) return;
    lastReported.current = pathname;
    const controller = new AbortController();
    const timeout = window.setTimeout(() => {
      void apiFetch("/activity/visits", {
        method: "POST",
        body: JSON.stringify({ path: pathname }),
        signal: controller.signal,
      }).catch(() => undefined);
    }, 1_200);
    return () => {
      window.clearTimeout(timeout);
      controller.abort();
    };
  }, [pathname]);

  return null;
}
