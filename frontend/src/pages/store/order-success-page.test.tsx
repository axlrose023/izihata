import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, expect, it } from "vitest";
import { OrderSuccessPage } from "./order-success-page";
afterEach(cleanup);
it("gives guests useful order instructions and preserves pickup delivery", () => {
  render(
    <MemoryRouter initialEntries={["/order/success?delivery=pickup"]}>
      <OrderSuccessPage />
    </MemoryRouter>,
  );
  expect(screen.getByText(/Збережіть номер замовлення/)).toBeInTheDocument();
  expect(
    screen.queryByRole("link", { name: /кабінеті/ }),
  ).not.toBeInTheDocument();
  expect(screen.getByText("Самовивіз")).toBeInTheDocument();
});
it("links orders created in the authenticated account to its history", () => {
  render(
    <MemoryRouter
      initialEntries={[
        { pathname: "/order/success", state: { accountOrder: true } },
      ]}
    >
      <OrderSuccessPage />
    </MemoryRouter>,
  );
  expect(
    screen.getByRole("link", { name: "Переглянути замовлення в кабінеті" }),
  ).toHaveAttribute("href", "/account");
});
