import { act, cleanup, render } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { Carousel } from "./carousel";

afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.restoreAllMocks();
});
it.each(["touch", "mouse", "reduced"])(
  "uses the expected autoplay policy for %s",
  (device) => {
    vi.useFakeTimers();
    const media = window.matchMedia;
    vi.spyOn(window, "matchMedia").mockImplementation((query) => ({
      ...media(query),
      matches:
        query === "(hover: hover) and (pointer: fine)"
          ? device !== "touch"
          : device === "reduced",
    }));
    const { container } = render(
      <Carousel ariaLabel="Товари" autoplayMs={100}>
        <span>Товар</span>
      </Carousel>,
    );
    const rail = container.querySelector(".carousel__rail")!;
    const scroll = vi.fn();
    Object.defineProperties(rail, {
      clientWidth: { value: 200 },
      scrollWidth: { value: 600 },
      scrollTo: { value: scroll },
    });
    act(() => {
      vi.advanceTimersByTime(300);
    });
    expect(scroll).toHaveBeenCalledTimes(device === "mouse" ? 3 : 0);
  },
);
