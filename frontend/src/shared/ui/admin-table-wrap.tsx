import type { ReactNode } from "react";

/**
 * Admin tables scroll sideways on narrow screens. A scroll container that
 * nothing inside can hold focus is unreachable from the keyboard, so it is
 * exposed as a labelled region that takes focus itself.
 */
export function AdminTableWrap({
  children,
  label,
}: {
  children: ReactNode;
  label: string;
}) {
  return (
    <div
      aria-label={label}
      className="admin-table-wrap"
      role="region"
      tabIndex={0}
    >
      {children}
    </div>
  );
}
