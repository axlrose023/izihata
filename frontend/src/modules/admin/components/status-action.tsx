import { LoaderCircle } from "lucide-react";

import { getUserErrorMessage } from "@/shared/api/errors";

export function StatusAction<TStatus extends string>({
  ariaLabel,
  error,
  labels,
  onChange,
  options,
  pending,
}: {
  ariaLabel: string;
  error: unknown;
  labels: Record<TStatus, string>;
  onChange: (status: TStatus) => void;
  options: TStatus[];
  pending: boolean;
}) {
  if (!options.length) return <span>—</span>;

  return (
    <div className="status-action">
      <select
        aria-label={ariaLabel}
        defaultValue=""
        disabled={pending}
        onChange={(event) => {
          if (event.target.value) onChange(event.target.value as TStatus);
        }}
      >
        <option disabled value="">
          Змінити…
        </option>
        {options.map((status) => (
          <option key={status} value={status}>
            {labels[status]}
          </option>
        ))}
      </select>
      {pending ? <LoaderCircle className="spin" size={16} /> : null}
      {error ? (
        <small>{getUserErrorMessage(error, "Не вдалося змінити статус")}</small>
      ) : null}
    </div>
  );
}
