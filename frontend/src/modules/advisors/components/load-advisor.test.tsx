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
  calculateCable: async () => ({
    products: [cable, cableAlternative],
    recommended_cross_section_mm2: "2.5",
    current_capacity_a: "25",
    requires_specialist: false,
  }),
  calculateBreaker: async () => ({
    products: [breaker],
    recommended_nominal_a: 20,
    recommended_curve: "B",
    requires_specialist: false,
  }),
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
