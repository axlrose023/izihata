import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import { SectionCards } from "./section-cards";

afterEach(cleanup);
it("reserves existing section-card geometry without fabricating catalog data", () => {
  const { container, rerender } = render(
    <SectionCards loading sections={[]} />,
  );
  expect(screen.getByRole("status")).toHaveTextContent("Завантажуємо напрями");
  expect(container.querySelectorAll(".section-card")).toHaveLength(3);
  expect(container.querySelectorAll("a, img")).toHaveLength(0);
  rerender(<SectionCards sections={[]} />);
  expect(container.querySelectorAll(".section-card")).toHaveLength(0);
});
