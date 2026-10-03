import { act, cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { useCartStore } from "../store";
import { LazyCartDrawer } from "./lazy-cart-drawer";

const { imported, mounted } = vi.hoisted(() => ({
  imported: vi.fn(),
  mounted: vi.fn(),
}));
vi.mock("./cart-drawer", () => {
  imported();
  return {
    CartDrawer: () => {
      mounted();
      return <div role="dialog">Кошик</div>;
    },
  };
});
afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.restoreAllMocks();
});

it("prepares the basket in idle time but mounts it only while open", async () => {
  vi.useFakeTimers();
  vi.spyOn(document, "readyState", "get").mockReturnValue("complete");
  useCartStore.setState({ isOpen: false, lines: [] });
  render(<LazyCartDrawer />);
  expect(imported).not.toHaveBeenCalled();
  await act(async () => {
    await vi.advanceTimersByTimeAsync(1000);
    await vi.dynamicImportSettled();
  });
  expect(imported).toHaveBeenCalledTimes(1);
  expect(mounted).not.toHaveBeenCalled();
  expect(screen.queryByRole("dialog")).toBeNull();
  vi.useRealTimers();
  act(() => useCartStore.getState().open());
  expect(await screen.findByText("Кошик")).toBeInTheDocument();
  act(() => useCartStore.getState().close());
  expect(screen.queryByRole("dialog")).toBeNull();
  expect(imported).toHaveBeenCalledTimes(1);
});
