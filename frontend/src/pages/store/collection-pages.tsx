import { CollectionPage } from "@/modules/collections/components/collection-page";
import { useDocumentTitle } from "@/shared/lib/use-document-title";

export function FavoritesPage() {
  useDocumentTitle("Обране");
  return (
    <div className="container collection-page">
      <span className="eyebrow">Ваш список</span>
      <h1>Обране</h1>
      <CollectionPage mode="favorites" />
    </div>
  );
}

export function ComparePage() {
  useDocumentTitle("Порівняння");
  return (
    <div className="container collection-page">
      <span className="eyebrow">Характеристики поруч</span>
      <h1>Порівняння</h1>
      <CollectionPage mode="compare" />
    </div>
  );
}
