import type { WayForPayWidgetSession } from "@/shared/types/api";

interface WayForPayInstance {
  closeit(): void;
  run(
    parameters: WayForPayWidgetSession,
    onApproved: (response: unknown) => void,
    onDeclined: (response: unknown) => void,
    onPending: (response: unknown) => void,
  ): void;
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

export async function openWayForPayWidget(
  parameters: WayForPayWidgetSession,
): Promise<WayForPayResult> {
  await prepareWayForPayWidget();
  const WayForPay = window.Wayforpay;
  if (!WayForPay) throw new Error("WayForPay widget did not initialize");

  return new Promise((resolve, reject) => {
    const widget = new WayForPay();
    let settled = false;
    const finish = (result: WayForPayResult) => {
      if (settled) return;
      settled = true;
      window.removeEventListener("message", onMessage);
      widget.closeit();
      resolve(result);
    };
    const onMessage = (event: MessageEvent<unknown>) => {
      if (
        event.origin === "https://secure.wayforpay.com" &&
        event.data === "WfpWidgetEventClose"
      )
        finish("closed");
    };

    window.addEventListener("message", onMessage);
    try {
      widget.run(
        parameters,
        () => finish("approved"),
        () => finish("declined"),
        () => finish("pending"),
      );
    } catch {
      window.removeEventListener("message", onMessage);
      widget.closeit();
      reject(
        new Error("Не вдалося відкрити платіжне вікно. Спробуйте ще раз."),
      );
    }
  });
}
