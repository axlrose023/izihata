import { LoaderCircle, X } from "lucide-react";
import { useBodyScrollLock } from "@/shared/lib/use-body-scroll-lock";
import { useCloseOnEscape } from "@/shared/lib/use-close-on-escape";

export function OverlayLoadingState({
  label,
  onClose,
}: {
  label: string;
  onClose: () => void;
}) {
  useBodyScrollLock(true);
  useCloseOnEscape(true, onClose);
  return (
    <div
      aria-label={label}
      aria-modal="true"
      className="overlay-loading"
      role="dialog"
    >
      <div className="overlay-loading__panel">
        <button
          aria-label="Закрити"
          className="icon-button"
          onClick={onClose}
          type="button"
        >
          <X size={20} />
        </button>
        <p role="status">
          <LoaderCircle aria-hidden="true" className="spin" size={24} /> {label}
          …
        </p>
      </div>
    </div>
  );
}
