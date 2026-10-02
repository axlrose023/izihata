import { act, cleanup, render, screen } from "@testing-library/react";
import type { ComponentType } from "react";
import { createMemoryRouter, Outlet, RouterProvider } from "react-router-dom";
import { afterEach, expect, it } from "vitest";

import { PageLoadingState } from "./page-loading-state";

let router: ReturnType<typeof createMemoryRouter>;
afterEach(() => {
  cleanup();
  router?.dispose();
});

it.each(["success", "failure"] as const)(
  "shows loading until the initial lazy route settles (%s)",
  async (result) => {
    let resolve!: (value: { Component: ComponentType }) => void;
    let reject!: (error: Error) => void;
    const page = new Promise<{ Component: ComponentType }>((done, fail) => {
      resolve = done;
      reject = fail;
    });
    router = createMemoryRouter(
      [
        {
          element: <Outlet />,
          HydrateFallback: PageLoadingState,
          errorElement: <p role="alert">Не вдалося відкрити сторінку</p>,
          children: [{ path: "/slow", lazy: () => page }],
        },
      ],
      { initialEntries: ["/slow"] },
    );
    render(<RouterProvider router={router} />);
    expect(screen.getByRole("status")).toHaveTextContent(
      "Завантажуємо сторінку…",
    );

    await act(async () => {
      if (result === "success") {
        resolve({ Component: () => <h1>Сторінку завантажено</h1> });
      } else {
        reject(new Error("Could not download route"));
      }
    });

    if (result === "success") {
      expect(await screen.findByRole("heading")).toHaveTextContent(
        "Сторінку завантажено",
      );
    } else {
      expect(await screen.findByRole("alert")).toHaveTextContent(
        "Не вдалося відкрити сторінку",
      );
    }
    expect(screen.queryByRole("status")).toBeNull();
  },
);
