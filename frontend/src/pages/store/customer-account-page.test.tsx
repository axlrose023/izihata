import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { expect, it, vi } from "vitest";

import { CustomerAccountPage } from "./customer-account-page";

const state = vi.hoisted(() => ({ status: "rejected", rate: "0.0150" }));
vi.mock("@/modules/customers/customer-auth-context", () => ({
  useCustomerAuth: () => ({
    status: "authenticated",
    sessionVersion: 1,
    request: vi.fn(),
    logout: vi.fn(),
    restore: vi.fn(),
  }),
}));
vi.mock("@tanstack/react-query", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@tanstack/react-query")>()),
  useQueries: () => [
    {
      data: {
        full_name: "Buyer",
        email: "buyer@example.com",
        phone: null,
        company: {
          name: "Company",
          kind: "fop",
          edrpou: "12345678",
          status: state.status,
          cumulative_discount_rate: state.rate,
          manager_name: null,
        },
      },
    },
    {
      data: {
        items: [],
        page: 1,
        total_pages: 0,
        has_next: false,
        has_prev: false,
      },
    },
  ],
}));

it("shows the actual rejected company decision", () => {
  render(
    <MemoryRouter>
      <CustomerAccountPage />
    </MemoryRouter>,
  );
  expect(
    screen.getByText(
      "Реквізити відхилено. Зверніться до магазину для уточнення.",
    ),
  ).toBeVisible();
  expect(
    screen.queryByText(
      "Менеджер перевіряє реквізити. Повідомимо про результат.",
    ),
  ).toBeNull();
});

it("shows the fractional business discount accurately", () => {
  state.status = "approved";
  render(
    <MemoryRouter>
      <CustomerAccountPage />
    </MemoryRouter>,
  );
  expect(screen.getByText(/Накопичувальна знижка:/).textContent).toContain(
    "1,5",
  );
});
