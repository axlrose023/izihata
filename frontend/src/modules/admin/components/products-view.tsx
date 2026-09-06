import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import {
  Check,
  Eye,
  EyeOff,
  LoaderCircle,
  Pencil,
  Plus,
  Search,
} from "lucide-react";
import { useState } from "react";

import { updateAdminProduct } from "@/modules/admin/api/admin-catalog";
import { ProductFormDialog } from "@/modules/admin/components/product-form-dialog";
import { useAuth } from "@/modules/auth/auth-provider";
import { buildQuery } from "@/shared/api/query";
import { getUserErrorMessage } from "@/shared/api/errors";
import { useDebouncedValue } from "@/shared/lib/use-debounced-value";
import type { AdminProduct, Paginated, StockStatus } from "@/shared/types/api";
import { ErrorNotice } from "@/shared/ui/error-notice";

function ProductRow({
  product,
  onEdit,
}: {
  product: AdminProduct;
  onEdit: (product: AdminProduct) => void;
}) {
  const { request } = useAuth();
  const queryClient = useQueryClient();
  const [price, setPrice] = useState(product.price);
  const [oldPrice, setOldPrice] = useState(product.old_price ?? "");
  const [stockStatus, setStockStatus] = useState<StockStatus>(
    product.stock_status,
  );
  const [message, setMessage] = useState<string | null>(null);
  const visibility = useMutation({
    mutationFn: (isActive: boolean) =>
      request(`/admin/catalog/products/${product.id}`, {
        method: "PATCH",
        body: JSON.stringify({ is_active: isActive }),
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["admin", "products"] });
    },
    onError: (error) =>
      setMessage(getUserErrorMessage(error, "Не вдалося змінити видимість")),
  });
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
    <tr data-hidden={product.is_active ? undefined : "true"}>
      <td>
        <strong>{product.name}</strong>
        {product.is_active ? null : (
          <span className="admin-hidden-flag">Прихований</span>
        )}
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
          <option value="in_stock_today">Відправимо сьогодні</option>
          <option value="preorder">Під замовлення</option>
          <option value="out_of_stock">Немає в наявності</option>
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
          <button
            aria-label={
              product.is_active
                ? `Прибрати з вітрини ${product.name}`
                : `Повернути на вітрину ${product.name}`
            }
            className="table-action__secondary"
            disabled={visibility.isPending}
            onClick={() => visibility.mutate(!product.is_active)}
            type="button"
          >
            {product.is_active ? <Eye size={16} /> : <EyeOff size={16} />}
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
  const [editingProduct, setEditingProduct] = useState<AdminProduct | null>(
    null,
  );
  const [onlyHidden, setOnlyHidden] = useState(false);
  const { request } = useAuth();
  const debouncedSearch = useDebouncedValue(search.trim(), 350);
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["admin", "products", debouncedSearch, onlyHidden],
    queryFn: () =>
      request<Paginated<AdminProduct>>(
        `/admin/catalog/products${buildQuery({
          page_size: 100,
          ...(debouncedSearch.length >= 2 ? { search: debouncedSearch } : {}),
          ...(onlyHidden ? { is_active: false } : {}),
        })}`,
      ),
    placeholderData: keepPreviousData,
  });
  const products = data?.items ?? [];

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
        <label className="admin-products-toolbar__filter">
          <input
            checked={onlyHidden}
            onChange={(event) => setOnlyHidden(event.target.checked)}
            type="checkbox"
          />
          Лише приховані
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
