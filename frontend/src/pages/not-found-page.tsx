import { Link } from "react-router-dom";

import { useDocumentTitle } from "@/shared/lib/use-document-title";
import { usePageMeta } from "@/shared/lib/use-page-meta";

export function NotFoundPage() {
  useDocumentTitle("Сторінку не знайдено");
  usePageMeta({
    title: "Сторінку не знайдено",
    description: "Перевірте адресу або поверніться до каталогу IZI HATA.",
  });
  return (
    <div className="container empty-state">
      <div className="empty-state__icon" aria-hidden="true">
        404
      </div>
      <h1>Сторінку не знайдено</h1>
      <p>Перевірте адресу або поверніться до каталогу.</p>
      <Link className="button button--primary" to="/#catalog">
        До каталогу
      </Link>
    </div>
  );
}
