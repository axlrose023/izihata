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

it("allows nearby cards to preload without changing the gallery default", () => {
  const margins: (string | undefined)[] = [];
  vi.stubGlobal(
    "IntersectionObserver",
    class {
      constructor(
        _handler: IntersectionObserverCallback,
        options?: IntersectionObserverInit,
      ) {
        margins.push(options?.rootMargin);
      }
      observe = vi.fn();
      disconnect = vi.fn();
    },
  );
  render(
    <>
      <VisibleImage alt="Card" src="card.webp" rootMargin="200px" />
      <VisibleImage alt="Gallery" src="gallery.webp" />
    </>,
  );
  expect(margins).toEqual(["200px", "0px"]);
  expect(screen.getByAltText("Card")).not.toHaveAttribute("rootMargin");
});

it("loads normally when IntersectionObserver is unavailable", () => {
  vi.stubGlobal("IntersectionObserver", undefined);
  render(<VisibleImage alt="Fallback" src="original.jpg" />);
  expect(screen.getByAltText("Fallback")).toHaveAttribute(
    "src",
    "original.jpg",
  );
});
