import { useState } from "react";

import type { LeadType } from "@/shared/types/api";

import { LazyLeadDialog } from "./lazy-lead-dialog";

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
      <button className={className} onClick={() => setOpen(true)} type="button">
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
