import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, expect, it, vi } from "vitest";

import { apiClient } from "@/shared/api/client";
import { LeadDialog } from "./lead-dialog";

vi.mock("@/shared/api/client", () => ({
  apiClient: vi.fn().mockResolvedValue({}),
}));
vi.mock("@/shared/ui/modal", () => ({
  Modal: ({ children }: { children: ReactNode }) => <div>{children}</div>,
}));
afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

it.each(["callback", "quick_buy"] as const)(
  "retains product context for %s",
  async (type) => {
    render(
      <LeadDialog
        open
        type={type}
        productId="product-123"
        onClose={() => {}}
      />,
    );
    fireEvent.change(screen.getByLabelText("Ім’я"), {
      target: { value: "Олена" },
    });
    fireEvent.change(screen.getByLabelText("Телефон"), {
      target: { value: "+380671234567" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Надіслати" }));
    await waitFor(() => expect(apiClient).toHaveBeenCalled());
    const init = vi.mocked(apiClient).mock.calls[0][1];
    expect(JSON.parse(String(init?.body))).toMatchObject({
      type,
      product_id: "product-123",
    });
  },
);
