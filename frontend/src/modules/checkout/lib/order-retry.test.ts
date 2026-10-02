import { webcrypto } from "node:crypto";
import { afterEach, expect, it, vi } from "vitest";

import { clearOrderRetry, orderRetryKey } from "./order-retry";

vi.stubGlobal("crypto", webcrypto);
afterEach(() => {
  clearOrderRetry();
  vi.resetModules();
});

it("restores the retry key after reload without storing contact data", async () => {
  const payload = JSON.stringify({
    email: "customer@example.com",
    phone: "+380671234567",
    items: [{ product_id: "a", quantity: 1 }],
  });
  const key = await orderRetryKey(payload);
  const stored = sessionStorage.getItem("izihata:order-retry")!;
  expect(stored).not.toContain("customer@example.com");
  expect(stored).not.toContain("+380");
  vi.resetModules();
  const reloaded = await import("./order-retry");
  expect(await reloaded.orderRetryKey(payload)).toBe(key);
  expect(await reloaded.orderRetryKey(`${payload}changed`)).not.toBe(key);
  reloaded.clearOrderRetry();
  expect(sessionStorage.getItem("izihata:order-retry")).toBeNull();
});
