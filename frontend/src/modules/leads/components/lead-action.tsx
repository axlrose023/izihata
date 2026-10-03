import { useState } from "react";

import type { LeadType } from "@/shared/types/api";

import { LazyLeadDialog } from "./lazy-lead-dialog";
import { preloadLeadDialog } from "./load-lead-dialog";

export function LeadAction({
  type,
  label,
  productId,
  className = "button button--outline",
}: {
  type: LeadType;
  label: string;
  productId?: string;
  className?: string;
}) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button
        className={className}
        onClick={() => setOpen(true)}
        onFocus={preloadLeadDialog}
        onPointerEnter={preloadLeadDialog}
        onPointerDown={preloadLeadDialog}
        type="button"
      >
        {label}
      </button>
      <LazyLeadDialog
        onClose={() => setOpen(false)}
        open={open}
        productId={productId}
        type={type}
      />
    </>
  );
}
