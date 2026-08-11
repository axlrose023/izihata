import { X } from "lucide-react";
import { useEffect, useRef } from "react";

export function Modal({
  open,
  title,
  size = "default",
  onClose,
  children,
}: {
  open: boolean;
  title: string;
  size?: "default" | "wide";
  onClose: () => void;
  children: React.ReactNode;
}) {
  const dialogRef = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  if (!open) return null;

  return (
    <dialog
      aria-labelledby="modal-title"
      className={`modal${size === "wide" ? " modal--wide" : ""}`}
      onCancel={onClose}
      onClick={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
      ref={dialogRef}
    >
      <div className="modal__panel">
        <header className="modal__header">
          <h2 id="modal-title">{title}</h2>
          <button
            aria-label="Закрити"
            className="icon-button"
            onClick={onClose}
            type="button"
          >
            <X size={20} />
          </button>
        </header>
        {children}
      </div>
    </dialog>
  );
}
