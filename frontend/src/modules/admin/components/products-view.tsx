import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, LoaderCircle, Search } from "lucide-react";
import { useMemo, useState } from "react";

import { useAuth } from "@/modules/auth/auth-provider";
import { apiClient } from "@/shared/api/client";
import { getUserErrorMessage } from "@/shared/api/errors";
import type { Product, ProductList, StockStatus } from "@/shared/types/api";
import { ErrorNotice } from "@/shared/ui/error-notice";

function ProductRow({ product }: { product: Product }) {
  const { request } = useAuth();
  const queryClient = useQueryClient();
  const [price, setPrice] = useState(product.price);
  const [oldPrice, setOldPrice] = useState(product.old_price ?? "");
  const [stockStatus, setStockStatus] = useState<StockStatus>(
    product.stock_status,
  );
  const [message, setMessage] = useState<string | null>(null);
  const update = useMutation({
    mutationFn: () =>
      request<Product>(`/admin/catalog/products/${product.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          price,
          old_price: oldPrice || null,
          stock_status: stockStatus,
        }),
      }),
    onSuccess: async () => {
      setMessage("Збережено");
      await queryClient.invalidateQueries({ queryKey: ["admin", "products"] });
    },
    onError: (error) => {
      setMessage(getUserErrorMessage(error, "Не вдалося зберегти"));
    },
  });

  return (
    <tr>
      <td>
        <strong>{product.name}</strong>
        <small>
          {product.brand} · {product.sku}
        </small>
      </td>
      <td>
        <input
          aria-label={`Ціна ${product.name}`}
          min="0.01"
          onChange={(event) => setPrice(event.target.value)}
          step="0.01"
          type="number"
          value={price}
        />
      </td>
      <td>
        <input
          aria-label={`Стара ціна ${product.name}`}
          min="0.01"
          onChange={(event) => setOldPrice(event.target.value)}
          placeholder="—"
          step="0.01"
          type="number"
          value={oldPrice}
        />
      </td>
      <td>
        <select
          aria-label={`Наявність ${product.name}`}
          onChange={(event) =>
            setStockStatus(event.target.value as StockStatus)
          }
          value={stockStatus}
        >
          <option value="in_stock">В наявності</option>
          <option value="preorder">Під замовлення</option>
        </select>
      </td>
      <td className="table-action">
        <button
          aria-label={`Зберегти ${product.name}`}
          disabled={update.isPending}
          onClick={() => update.mutate()}
          type="button"
        >
          {update.isPending ? (
            <LoaderCircle className="spin" size={17} />
          ) : (
            <Check size={17} />
          )}
        </button>
        {message ? <small role="status">{message}</small> : null}
      </td>
    </tr>
  );
}

export function ProductsView() {
  const [search, setSearch] = useState("");
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["admin", "products"],
    queryFn: () =>
      apiClient<ProductList>("/catalog/products?page_size=100&sort=newest"),
  });
  const products = useMemo(() => {
    const normalized = search.trim().toLocaleLowerCase("uk");
    if (!normalized) return data?.items ?? [];
    return (data?.items ?? []).filter((product) =>
      `${product.name} ${product.brand} ${product.sku}`
        .toLocaleLowerCase("uk")
        .includes(normalized),
    );
  }, [data, search]);

  if (isLoading)
    return <div className="admin-loader">Завантажуємо товари…</div>;
  if (error)
    return (
      <ErrorNotice
        className="admin-error"
        error={error}
        fallback="Не вдалося завантажити каталог."
        onRetry={() => void refetch()}
      />
    );

  return (
    <>
      <label className="admin-search">
        <Search size={18} />
        <input
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Назва, бренд або SKU"
          value={search}
        />
      </label>
      <div className="admin-table-wrap">
        <table className="admin-table">
          <thead>
            <tr>
              <th>Товар</th>
              <th>Ціна</th>
              <th>Стара ціна</th>
              <th>Наявність</th>
              <th>Дія</th>
            </tr>
          </thead>
          <tbody>
            {products.map((product) => (
              <ProductRow key={product.id} product={product} />
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
