import { afterEach, expect, it, vi } from "vitest";

import { preloadModule } from "./module-preload";

afterEach(() => vi.restoreAllMocks());

it("deduplicates concurrent and completed preparations", async () => {
  let finish!: () => void;
  const load = vi.fn(() => new Promise<void>((resolve) => (finish = resolve)));
  preloadModule(load);
  preloadModule(load);
  expect(load).toHaveBeenCalledTimes(1);
  finish();
  await Promise.resolve();
  preloadModule(load);
  expect(load).toHaveBeenCalledTimes(1);
});

it("allows another preparation after a failed request", async () => {
  const load = vi
    .fn()
    .mockRejectedValueOnce(new Error("Network unavailable"))
    .mockResolvedValue(undefined);
  preloadModule(load);
  await Promise.resolve();
  preloadModule(load);
  expect(load).toHaveBeenCalledTimes(2);
});

it("can prepare after coming online again", () => {
  const online = vi.spyOn(navigator, "onLine", "get");
  const load = vi.fn().mockResolvedValue(undefined);
  online.mockReturnValue(false);
  preloadModule(load);
  expect(load).not.toHaveBeenCalled();
  online.mockReturnValue(true);
  preloadModule(load);
  expect(load).toHaveBeenCalledTimes(1);
});

it.each([
  { saveData: true, effectiveType: "4g" },
  { effectiveType: "2g" },
  { effectiveType: "slow-2g" },
])("does not spend bandwidth on a constrained connection: %j", (connection) => {
  Object.defineProperty(navigator, "connection", {
    configurable: true,
    value: connection,
  });
  try {
    const load = vi.fn().mockResolvedValue(undefined);
    preloadModule(load);
    expect(load).not.toHaveBeenCalled();
  } finally {
    Reflect.deleteProperty(navigator, "connection");
  }
});
