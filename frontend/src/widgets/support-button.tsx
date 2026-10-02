import { Headset } from "lucide-react";
import { useState } from "react";

import { LazyLeadDialog } from "@/modules/leads/components/lazy-lead-dialog";

export function SupportButton() {
  const [open, setOpen] = useState(false);

  return (
    <>
      <button
        aria-label="Замовити дзвінок"
        className="support-button"
        onClick={() => setOpen(true)}
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
