import { afterEach, expect, it, vi } from "vitest";

import { openWayForPayInvoice, prepareWayForPayWidget } from "./wayforpay";

class Widget {
  closeit() {}
  invoice() {}
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
      invoice() {
        window.dispatchEvent(
          new MessageEvent("message", {
            origin: "https://secure.wayforpay.com",
            data: `WfpWidgetEvent${result[0].toUpperCase()}${result.slice(1)}`,
          }),
        );
      }
    };
    await expect(
      openWayForPayInvoice("https://secure.wayforpay.com/invoice/test"),
    ).resolves.toBe(result);
    expect(close).toHaveBeenCalledOnce();
  },
);

it("accepts close events only from WayForPay and removes the listener", async () => {
  window.Wayforpay = class extends Widget {
    invoice() {}
  };
  const remove = vi.spyOn(window, "removeEventListener");
  const result = openWayForPayInvoice(
    "https://secure.wayforpay.com/invoice/test",
  );
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
    invoice() {
      throw new Error("broken");
    }
  };
  const remove = vi.spyOn(window, "removeEventListener");
  await expect(
    openWayForPayInvoice("https://secure.wayforpay.com/invoice/test"),
  ).rejects.toThrow(/платіжне вікно/);
  expect(remove).toHaveBeenCalledWith("message", expect.any(Function));
});

it("detects a provider-removed invoice window and allows another opening", async () => {
  const invoice = vi.fn(() => {
    const container = document.createElement("div");
    container.id = "wfp-container";
    document.body.append(container);
  });
  window.Wayforpay = class extends Widget {
    invoice = invoice;
  };
  const first = openWayForPayInvoice(
    "https://secure.wayforpay.com/invoice/test",
  );
  await Promise.resolve();
  document.getElementById("wfp-container")!.remove();
  await expect(first).resolves.toBe("closed");
  const second = openWayForPayInvoice(
    "https://secure.wayforpay.com/invoice/test",
  );
  await Promise.resolve();
  document.getElementById("wfp-container")!.remove();
  await expect(second).resolves.toBe("closed");
  expect(invoice).toHaveBeenCalledTimes(2);
});

it("rejects an invoice hosted outside WayForPay", async () => {
  await expect(
    openWayForPayInvoice("https://attacker.invalid/invoice/test"),
  ).rejects.toThrow(/платіжне посилання/);
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
    invoice() {}
  };
  document
    .getElementById("widget-wfp-script")!
    .dispatchEvent(new Event("load"));
  await expect(retry).resolves.toBeUndefined();
});
