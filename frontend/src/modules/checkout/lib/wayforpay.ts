interface WayForPayInstance {
  closeit(): void;
  invoice(url: string, straight: boolean): void;
}

declare global {
  interface Window {
    Wayforpay?: new () => WayForPayInstance;
  }
}

export type WayForPayResult = "approved" | "declined" | "pending" | "closed";

let scriptPromise: Promise<void> | null = null;

export function prepareWayForPayWidget(): Promise<void> {
  if (window.Wayforpay) return Promise.resolve();
  if (scriptPromise) return scriptPromise;

  scriptPromise = new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.id = "widget-wfp-script";
    script.src = "https://secure.wayforpay.com/server/pay-widget.js";
    script.async = true;
    const fail = () => {
      window.clearTimeout(timeout);
      script.remove();
      scriptPromise = null;
      reject(
        new Error("Не вдалося завантажити платіжне вікно. Спробуйте ще раз."),
      );
    };
    const timeout = window.setTimeout(fail, 15_000);
    script.onload = () => {
      window.clearTimeout(timeout);
      if (window.Wayforpay) resolve();
      else {
        scriptPromise = null;
        fail();
      }
    };
    script.onerror = fail;
    document.head.append(script);
  });
  return scriptPromise;
}

export async function openWayForPayInvoice(
  url: string,
): Promise<WayForPayResult> {
  const parsed = new URL(url);
  if (
    parsed.origin !== "https://secure.wayforpay.com" ||
    !parsed.pathname.startsWith("/invoice/")
  )
    throw new Error("Некоректне платіжне посилання.");
  await prepareWayForPayWidget();
  const WayForPay = window.Wayforpay;
  if (!WayForPay) throw new Error("WayForPay widget did not initialize");

  return new Promise((resolve, reject) => {
    const widget = new WayForPay();
    let settled = false;
    let observer: MutationObserver | undefined;
    const finish = (result: WayForPayResult) => {
      if (settled) return;
      settled = true;
      window.removeEventListener("message", onMessage);
      observer?.disconnect();
      widget.closeit();
      resolve(result);
    };
    const onMessage = (event: MessageEvent<unknown>) => {
      if (event.origin !== "https://secure.wayforpay.com") return;
      const events: Record<string, WayForPayResult> = {
        WfpWidgetEventClose: "closed",
        WfpWidgetEventApproved: "approved",
        WfpWidgetEventDeclined: "declined",
        WfpWidgetEventPending: "pending",
      };
      if (typeof event.data === "string" && events[event.data])
        finish(events[event.data]);
    };

    window.addEventListener("message", onMessage);
    try {
      widget.invoice(url, true);
      const container = document.getElementById("wfp-container");
      if (!settled && container) {
        observer = new MutationObserver(() => {
          if (!container.isConnected) finish("closed");
        });
        observer.observe(document.body, { childList: true, subtree: true });
      }
    } catch {
      window.removeEventListener("message", onMessage);
      widget.closeit();
      reject(
        new Error("Не вдалося відкрити платіжне вікно. Спробуйте ще раз."),
      );
    }
  });
}
