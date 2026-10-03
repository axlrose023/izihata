import { useEffect } from "react";

let lockCount = 0;
let restoreBody: (() => void) | undefined;

/**
 * Freezes the page behind an overlay.
 *
 * Without this the document keeps scrolling under an open drawer or menu, so
 * closing it leaves the visitor somewhere they never navigated to.
 */
export function useBodyScrollLock(locked: boolean): void {
  useEffect(() => {
    if (!locked) return;
    if (lockCount++ === 0) {
      const { body } = document;
      const previousOverflow = body.style.overflow;
      const previousPadding = body.style.paddingRight;
      const scrollbar =
        window.innerWidth - document.documentElement.clientWidth;
      const padding =
        Number.parseFloat(getComputedStyle(body).paddingRight) || 0;
      body.style.overflow = "hidden";
      if (scrollbar > 0) body.style.paddingRight = `${padding + scrollbar}px`;
      restoreBody = () => {
        body.style.overflow = previousOverflow;
        body.style.paddingRight = previousPadding;
      };
    }
    return () => {
      if (--lockCount === 0) {
        restoreBody?.();
        restoreBody = undefined;
      }
    };
  }, [locked]);
}
