import { act, cleanup, render } from "@testing-library/react";
import { StrictMode } from "react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import type { ModuleLoader } from "./module-preload";
import { useIdlePreload } from "./use-idle-preload";

function Prepare({ load }: { load: ModuleLoader }) {
  useIdlePreload(load);
  return null;
}

beforeEach(() => vi.useFakeTimers());
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

it("waits for the page to load and for idle time, including in StrictMode", () => {
  const ready = vi.spyOn(document, "readyState", "get");
  ready.mockReturnValue("loading");
  const requestIdle = vi.fn().mockReturnValue(1);
  vi.stubGlobal("requestIdleCallback", requestIdle);
  vi.stubGlobal("cancelIdleCallback", vi.fn());
  const load = vi.fn().mockResolvedValue(undefined);
  render(
    <StrictMode>
      <Prepare load={load} />
    </StrictMode>,
  );
  act(() => vi.advanceTimersByTime(5000));
  expect(load).not.toHaveBeenCalled();
  expect(requestIdle).not.toHaveBeenCalled();
  ready.mockReturnValue("complete");
  act(() => window.dispatchEvent(new Event("load")));
  act(() => vi.advanceTimersByTime(1000));
  expect(load).not.toHaveBeenCalled();
  expect(requestIdle).toHaveBeenCalledTimes(1);
  act(() => requestIdle.mock.calls[0][0]());
  expect(load).toHaveBeenCalledTimes(1);
});

it("cancels pending idle work when the shell unmounts", () => {
  vi.spyOn(document, "readyState", "get").mockReturnValue("complete");
  const requestIdle = vi.fn().mockReturnValue(7);
  const cancelIdle = vi.fn();
  vi.stubGlobal("requestIdleCallback", requestIdle);
  vi.stubGlobal("cancelIdleCallback", cancelIdle);
  const load = vi.fn().mockResolvedValue(undefined);
  const { unmount } = render(<Prepare load={load} />);
  act(() => vi.advanceTimersByTime(1000));
  unmount();
  expect(cancelIdle).toHaveBeenCalledWith(7);
  expect(load).not.toHaveBeenCalled();
});

it("removes the load listener when unmounted before the page loads", () => {
  vi.spyOn(document, "readyState", "get").mockReturnValue("loading");
  const load = vi.fn().mockResolvedValue(undefined);
  const { unmount } = render(<Prepare load={load} />);
  unmount();
  act(() => window.dispatchEvent(new Event("load")));
  act(() => vi.runAllTimers());
  expect(load).not.toHaveBeenCalled();
});

it("also works without requestIdleCallback and cancels its timer on unmount", () => {
  vi.spyOn(document, "readyState", "get").mockReturnValue("complete");
  const load = vi.fn().mockResolvedValue(undefined);
  const { unmount } = render(<Prepare load={load} />);
  act(() => vi.advanceTimersByTime(1000));
  expect(load).toHaveBeenCalledTimes(1);
  unmount();
  const cancelled = vi.fn().mockResolvedValue(undefined);
  render(<Prepare load={cancelled} />).unmount();
  act(() => vi.runAllTimers());
  expect(cancelled).not.toHaveBeenCalled();
});
