import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { useAuth } from "@/modules/auth/auth-provider";
import { formatDate, formatMoney } from "@/shared/lib/format";
import type {
  Order,
  OrderStatus,
  OrderSummary,
  Paginated,
} from "@/shared/types/api";
import { ErrorNotice } from "@/shared/ui/error-notice";
import { StatusBadge } from "@/shared/ui/status-badge";

import { StatusAction } from "./status-action";
import { AdminPagination } from "@/shared/ui/admin-pagination";
import { AdminTableWrap } from "@/shared/ui/admin-table-wrap";

const transitions: Record<OrderStatus, OrderStatus[]> = {
  new: ["processing", "cancelled"],
  processing: ["confirmed", "cancelled"],
  confirmed: ["shipped", "cancelled"],
  shipped: ["delivered"],
  delivered: [],
  cancelled: [],
};

const labels: Record<OrderStatus, string> = {
  new: "Новий",
  processing: "В роботі",
  confirmed: "Підтверджено",
  shipped: "Відправлено",
  delivered: "Доставлено",
  cancelled: "Скасовано",
};

function OrderAction({ order }: { order: OrderSummary }) {
  const { request } = useAuth();
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: (status: OrderStatus) =>
      request<Order>(`/admin/orders/${order.id}/status`, {
        method: "PATCH",
        body: JSON.stringify({ status }),
      }),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["admin", "orders"] }),
        queryClient.invalidateQueries({
          queryKey: ["admin", "order", order.id],
        }),
      ]);
    },
  });
  const options = transitions[order.status];
  return (
    <StatusAction
      ariaLabel={`Статус замовлення ${order.number}`}
      error={mutation.error}
      labels={labels}
      onChange={(status) => mutation.mutate(status)}
      options={options}
      pending={mutation.isPending}
    />
  );
}

function OrderRow({ order }: { order: OrderSummary }) {
  const { request } = useAuth();
  const [expanded, setExpanded] = useState(false);
  const detail = useQuery({
    queryKey: ["admin", "order", order.id],
    enabled: expanded,
    queryFn: () => request<Order>(`/admin/orders/${order.id}`),
  });
  return (
    <>
      <tr>
        <td>
          <button
            aria-expanded={expanded}
            onClick={() => setExpanded((value) => !value)}
            type="button"
          >
            <strong>{order.number}</strong>
          </button>
          <small>{formatDate(order.created_at)}</small>
        </td>
        <td>
          <span>{order.customer_name}</span>
          <small>{order.phone}</small>
          {order.email ? <small>{order.email}</small> : null}
        </td>
        <td>
          <span>
            {order.delivery.method === "pickup"
              ? "Самовивіз"
              : order.delivery.city}
          </span>
          <small>{order.delivery.point ?? "За погодженням"}</small>
        </td>
        <td>
          <strong>{formatMoney(order.total)}</strong>
          <small>
            <StatusBadge status={order.payment_status} />
          </small>
        </td>
        <td>
          <StatusBadge status={order.status} />
        </td>
        <td>
          <OrderAction order={order} />
        </td>
      </tr>
      {expanded ? (
        <tr>
          <td colSpan={6}>
            {detail.isPending ? (
              <span>Завантажуємо склад замовлення…</span>
            ) : null}
            {detail.isError ? (
              <ErrorNotice
                error={detail.error}
                fallback="Не вдалося завантажити склад замовлення."
                onRetry={() => void detail.refetch()}
              />
            ) : null}
            {detail.data ? (
              <ul className="admin-order-items">
                {detail.data.items.map((item) => (
                  <li key={`${item.product_id}:${item.sku}`}>
                    <span>
                      {item.product_name} · {item.sku}
                    </span>
                    <span>
                      {item.quantity} × {formatMoney(item.unit_price)}
                    </span>
                    <strong>{formatMoney(item.total)}</strong>
                  </li>
                ))}
              </ul>
            ) : null}
          </td>
        </tr>
      ) : null}
    </>
  );
}

export function OrdersView() {
  const { request } = useAuth();
  const [page, setPage] = useState(1);
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["admin", "orders", page],
    queryFn: () =>
      request<Paginated<OrderSummary>>(
        `/admin/orders?page=${page}&page_size=100`,
      ),
  });
  if (isLoading)
    return <div className="admin-loader">Завантажуємо замовлення…</div>;
  if (error)
    return (
      <ErrorNotice
        className="admin-error"
        error={error}
        fallback="Не вдалося завантажити замовлення."
        onRetry={() => void refetch()}
      />
    );
  return (
    <>
      <AdminTableWrap label="Замовлення">
        <table className="admin-table">
          <thead>
            <tr>
              <th>Замовлення</th>
              <th>Клієнт</th>
              <th>Доставка</th>
              <th>Сума</th>
              <th>Статус</th>
              <th>Дія</th>
            </tr>
          </thead>
          <tbody>
            {data?.items.map((order) => (
              <OrderRow key={order.id} order={order} />
            ))}
          </tbody>
        </table>
      </AdminTableWrap>
      {data ? (
        <AdminPagination
          hasNext={data.has_next}
          hasPrev={data.has_prev}
          onPageChange={setPage}
          page={data.page}
          totalPages={data.total_pages}
        />
      ) : null}
    </>
  );
}
