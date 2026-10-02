import { usePageMeta } from "./use-page-meta";

export function useDocumentTitle(title?: string): void {
  usePageMeta({
    title: title ?? "Електротовари",
    description:
      "Каталог електротоварів IZI HATA: товари, характеристики, доставка й оформлення замовлень.",
  });
}
