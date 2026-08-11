import { RefreshCw } from "lucide-react";

import { getUserErrorMessage } from "@/shared/api/errors";

export function ErrorNotice({
  error,
  fallback,
  onRetry,
  className = "service-notice",
}: {
  error: unknown;
  fallback: string;
  onRetry?: () => void;
  className?: string;
}) {
  return (
    <div className={`${className} error-notice`} role="alert">
      <span>{getUserErrorMessage(error, fallback)}</span>
      {onRetry ? (
        <button onClick={onRetry} type="button">
          <RefreshCw size={15} /> Повторити
        </button>
      ) : null}
    </div>
  );
}
