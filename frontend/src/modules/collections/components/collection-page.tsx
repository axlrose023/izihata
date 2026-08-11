import { useQuery } from "@tanstack/react-query";
import { X } from "lucide-react";

import { ProductCard } from "@/modules/catalog/components/product-card";
import { apiClient } from "@/shared/api/client";
import { buildQuery } from "@/shared/api/query";
import { formatMoney } from "@/shared/lib/format";
import type { ProductList } from "@/shared/types/api";
import { EmptyState } from "@/shared/ui/empty-state";
import { ErrorNotice } from "@/shared/ui/error-notice";

import { useCollectionStore } from "../store";

export function CollectionPage({ mode }: { mode: "favorites" | "compare" }) {
  const ids = useCollectionStore((state) => state[mode]);
  const toggle = useCollectionStore((state) =>
    mode === "favorites" ? state.toggleFavorite : state.toggleCompare,
  );
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["collection", mode, ids],
    enabled: ids.length > 0,
    queryFn: () =>
      apiClient<ProductList>(
        `/catalog/products${buildQuery({ id: ids, page_size: 100 })}`,
      ),
  });
  const products = data?.items ?? [];

  if (!ids.length) {
    return (
      <EmptyState
        actionHref="/catalog"
        actionLabel="Перейти до каталогу"
        description={
          mode === "favorites"
            ? "Позначайте серцем товари, до яких хочете повернутися."
            : "Додайте до чотирьох товарів, щоб зіставити характеристики."
        }
        title={
          mode === "favorites"
            ? "Обране порожнє"
            : "Немає товарів для порівняння"
        }
      />
    );
  }
  if (isLoading) return <div className="page-loader">Завантажуємо товари…</div>;
  if (error)
    return (
      <ErrorNotice
        error={error}
        fallback="Не вдалося завантажити товари."
        onRetry={() => void refetch()}
      />
    );

  if (mode === "favorites") {
    return (
      <div className="product-grid product-grid--catalog">
        {products.map((product) => (
          <ProductCard key={product.id} product={product} />
        ))}
      </div>
    );
  }

  if (products.length < 2) {
    return (
      <EmptyState
        actionHref="/catalog"
        actionLabel="Додати ще товар"
        description="Для змістовного порівняння потрібні щонайменше два товари."
        title="Додайте ще один товар"
      />
    );
  }

  const specNames = [
    ...new Set(products.flatMap((product) => Object.keys(product.specs))),
  ];
  return (
    <div className="compare-scroll">
      <table className="compare-table">
        <thead>
          <tr>
            <th>Параметр</th>
            {products.map((product) => (
              <th key={product.id}>
                <button
                  aria-label={`Прибрати ${product.name}`}
                  className="compare-table__remove"
                  onClick={() => toggle(product.id)}
                  type="button"
                >
                  <X size={16} />
                </button>
                <strong>{product.name}</strong>
                <span>{formatMoney(product.price)}</span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          <tr>
            <th>Бренд</th>
            {products.map((product) => (
              <td key={product.id}>{product.brand}</td>
            ))}
          </tr>
          {specNames.map((spec) => (
            <tr key={spec}>
              <th>{spec}</th>
              {products.map((product) => (
                <td key={product.id}>{product.specs[spec] ?? "—"}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
