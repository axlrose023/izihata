import { act, cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { VisibleImage } from "./visible-image";
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});
it("waits for a visible image before assigning a download URL", () => {
  let callback!: IntersectionObserverCallback;
  const disconnect = vi.fn();
  vi.stubGlobal(
    "IntersectionObserver",
    class {
      constructor(handler: IntersectionObserverCallback) {
        callback = handler;
      }
      observe = vi.fn();
      disconnect = disconnect;
    },
  );
  render(
    <VisibleImage alt="Thumbnail" src="original.jpg" srcSet="small.webp 80w" />,
  );
  const image = screen.getByAltText("Thumbnail");
  expect(image).not.toHaveAttribute("src");
  expect(image).not.toHaveAttribute("srcset");
  act(() =>
    callback(
      [{ isIntersecting: true } as IntersectionObserverEntry],
      {} as IntersectionObserver,
    ),
  );
  expect(image).toHaveAttribute("src", "original.jpg");
  expect(image).toHaveAttribute("srcset", "small.webp 80w");
  expect(disconnect).toHaveBeenCalled();
});
