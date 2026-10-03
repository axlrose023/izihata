import {
  cleanup,
  createEvent,
  fireEvent,
  render,
  screen,
} from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import type { RouteObject } from "react-router-dom";

import { RoutePreloader } from "./route-preloader";

afterEach(cleanup);

it("prepares the matched page on keyboard focus without requesting its data", () => {
  const page = vi.fn().mockResolvedValue({});
  const otherPage = vi.fn().mockResolvedValue({});
  const loader = vi.fn().mockResolvedValue({});
  const routes: RouteObject[] = [
    {
      children: [
        { path: "/catalog/:category", lazy: page, loader },
        { path: "/account", lazy: otherPage },
      ],
    },
  ];
  render(
    <>
      <RoutePreloader routes={routes} />
      <a href="/catalog/cables?sort=price_asc">Каталог</a>
    </>,
  );
  fireEvent.focusIn(screen.getByRole("link"));
  fireEvent.pointerDown(screen.getByRole("link"));
  expect(page).toHaveBeenCalledTimes(1);
  expect(otherPage).not.toHaveBeenCalled();
  expect(loader).not.toHaveBeenCalled();
});

it("prepares nested lazy layouts on touch intent, including on an icon", () => {
  const parent = vi.fn().mockResolvedValue({});
  const page = vi.fn().mockResolvedValue({});
  render(
    <>
      <RoutePreloader
        routes={[
          {
            path: "/account",
            lazy: parent,
            children: [{ path: "orders", lazy: page }],
          },
        ]}
      />
      <a href="/account/orders">
        <svg aria-label="Замовлення" />
      </a>
    </>,
  );
  fireEvent.pointerDown(screen.getByLabelText("Замовлення"));
  expect(parent).toHaveBeenCalledTimes(1);
  expect(page).toHaveBeenCalledTimes(1);
});

it("does not prepare external, download, new-tab, same-page or unknown links", () => {
  const load = vi.fn().mockResolvedValue({});
  render(
    <>
      <RoutePreloader routes={[{ path: "/catalog", lazy: load }]} />
      <a href="https://external.example/catalog">External</a>
      <a href="/catalog" download>
        Download
      </a>
      <a href="/catalog" target="_blank">
        New tab
      </a>
      <a href={`${window.location.pathname}?page=2#catalog`}>Same page</a>
      <a href="/unknown">Unknown</a>
      <a href="http://[">Invalid address</a>
    </>,
  );
  for (const link of screen.getAllByRole("link")) fireEvent.focusIn(link);
  expect(load).not.toHaveBeenCalled();
});

it("prepares on mouse hover but ignores pointer movement from touch scrolling", () => {
  const load = vi.fn().mockResolvedValue({});
  render(
    <>
      <RoutePreloader routes={[{ path: "/catalog", lazy: load }]} />
      <a href="/catalog">Каталог</a>
    </>,
  );
  const link = screen.getByRole("link");
  for (const pointerType of ["touch", "mouse"]) {
    const event = createEvent.pointerOver(link);
    Object.defineProperty(event, "pointerType", { value: pointerType });
    fireEvent(link, event);
    expect(load).toHaveBeenCalledTimes(pointerType === "mouse" ? 1 : 0);
  }
});

it("removes document handlers when unmounted", () => {
  const load = vi.fn().mockResolvedValue({});
  const { unmount } = render(
    <RoutePreloader routes={[{ path: "/catalog", lazy: load }]} />,
  );
  unmount();
  const link = document.createElement("a");
  link.href = "/catalog";
  document.body.appendChild(link);
  try {
    fireEvent.pointerDown(link);
    expect(load).not.toHaveBeenCalled();
  } finally {
    link.remove();
  }
});
