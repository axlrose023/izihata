import { labels } from "@/shared/lib/status-labels";

export function StatusBadge({ status }: { status: string }) {
  return (
    <span className="status-badge" data-status={status}>
      <i aria-hidden="true" />
      {labels[status] ?? status}
    </span>
  );
}
