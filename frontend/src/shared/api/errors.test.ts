import { describe, expect, it } from "vitest";

import { ApiError, getUserErrorMessage, toApiError } from "./errors";

describe("toApiError", () => {
  it("uses a backend detail message", async () => {
    const error = await toApiError(
      Response.json({ detail: "Product not found" }, { status: 404 }),
    );

    expect(error).toBeInstanceOf(ApiError);
    expect(error.status).toBe(404);
    expect(error.message).toBe("Product not found");
  });

  it("preserves a stable backend error code", async () => {
    const error = await toApiError(
      Response.json(
        {
          code: "promotion_invalid",
          detail: "Promotion code is invalid or expired",
        },
        { status: 422 },
      ),
    );

    expect(error.code).toBe("promotion_invalid");
    expect(getUserErrorMessage(error, "Fallback")).toBe(
      "Промокод недійсний або термін його дії минув.",
    );
  });

  it("turns FastAPI validation details into a field message", async () => {
    const error = await toApiError(
      Response.json(
        { detail: [{ loc: ["body", "phone"], msg: "Field required" }] },
        { status: 422 },
      ),
    );

    expect(error.message).toBe("phone: Field required");
  });

  it("does not expose an unreadable upstream response", async () => {
    const error = await toApiError(
      new Response("gateway html", { status: 502 }),
    );

    expect(error.message).toBe("Request failed with status 502");
  });

  it("uses a safe fallback for unknown client errors", () => {
    expect(
      getUserErrorMessage(new TypeError("Failed to fetch"), "Повторіть"),
    ).toBe("Повторіть");
  });

  it.each([
    [401, "Потрібна повторна авторизація."],
    [403, "Недостатньо прав для цієї дії."],
    [404, "Запитувані дані не знайдено."],
    [429, "Забагато запитів. Зачекайте хвилину й повторіть."],
    [503, "На сервері сталася помилка. Спробуйте трохи пізніше."],
    [400, "Fallback"],
  ])("localizes an HTTP %s error without a code", (status, message) => {
    expect(getUserErrorMessage(new ApiError(status, "raw"), "Fallback")).toBe(
      message,
    );
  });
});
