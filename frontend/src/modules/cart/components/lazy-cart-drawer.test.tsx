import { act, cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { useCartStore } from "../store";
import { LazyCartDrawer } from "./lazy-cart-drawer";

const { imported } = vi.hoisted(() => ({ imported: vi.fn() }));
vi.mock("./cart-drawer", () => {
  imported();
  return { CartDrawer: () => <div role="dialog">Кошик</div> };
});
afterEach(cleanup);

it("does not load the closed basket and unmounts it when closed", async () => {
  useCartStore.setState({ isOpen: false, lines: [] });
  render(<LazyCartDrawer />);
  expect(imported).not.toHaveBeenCalled();
  act(() => useCartStore.getState().open());
  expect(await screen.findByRole("dialog")).toBeInTheDocument();
  act(() => useCartStore.getState().close());
  expect(screen.queryByRole("dialog")).toBeNull();
  expect(imported).toHaveBeenCalledTimes(1);
});
