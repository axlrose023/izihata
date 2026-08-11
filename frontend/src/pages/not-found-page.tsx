import { Link } from "react-router-dom";

import { useDocumentTitle } from "@/shared/lib/use-document-title";

export function NotFoundPage() {
  useDocumentTitle("Сторінку не знайдено");
  return (
    <div className="container empty-state">
      <div className="empty-state__icon" aria-hidden="true">
        404
      </div>
      <h1>Сторінку не знайдено</h1>
      <p>Перевірте адресу або поверніться до каталогу.</p>
      <Link className="button button--primary" to="/catalog">
        До каталогу
      </Link>
    </div>
  );
}
