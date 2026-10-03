import type { ReactNode } from "react";
import { useDocumentTitle } from "@/shared/lib/use-document-title";

export function AdminPage({
  eyebrow,
  title,
  description,
  children,
}: {
  eyebrow: string;
  title: string;
  description?: string;
  children: ReactNode;
}) {
  useDocumentTitle(title);
  return (
    <div className="admin-page">
      <header className="admin-page__header">
        <div>
          <span className="eyebrow">{eyebrow}</span>
          <h1>{title}</h1>
        </div>
        {description ? <p>{description}</p> : null}
      </header>
      {children}
    </div>
  );
}
