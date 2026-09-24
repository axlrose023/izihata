import { useEffect } from "react";

/**
 * Closes an overlay on Escape.
 *
 * A modal layer that only closes by pointer leaves keyboard users stuck behind
 * it, so every drawer and sheet listens while it is open.
 */
export function useCloseOnEscape(active: boolean, close: () => void): void {
  useEffect(() => {
    if (!active) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") close();
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [active, close]);
}
