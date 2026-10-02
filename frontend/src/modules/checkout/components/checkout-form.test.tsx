import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { useCartStore } from "@/modules/cart/store";
import { apiClient } from "@/shared/api/client";
import { ApiError } from "@/shared/api/errors";
import { productFixture } from "@/tests/product-fixture";
import { CheckoutForm } from "./checkout-form";

vi.mock("@/shared/api/client", () => ({ apiClient: vi.fn() }));
vi.mock("@/modules/customers/customer-auth-context", () => ({
  useCustomerAuth: () => ({ status: "guest", sessionVersion: 0 }),
}));
vi.mock("@/shared/lib/use-debounced-value", () => ({
  useDebouncedValue: (value: unknown) => value,
}));
vi.mock("@/modules/checkout/lib/order-retry", () => ({
  orderRetryKey: async () => "test-order",
  clearOrderRetry: vi.fn(),
}));

const product = productFixture();
const quote = {
  items: [
    {
      product_id: product.id,
      sku: product.sku,
      name: product.name,
      quantity: 1,
      unit_price: "100.00",
      total: "100.00",
      price_type: "retail",
      stock_status: "in_stock",
    },
  ],
  subtotal: "100.00",
  discount: "0.00",
  total: "100.00",
  promotion: null,
};
const unavailable = new ApiError(
  503,
  "Unavailable",
  undefined,
  "delivery_provider_unavailable",
);

beforeEach(() => {
  vi.clearAllMocks();
  useCartStore.setState({ lines: [{ product, quantity: 1 }], isOpen: false });
});
afterEach(cleanup);

function renderForm(
  cityFails = true,
  pointFails = false,
  pointOptions: unknown[] = [],
) {
  vi.mocked(apiClient).mockImplementation(async (path) => {
    if (path === "/checkout/quote") return quote;
    if (path.startsWith("/delivery/cities")) {
      if (cityFails) throw unavailable;
      return [{ ref: "city-1", name: "Київ", label: "Київ" }];
    }
    if (path.startsWith("/delivery/points")) {
      if (pointFails) throw unavailable;
      return pointOptions;
    }
    throw unavailable; // Never create an order, even inside this regression.
  });
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const view = render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <CheckoutForm />
      </MemoryRouter>
    </QueryClientProvider>,
  );
  fireEvent.change(
    view.container.querySelector('input[name="customer_name"]')!,
    { target: { value: "Аудит форми" } },
  );
  fireEvent.change(view.container.querySelector('input[name="phone"]')!, {
    target: { value: "+380501234567" },
  });
  fireEvent.change(view.container.querySelector('input[name="email"]')!, {
    target: { value: "audit@example.invalid" },
  });
  return { ...view, client };
}

it("allows manual delivery when the city directory fails", async () => {
  renderForm();
  expect(
    screen.getByText("Оплата після підтвердження замовлення"),
  ).toBeInTheDocument();
  expect(
    screen.queryByText(/захищений шлюз|\[строк\]/),
  ).not.toBeInTheDocument();
  const [city, point] = screen.getAllByRole("combobox");
  fireEvent.change(city, { target: { value: "Київ" } });
  await screen.findByText(/Автопідказки Нової пошти/);
  expect(point).not.toBeDisabled();
  fireEvent.change(point, { target: { value: "Відділення № 1" } });
  await screen.findByText(/Адресу введено вручну/);
  fireEvent.click(
    screen.getByRole("button", { name: "Підтвердити замовлення" }),
  );
  await waitFor(() =>
    expect(apiClient).toHaveBeenCalledWith(
      "/orders",
      expect.objectContaining({
        body: expect.stringContaining('"point":"Відділення № 1"'),
      }),
    ),
  );
  expect(useCartStore.getState().lines).toHaveLength(1);
});

it("requires a directory selection while the provider works", async () => {
  const view = renderForm(false);
  fireEvent.change(screen.getAllByRole("combobox")[0], {
    target: { value: "Київ" },
  });
  await waitFor(() =>
    expect(apiClient).toHaveBeenCalledWith(
      expect.stringContaining("/delivery/cities"),
      expect.anything(),
    ),
  );
  expect(screen.getAllByRole("combobox")[1]).toBeDisabled();
  fireEvent.submit(view.container.querySelector("form")!);
  await screen.findByText("Вкажіть відділення");
  expect(
    vi.mocked(apiClient).mock.calls.some(([path]) => path === "/orders"),
  ).toBe(false);
});

it("allows a manual point when only the point directory fails", async () => {
  renderForm(false, true);
  const [city, point] = screen.getAllByRole("combobox");
  fireEvent.focus(city);
  fireEvent.change(city, { target: { value: "Київ" } });
  fireEvent.mouseDown(await screen.findByRole("option", { name: "Київ" }));
  await screen.findByText(/Автопідказки Нової пошти/);
  fireEvent.change(point, { target: { value: "Відділення № 8" } });
  fireEvent.click(
    screen.getByRole("button", { name: "Підтвердити замовлення" }),
  );
  await waitFor(() =>
    expect(apiClient).toHaveBeenCalledWith(
      "/orders",
      expect.objectContaining({
        body: expect.stringContaining('"point":"Відділення № 8"'),
      }),
    ),
  );
});

it("submits the full delivery point description including its number", async () => {
  renderForm(false, false, [
    {
      ref: "point-8",
      label: "вул. Хрещатик, 1",
      name: "Відділення № 8: вул. Хрещатик, 1",
      number: "8",
    },
  ]);
  const [city, point] = screen.getAllByRole("combobox");
  fireEvent.focus(city);
  fireEvent.change(city, { target: { value: "Київ" } });
  fireEvent.mouseDown(await screen.findByRole("option", { name: "Київ" }));
  fireEvent.focus(point);
  fireEvent.change(point, { target: { value: "8" } });
  fireEvent.mouseDown(
    await screen.findByRole("option", { name: "вул. Хрещатик, 1" }),
  );
  fireEvent.click(
    screen.getByRole("button", { name: "Підтвердити замовлення" }),
  );
  await waitFor(() =>
    expect(apiClient).toHaveBeenCalledWith(
      "/orders",
      expect.objectContaining({
        body: expect.stringContaining(
          '"point":"Відділення № 8: вул. Хрещатик, 1"',
        ),
      }),
    ),
  );
});

it("retains the applied promo through temporary failures and retries explicitly", async () => {
  renderForm();
  await waitFor(() =>
    expect(apiClient).toHaveBeenCalledWith(
      "/checkout/quote",
      expect.anything(),
    ),
  );
  vi.mocked(apiClient).mockImplementation(async () => {
    throw new ApiError(503, "Unavailable", undefined, "service_unavailable");
  });
  vi.useFakeTimers();
  try {
    fireEvent.change(screen.getByRole("textbox", { name: "Промокод" }), {
      target: { value: "SAVE" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Застосувати" }));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(50);
    });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(6500);
    });
    expect(
      screen.getByRole("button", { name: "Прибрати промокод SAVE" }),
    ).toBeInTheDocument();
    const before = vi.mocked(apiClient).mock.calls.length;
    fireEvent.click(screen.getByRole("button", { name: "Застосувати" }));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(50);
    });
    expect(vi.mocked(apiClient).mock.calls.length).toBeGreaterThan(before);
    expect(vi.mocked(apiClient).mock.calls.at(-1)?.[1]?.body).toContain(
      '"promo_code":"SAVE"',
    );
  } finally {
    vi.useRealTimers();
  }
});
