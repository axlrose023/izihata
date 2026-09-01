import { Headset } from "lucide-react";
import { useState } from "react";

import { LeadDialog } from "@/modules/leads/components/lead-dialog";

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
      <LeadDialog onClose={() => setOpen(false)} open={open} type="callback" />
    </>
  );
}
