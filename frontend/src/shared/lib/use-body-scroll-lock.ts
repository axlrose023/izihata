import { useEffect } from "react";

/**
 * Freezes the page behind an overlay.
 *
 * Without this the document keeps scrolling under an open drawer or menu, so
 * closing it leaves the visitor somewhere they never navigated to.
 */
export function useBodyScrollLock(locked: boolean): void {
  useEffect(() => {
    if (!locked) return;
    const { body } = document;
    const previousOverflow = body.style.overflow;
    const previousPadding = body.style.paddingRight;
    // Replace the scrollbar with padding so the layout does not jump.
    const scrollbar = window.innerWidth - document.documentElement.clientWidth;
    body.style.overflow = "hidden";
    if (scrollbar > 0) body.style.paddingRight = `${scrollbar}px`;
    return () => {
      body.style.overflow = previousOverflow;
      body.style.paddingRight = previousPadding;
    };
  }, [locked]);
}
