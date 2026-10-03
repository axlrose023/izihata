import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import type { ReactNode } from "react";

import { ProductsView } from "./products-view";

const { moduleImported, request } = vi.hoisted(() => ({
  moduleImported: vi.fn(),
  request: vi.fn(async () => ({ items: [], page: 1, total_pages: 0 })),
}));
vi.mock("@/modules/auth/auth-provider", () => ({
  useAuth: () => ({ request }),
}));
vi.mock("@/shared/ui/modal", () => ({
  Modal: ({ children }: { children: ReactNode }) => <>{children}</>,
}));
vi.mock("./product-form-dialog", () => {
  moduleImported();
  return {
    ProductFormDialog: ({ onClose }: { onClose: () => void }) => (
      <div role="dialog" aria-label="Editor">
        <input aria-label="Draft" defaultValue="" />
        <button type="button" onClick={onClose}>
          Close editor
        </button>
      </div>
    ),
  };
});
afterEach(cleanup);

it("loads the editor only on opening and unmounts drafts on close", async () => {
  render(
    <QueryClientProvider client={new QueryClient()}>
      <ProductsView />
    </QueryClientProvider>,
  );
  const open = await screen.findByRole("button", { name: "Додати товар" });
  expect(moduleImported).not.toHaveBeenCalled();
  expect(screen.queryByRole("dialog")).toBeNull();
  fireEvent.click(open);
  const input = await screen.findByLabelText("Draft");
  fireEvent.change(input, { target: { value: "Unsaved product" } });
  fireEvent.click(screen.getByRole("button", { name: "Close editor" }));
  expect(screen.queryByRole("dialog")).toBeNull();
  fireEvent.click(open);
  expect(await screen.findByLabelText("Draft")).toHaveValue("");
  expect(moduleImported).toHaveBeenCalledTimes(1);
});
