import { lazy, Suspense } from "react";
import type { ComponentProps } from "react";
import { LoaderCircle } from "lucide-react";
import { Modal } from "@/shared/ui/modal";

const LeadDialog = lazy(() =>
  import("./lead-dialog").then((module) => ({ default: module.LeadDialog })),
);

export function LazyLeadDialog(props: ComponentProps<typeof LeadDialog>) {
  if (!props.open) return null;
  return (
    <Suspense
      fallback={
        <Modal open title="Завантажуємо форму" onClose={props.onClose}>
          <p role="status">
            <LoaderCircle className="spin" /> Завантажуємо…
          </p>
        </Modal>
      }
    >
      <LeadDialog {...props} />
    </Suspense>
  );
}
