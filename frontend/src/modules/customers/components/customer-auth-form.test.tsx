import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { expect, it } from "vitest";

import { ApiError } from "@/shared/api/errors";

import {
  CustomerAuthContext,
  type CustomerAuthContextValue,
} from "../customer-auth-context";
import { CustomerAuthForm } from "./customer-auth-form";

it("shows a clear message when the email or phone is already registered", async () => {
  const auth: CustomerAuthContextValue = {
    status: "guest",
    sessionVersion: 0,
    request: async <T,>() => ({}) as T,
    login: async () => undefined,
    register: async () => {
      throw new ApiError(
        409,
        "Duplicate registration contact",
        undefined,
        "customer_contact_exists",
      );
    },
    logout: async () => undefined,
    restore: async () => null,
  };

  render(
    <MemoryRouter initialEntries={["/account/login?mode=register"]}>
      <CustomerAuthContext.Provider value={auth}>
        <CustomerAuthForm />
      </CustomerAuthContext.Provider>
    </MemoryRouter>,
  );

  fireEvent.change(screen.getByLabelText("Ім’я та прізвище"), {
    target: { value: "Олена Покупець" },
  });
  fireEvent.change(screen.getByLabelText("Email"), {
    target: { value: "buyer@example.com" },
  });
  fireEvent.change(screen.getByLabelText("Пароль"), {
    target: { value: "customer-password-123" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Створити акаунт" }));

  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Користувач із такою електронною адресою або номером телефону вже зареєстрований.",
  );
});
