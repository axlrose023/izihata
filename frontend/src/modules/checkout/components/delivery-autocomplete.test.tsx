import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
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

it("opens suggestions above the field when there is no room below", async () => {
  const bounds = vi
    .spyOn(HTMLInputElement.prototype, "getBoundingClientRect")
    .mockReturnValue({
      x: 0,
      y: 780,
      width: 300,
      height: 40,
      top: 780,
      right: 300,
      bottom: 820,
      left: 0,
      toJSON: () => ({}),
    });
  render(<DeliveryAutocomplete {...props()} />);
  fireEvent.focus(screen.getByRole("combobox"));

  const menu = screen.getByRole("listbox").parentElement;
  await waitFor(() => expect(menu).toHaveAttribute("data-placement", "above"));
  expect(menu).toHaveStyle({ maxHeight: "242px" });
  bounds.mockRestore();
});

it("selects on click rather than on touch press and keeps focus in the input", () => {
  const initial = props();
  render(<DeliveryAutocomplete {...initial} />);
  const input = screen.getByRole("combobox");
  fireEvent.focus(input);
  const option = screen.getAllByRole("option")[0];
  fireEvent.mouseDown(option);
  expect(initial.onSelect).not.toHaveBeenCalled();
  fireEvent.click(option);
  expect(initial.onSelect).toHaveBeenCalledWith(options[0]);
  expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  expect(input).toHaveFocus();
});

it("loads another page without selecting a delivery point", () => {
  const initial = props();
  const load = vi.fn();
  render(<DeliveryAutocomplete {...initial} hasMore onLoadMore={load} />);
  fireEvent.focus(screen.getByRole("combobox"));
  fireEvent.click(screen.getByRole("button", { name: "Показати ще" }));
  expect(load).toHaveBeenCalledOnce();
  expect(initial.onSelect).not.toHaveBeenCalled();
});

it("does not select stale results while the next search is loading", () => {
  const initial = props();
  const { rerender } = render(<DeliveryAutocomplete {...initial} />);
  const input = screen.getByRole("combobox");
  fireEvent.focus(input);
  fireEvent.keyDown(input, { key: "ArrowDown" });
  rerender(<DeliveryAutocomplete {...initial} isLoading />);
  fireEvent.keyDown(input, { key: "Enter" });
  expect(initial.onSelect).not.toHaveBeenCalled();
});
