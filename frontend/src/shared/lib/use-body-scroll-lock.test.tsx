import { cleanup, render } from "@testing-library/react";
import { StrictMode } from "react";
import { afterEach, expect, it, vi } from "vitest";
import { useBodyScrollLock } from "./use-body-scroll-lock";

function Lock({ enabled }: { enabled: boolean }) {
  useBodyScrollLock(enabled);
  return null;
}

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  document.body.style.cssText = "";
});

it.each(["first", "second"])(
  "retains overlapping locks when %s closes first",
  (first) => {
    document.body.style.overflow = "auto";
    document.body.style.paddingRight = "12px";
    vi.stubGlobal("innerWidth", 400);
    vi.spyOn(document.documentElement, "clientWidth", "get").mockReturnValue(
      385,
    );
    const show = (a: boolean, b: boolean) => (
      <StrictMode>
        <Lock enabled={a} />
        <Lock enabled={b} />
      </StrictMode>
    );
    const { rerender, unmount } = render(show(true, true));
    expect(document.body.style.overflow).toBe("hidden");
    expect(document.body.style.paddingRight).toBe("27px");
    rerender(show(first !== "first", first !== "second"));
    expect(document.body.style.overflow).toBe("hidden");
    expect(document.body.style.paddingRight).toBe("27px");
    unmount();
    expect(document.body.style.overflow).toBe("auto");
    expect(document.body.style.paddingRight).toBe("12px");
  },
);
