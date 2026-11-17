import { afterEach, expect, it, vi } from "vitest";

import type { WayForPayWidgetSession } from "@/shared/types/api";
import { openWayForPayWidget, prepareWayForPayWidget } from "./wayforpay";

class Widget {
  closeit() {}
}

afterEach(() => {
  delete window.Wayforpay;
  document.getElementById("widget-wfp-script")?.remove();
  vi.restoreAllMocks();
});

it.each(["approved", "declined", "pending"])(
  "returns widget %s without confirming backend payment",
  async (result) => {
    const close = vi.spyOn(Widget.prototype, "closeit");
    window.Wayforpay = class extends Widget {
      run(
        _parameters: unknown,
        approved: (response: unknown) => void,
        declined: (response: unknown) => void,
        pending: (response: unknown) => void,
      ) {
        ({ approved, declined, pending })[
          result as "approved" | "declined" | "pending"
        ]({});
      }
    };
    await expect(
      openWayForPayWidget({} as WayForPayWidgetSession),
    ).resolves.toBe(result);
    expect(close).toHaveBeenCalledOnce();
  },
);

it("accepts close events only from WayForPay and removes the listener", async () => {
  window.Wayforpay = class extends Widget {
    run() {}
  };
  const remove = vi.spyOn(window, "removeEventListener");
  const result = openWayForPayWidget({} as WayForPayWidgetSession);
  await Promise.resolve();
  const finished = vi.fn();
  void result.then(finished);
  window.dispatchEvent(
    new MessageEvent("message", {
      origin: "https://attacker.invalid",
      data: "WfpWidgetEventClose",
    }),
  );
  await Promise.resolve();
  expect(finished).not.toHaveBeenCalled();
  window.dispatchEvent(
    new MessageEvent("message", {
      origin: "https://secure.wayforpay.com",
      data: "WfpWidgetEventClose",
    }),
  );
  await expect(result).resolves.toBe("closed");
  expect(remove).toHaveBeenCalledWith("message", expect.any(Function));
});

it("cleans up when the widget throws", async () => {
  window.Wayforpay = class extends Widget {
    run() {
      throw new Error("broken");
    }
  };
  const remove = vi.spyOn(window, "removeEventListener");
  await expect(
    openWayForPayWidget({} as WayForPayWidgetSession),
  ).rejects.toThrow(/платіжне вікно/);
  expect(remove).toHaveBeenCalledWith("message", expect.any(Function));
});

it("loads one script for concurrent callers and allows retry after failure", async () => {
  const first = prepareWayForPayWidget();
  expect(prepareWayForPayWidget()).toBe(first);
  const error = expect(first).rejects.toThrow(/завантажити/);
  document
    .getElementById("widget-wfp-script")!
    .dispatchEvent(new Event("error"));
  await error;
  const retry = prepareWayForPayWidget();
  window.Wayforpay = class extends Widget {
    run() {}
  };
  document
    .getElementById("widget-wfp-script")!
    .dispatchEvent(new Event("load"));
  await expect(retry).resolves.toBeUndefined();
});
