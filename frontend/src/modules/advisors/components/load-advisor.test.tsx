import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";
import { useCartStore } from "@/modules/cart/store";
import { productFixture } from "@/tests/product-fixture";
import { LoadAdvisor } from "./load-advisor";

const cable = productFixture({
  id: "cable",
  name: "Cable",
  sale_unit: "meter",
});
const cableAlternative = productFixture({
  id: "cable-2",
  name: "Other cable",
  sale_unit: "meter",
});
const breaker = productFixture({ id: "breaker", name: "Breaker" });
vi.mock("@/modules/advisors/api/advisor-api", () => ({
  calculateLoad: vi.fn(async () => ({
    cable: {
      products: [cable, cableAlternative],
      recommended_cross_section_mm2: "2.5",
      current_capacity_a: "25",
      requires_specialist: false,
    },
    breaker: {
      products: [breaker],
      recommended_nominal_a: 20,
      recommended_curve: "B",
      requires_specialist: false,
    },
  })),
}));
afterEach(cleanup);
it("adds only the explicitly selected cable and breaker", async () => {
  useCartStore.setState({ lines: [], isOpen: false });
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <LoadAdvisor />
      </MemoryRouter>
    </QueryClientProvider>,
  );
  const add = await screen.findByRole("button", { name: /Додати комплект/ });
  expect(add).toBeDisabled();
  fireEvent.click(await screen.findByRole("radio", { name: "Обрати Cable" }));
  expect(add).toBeDisabled();
  fireEvent.click(screen.getByRole("radio", { name: "Обрати Breaker" }));
  fireEvent.click(add);
  expect(
    useCartStore
      .getState()
      .lines.map((line) => [line.product.id, line.quantity]),
  ).toEqual([
    ["cable", 20],
    ["breaker", 1],
  ]);
});

it("debounces slider changes into one combined request", async () => {
  const { calculateLoad } = await import("@/modules/advisors/api/advisor-api");
  vi.mocked(calculateLoad).mockClear();
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <LoadAdvisor />
      </MemoryRouter>
    </QueryClientProvider>,
  );
  await screen.findByRole("radio", { name: "Обрати Cable" }, { timeout: 3000 });
  const slider = screen.getByRole("slider", { name: "Потужність лінії" });
  for (const value of [4, 4.5, 5])
    fireEvent.change(slider, { target: { value } });
  expect(calculateLoad).toHaveBeenCalledTimes(1);
  expect(
    screen.getByRole("button", { name: /Додати комплект/ }),
  ).toBeDisabled();
  await screen.findByRole("radio", { name: "Обрати Cable" }, { timeout: 3000 });
  expect(calculateLoad).toHaveBeenCalledTimes(2);
  expect(vi.mocked(calculateLoad).mock.calls[1][1]).toBeInstanceOf(AbortSignal);
});
