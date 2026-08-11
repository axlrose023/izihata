import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

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
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["admin", "orders"] }),
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

export function OrdersView() {
  const { request } = useAuth();
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["admin", "orders"],
    queryFn: () =>
      request<Paginated<OrderSummary>>("/admin/orders?page_size=100"),
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
    <div className="admin-table-wrap">
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
            <tr key={order.id}>
              <td>
                <strong>{order.number}</strong>
                <small>{formatDate(order.created_at)}</small>
              </td>
              <td>
                <span>{order.customer_name}</span>
                <small>{order.phone}</small>
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
          ))}
        </tbody>
      </table>
    </div>
  );
}
