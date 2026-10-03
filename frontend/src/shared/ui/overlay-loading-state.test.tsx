import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { OverlayLoadingState } from "./overlay-loading-state";

afterEach(cleanup);
it("announces loading, freezes the page and permits dismissal before import", () => {
  const close = vi.fn();
  const { unmount } = render(
    <OverlayLoadingState label="Завантажуємо меню" onClose={close} />,
  );
  expect(screen.getByRole("dialog")).toHaveAttribute("aria-modal", "true");
  expect(screen.getByRole("status")).toHaveTextContent("Завантажуємо меню");
  expect(document.body.style.overflow).toBe("hidden");
  fireEvent.click(screen.getByRole("button", { name: "Закрити" }));
  fireEvent.keyDown(document, { key: "Escape" });
  expect(close).toHaveBeenCalledTimes(2);
  unmount();
  expect(document.body.style.overflow).toBe("");
});
