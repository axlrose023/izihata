import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeAll, expect, it } from "vitest";
import { LeadAction } from "./lead-action";
beforeAll(() => {
  HTMLDialogElement.prototype.showModal = function () {
    this.open = true;
  };
  HTMLDialogElement.prototype.close = function () {
    this.open = false;
  };
});
afterEach(cleanup);
it("mounts the lead form only after the action is opened", async () => {
  render(<LeadAction label="Відкрити" type="callback" />);
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Відкрити" }));
  await screen.findByRole("textbox", { name: "Ім’я" });
  fireEvent.click(screen.getByRole("button", { name: "Закрити" }));
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
});
