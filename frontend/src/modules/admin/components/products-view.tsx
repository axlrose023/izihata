import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, LoaderCircle, Pencil, Plus, Search } from "lucide-react";
import { useMemo, useState } from "react";

import { updateAdminProduct } from "@/modules/admin/api/admin-catalog";
import { ProductFormDialog } from "@/modules/admin/components/product-form-dialog";
import { useAuth } from "@/modules/auth/auth-provider";
import { apiClient } from "@/shared/api/client";
import { getUserErrorMessage } from "@/shared/api/errors";
import type { Product, ProductList, StockStatus } from "@/shared/types/api";
import { ErrorNotice } from "@/shared/ui/error-notice";

function ProductRow({
  product,
  onEdit,
}: {
  product: Product;
  onEdit: (product: Product) => void;
}) {
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
      updateAdminProduct(request, product.id, {
        price,
        old_price: oldPrice || null,
        stock_status: stockStatus,
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
        <div className="table-action__buttons">
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
          <button
            aria-label={`Редагувати ${product.name}`}
            className="table-action__secondary"
            onClick={() => onEdit(product)}
            type="button"
          >
            <Pencil size={16} />
          </button>
        </div>
        {message ? <small role="status">{message}</small> : null}
      </td>
    </tr>
  );
}

export function ProductsView() {
  const [search, setSearch] = useState("");
  const [formOpen, setFormOpen] = useState(false);
  const [editingProduct, setEditingProduct] = useState<Product | null>(null);
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

  return (
    <>
      <div className="admin-products-toolbar">
        <label className="admin-search">
          <Search size={18} />
          <input
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Назва, бренд або SKU"
            value={search}
          />
        </label>
        <button
          className="button button--primary"
          onClick={() => {
            setEditingProduct(null);
            setFormOpen(true);
          }}
          type="button"
        >
          <Plus size={17} /> Додати товар
        </button>
      </div>
      {isLoading ? (
        <div className="admin-loader">Завантажуємо товари…</div>
      ) : error ? (
        <ErrorNotice
          className="admin-error"
          error={error}
          fallback="Не вдалося завантажити каталог."
          onRetry={() => void refetch()}
        />
      ) : (
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
                <ProductRow
                  key={product.id}
                  onEdit={(selected) => {
                    setEditingProduct(selected);
                    setFormOpen(true);
                  }}
                  product={product}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}
      <ProductFormDialog
        onClose={() => setFormOpen(false)}
        open={formOpen}
        product={editingProduct}
      />
    </>
  );
}
