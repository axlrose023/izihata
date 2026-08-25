import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "./errors";
import { apiClient, setCustomerAccessToken } from "./client";

describe("apiClient", () => {
  afterEach(() => {
    setCustomerAccessToken(null);
    vi.unstubAllGlobals();
  });

  it("uses the versioned same-origin API and JSON headers", async () => {
    const fetchMock = vi.fn().mockResolvedValue(Response.json({ ok: true }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(
      apiClient<{ ok: boolean }>("/leads", {
        method: "POST",
        body: JSON.stringify({ type: "callback" }),
      }),
    ).resolves.toEqual({ ok: true });
    const [url, request] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/v1/leads");
    expect(request.method).toBe("POST");
    expect(new Headers(request.headers).get("Accept")).toBe("application/json");
    expect(new Headers(request.headers).get("Content-Type")).toBe(
      "application/json",
    );
  });

  it("attaches the active customer token to customer-priced requests", async () => {
    const fetchMock = vi.fn().mockResolvedValue(Response.json({ ok: true }));
    vi.stubGlobal("fetch", fetchMock);
    setCustomerAccessToken("customer-token");

    await apiClient("/checkout/quote", { method: "POST", body: "{}" });

    const request = fetchMock.mock.calls[0]?.[1] as RequestInit;
    expect(new Headers(request.headers).get("Authorization")).toBe(
      "Bearer customer-token",
    );
  });

  it("returns undefined for a successful empty response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(null, { status: 204 })),
    );
    await expect(
      apiClient<void>("/auth/logout", { method: "POST" }),
    ).resolves.toBeUndefined();
  });

  it("throws a normalized API error", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          Response.json({ detail: "Conflict" }, { status: 409 }),
        ),
    );
    await expect(
      apiClient("/orders", { method: "POST" }),
    ).rejects.toBeInstanceOf(ApiError);
  });

  it("normalizes a browser network failure", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("offline")));

    await expect(apiClient("/catalog/categories")).rejects.toMatchObject({
      code: "network_error",
      status: 0,
    });
  });

  it("normalizes a request timeout", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValue(new DOMException("timed out", "TimeoutError")),
    );

    await expect(apiClient("/catalog/categories")).rejects.toMatchObject({
      code: "request_timeout",
      status: 0,
    });
  });
});
