import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "./errors";
import { apiClient } from "./client";

describe("apiClient", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("uses the versioned same-origin API and JSON headers", async () => {
    const fetchMock = vi.fn().mockResolvedValue(Response.json({ ok: true }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(
      apiClient<{ ok: boolean }>("/leads", {
        method: "POST",
        body: JSON.stringify({ type: "callback" }),
      }),
    ).resolves.toEqual({ ok: true });
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/leads",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({
          Accept: "application/json",
          "Content-Type": "application/json",
        }),
      }),
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
