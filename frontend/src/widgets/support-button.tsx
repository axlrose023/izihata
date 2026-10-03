import { Headset } from "lucide-react";
import { useState } from "react";

import { LazyLeadDialog } from "@/modules/leads/components/lazy-lead-dialog";
import {
  loadLeadDialog,
  preloadLeadDialog,
} from "@/modules/leads/components/load-lead-dialog";
import { useIdlePreload } from "@/shared/lib/use-idle-preload";

export function SupportButton() {
  useIdlePreload(loadLeadDialog);
  const [open, setOpen] = useState(false);

  return (
    <>
      <button
        aria-label="Замовити дзвінок"
        className="support-button"
        onClick={() => setOpen(true)}
        onFocus={preloadLeadDialog}
        onPointerEnter={preloadLeadDialog}
        onPointerDown={preloadLeadDialog}
        type="button"
      >
        <Headset size={21} />
        <span>Підтримка</span>
      </button>
      <LazyLeadDialog
        onClose={() => setOpen(false)}
        open={open}
        type="callback"
      />
    </>
  );
}
