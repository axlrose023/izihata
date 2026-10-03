import { act, renderHook } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { apiFetch, setCustomerAccessToken } from "./client";
import { useRefreshableSession } from "./use-refreshable-session";

afterEach(() => {
  setCustomerAccessToken(null);
  vi.unstubAllGlobals();
});

it.each(["http", "network"])(
  "reports %s logout failure and permits retry",
  async (failure) => {
    let fail = false;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => {
        if (url.endsWith("/login"))
          return Response.json({ access_token: "token-a" });
        if (url.endsWith("/logout") && fail) {
          if (failure === "network") throw new TypeError("offline");
          return Response.json({ detail: "Unavailable" }, { status: 503 });
        }
        return new Response(null, { status: 204 });
      }),
    );
    const onTokenChange = vi.fn();
    const { result } = renderHook(() =>
      useRefreshableSession("/customer-auth", onTokenChange, false),
    );
    await act(() => result.current.login({ email: "a@example.com" }));
    onTokenChange.mockClear();
    fail = true;
    await act(async () => {
      await expect(result.current.logout()).rejects.toThrow();
    });
    expect(result.current.status).toBe("authenticated");
    expect(onTokenChange).not.toHaveBeenCalledWith(null);
    fail = false;
    await act(() => result.current.logout());
    expect(result.current.status).toBe("guest");
    expect(onTokenChange).toHaveBeenLastCalledWith(null);
  },
);

it("clears the previous account token after a failed account switch", async () => {
  const fetch = vi.fn(async (url: string, init: RequestInit) => {
    if (url.endsWith("/login")) {
      const body = JSON.parse(init.body as string) as { email: string };
      return body.email === "a@example.com"
        ? Response.json({ access_token: "token-a" })
        : Response.json({ detail: "Invalid credentials" }, { status: 401 });
    }
    return Response.json({});
  });
  vi.stubGlobal("fetch", fetch);
  const { result } = renderHook(() =>
    useRefreshableSession("/customer-auth", setCustomerAccessToken, false),
  );
  await act(() => result.current.login({ email: "a@example.com" }));
  expect(result.current.status).toBe("authenticated");
  await act(async () => {
    await expect(
      result.current.login({ email: "b@example.com" }),
    ).rejects.toThrow();
  });
  expect(result.current.status).toBe("guest");
  await apiFetch("/checkout/quote");
  const init = fetch.mock.calls.at(-1)![1];
  expect(new Headers(init.headers).has("Authorization")).toBe(false);
});

it("revokes an unrestored refresh cookie before a failed cold account login", async () => {
  let oldCookie = true;
  const fetch = vi.fn(async (url: string) => {
    if (url.endsWith("/logout")) {
      oldCookie = false;
      return new Response(null, { status: 204 });
    }
    if (url.endsWith("/refresh") && oldCookie) {
      return Response.json({ access_token: "old-account" });
    }
    return Response.json({ detail: "Invalid credentials" }, { status: 401 });
  });
  vi.stubGlobal("fetch", fetch);
  const { result } = renderHook(() =>
    useRefreshableSession("/customer-auth", undefined, false),
  );
  await act(async () => {
    await expect(
      result.current.login({ email: "new@example.com" }),
    ).rejects.toThrow();
  });
  await act(() => result.current.refresh());
  expect(result.current.status).toBe("guest");
  expect(oldCookie).toBe(false);
  expect(fetch.mock.calls.map(([url]) => url)).toEqual([
    "/api/v1/customer-auth/logout",
    "/api/v1/customer-auth/login",
    "/api/v1/customer-auth/refresh",
  ]);
});
