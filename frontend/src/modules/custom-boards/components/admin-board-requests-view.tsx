import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useAuth } from "@/modules/auth/auth-provider";
import { getUserErrorMessage } from "@/shared/api/errors";
import { formatDate, formatMoney } from "@/shared/lib/format";
import type {
  AdminCustomBoardRequest,
  BoardRequestStatus,
  Paginated,
} from "@/shared/types/api";
import { ErrorNotice } from "@/shared/ui/error-notice";
import { StatusBadge } from "@/shared/ui/status-badge";

const statuses: Array<{ value: BoardRequestStatus; label: string }> = [
  { value: "in_review", label: "Взяти в роботу" },
  { value: "quoted", label: "Надіслати кошторис" },
  { value: "closed", label: "Закрити" },
  { value: "cancelled", label: "Скасувати" },
];

function BoardStatusAction({
  requestItem,
}: {
  requestItem: AdminCustomBoardRequest;
}) {
  const { request } = useAuth();
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: (status: BoardRequestStatus) =>
      request<void>(`/admin/custom-boards/requests/${requestItem.id}`, {
        method: "PATCH",
        body: JSON.stringify({ status }),
      }),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["admin", "board-requests"] }),
  });
  return (
    <div className="status-action">
      <select
        aria-label={`Статус запиту ${requestItem.customer_name}`}
        defaultValue=""
        disabled={mutation.isPending}
        onChange={(event) => {
          const value = event.target.value as BoardRequestStatus | "";
          if (value) mutation.mutate(value);
        }}
      >
        <option disabled value="">
          Змінити…
        </option>
        {statuses
          .filter((item) => item.value !== requestItem.status)
          .map((item) => (
            <option key={item.value} value={item.value}>
              {item.label}
            </option>
          ))}
      </select>
      {mutation.isError ? (
        <small>
          {getUserErrorMessage(mutation.error, "Не вдалося змінити статус")}
        </small>
      ) : null}
    </div>
  );
}

export function AdminBoardRequestsView() {
  const { request } = useAuth();
  const result = useQuery({
    queryKey: ["admin", "board-requests"],
    queryFn: () =>
      request<Paginated<AdminCustomBoardRequest>>(
        "/admin/custom-boards/requests?page_size=100",
      ),
  });
  if (result.isPending)
    return <div className="admin-loader">Завантажуємо запити…</div>;
  if (result.isError)
    return (
      <ErrorNotice
        className="admin-error"
        error={result.error}
        fallback="Не вдалося завантажити запити."
        onRetry={() => void result.refetch()}
      />
    );
  return (
    <div className="admin-table-wrap">
      <table className="admin-table">
        <thead>
          <tr>
            <th>Клієнт</th>
            <th>Щит</th>
            <th>Оцінка</th>
            <th>Створено</th>
            <th>Статус</th>
            <th>Дія</th>
          </tr>
        </thead>
        <tbody>
          {result.data.items.map((item) => (
            <tr key={item.id}>
              <td>
                <strong>{item.customer_name}</strong>
                <small>
                  {item.phone}
                  {item.email ? ` · ${item.email}` : ""}
                </small>
              </td>
              <td>
                <span>
                  {item.application} · {item.groups_count} груп ·{" "}
                  {item.ip_class}
                </span>
                <small>{item.automation_brand ?? "Бренд не вказано"}</small>
              </td>
              <td>{formatMoney(item.estimated_from_price)}</td>
              <td>{formatDate(item.created_at)}</td>
              <td>
                <StatusBadge status={item.status} />
              </td>
              <td>
                <BoardStatusAction requestItem={item} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
