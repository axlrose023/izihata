import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { DeliveryAutocomplete } from "./delivery-autocomplete";

afterEach(cleanup);

const options = Array.from({ length: 12 }, (_, index) => ({
  ref: `city-${index}`,
  label: `City ${index}`,
}));

function props() {
  return {
    emptyMessage: "Empty",
    isLoading: false,
    onChange: vi.fn(),
    onSelect: vi.fn(),
    options,
    placeholder: "City",
    value: "City",
  };
}

it("does not select a removed suggestion after the result list shrinks", () => {
  const initial = props();
  const { rerender } = render(<DeliveryAutocomplete {...initial} />);
  const input = screen.getByRole("combobox");
  fireEvent.focus(input);
  for (let index = 0; index < 12; index++)
    fireEvent.keyDown(input, { key: "ArrowDown" });

  rerender(<DeliveryAutocomplete {...initial} options={options.slice(0, 9)} />);
  expect(input).not.toHaveAttribute("aria-activedescendant");
  fireEvent.keyDown(input, { key: "Enter" });
  expect(initial.onSelect).not.toHaveBeenCalled();

  fireEvent.keyDown(input, { key: "ArrowDown" });
  fireEvent.keyDown(input, { key: "Enter" });
  expect(initial.onSelect).toHaveBeenCalledWith(options[0]);
});

it("tracks the selected reference when suggestions are reordered", () => {
  const initial = props();
  const { rerender } = render(<DeliveryAutocomplete {...initial} />);
  const input = screen.getByRole("combobox");
  fireEvent.focus(input);
  fireEvent.keyDown(input, { key: "ArrowDown" });
  rerender(
    <DeliveryAutocomplete {...initial} options={[...options].reverse()} />,
  );
  fireEvent.keyDown(input, { key: "Enter" });
  expect(initial.onSelect).toHaveBeenCalledWith(options[0]);
});
