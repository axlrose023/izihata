import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useAuth } from "@/modules/auth/auth-provider";
import { formatDate } from "@/shared/lib/format";
import type { AdminLead, LeadStatus, Paginated } from "@/shared/types/api";
import { ErrorNotice } from "@/shared/ui/error-notice";
import { StatusBadge } from "@/shared/ui/status-badge";

import { StatusAction } from "./status-action";

const transitions: Record<LeadStatus, LeadStatus[]> = {
  new: ["contacted", "closed"],
  contacted: ["closed"],
  closed: [],
};
const labels: Record<LeadStatus, string> = {
  new: "Новий",
  contacted: "Зв’язались",
  closed: "Закрити",
};
const typeLabels = {
  callback: "Дзвінок",
  quick_buy: "Швидка покупка",
  wholesale: "Гурт",
};

function LeadAction({ lead }: { lead: AdminLead }) {
  const { request } = useAuth();
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: (status: LeadStatus) =>
      request<AdminLead>(`/admin/leads/${lead.id}/status`, {
        method: "PATCH",
        body: JSON.stringify({ status }),
      }),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["admin", "leads"] }),
  });
  const options = transitions[lead.status];
  return (
    <StatusAction
      ariaLabel={`Статус звернення ${lead.name}`}
      error={mutation.error}
      labels={labels}
      onChange={(status) => mutation.mutate(status)}
      options={options}
      pending={mutation.isPending}
    />
  );
}

export function LeadsView() {
  const { request } = useAuth();
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["admin", "leads"],
    queryFn: () => request<Paginated<AdminLead>>("/admin/leads?page_size=100"),
  });
  if (isLoading)
    return <div className="admin-loader">Завантажуємо звернення…</div>;
  if (error)
    return (
      <ErrorNotice
        className="admin-error"
        error={error}
        fallback="Не вдалося завантажити звернення."
        onRetry={() => void refetch()}
      />
    );
  return (
    <div className="admin-table-wrap">
      <table className="admin-table">
        <thead>
          <tr>
            <th>Тип</th>
            <th>Контакт</th>
            <th>Компанія / товар</th>
            <th>Створено</th>
            <th>Статус</th>
            <th>Дія</th>
          </tr>
        </thead>
        <tbody>
          {data?.items.map((lead) => (
            <tr key={lead.id}>
              <td>{typeLabels[lead.type]}</td>
              <td>
                <strong>{lead.name}</strong>
                <small>{lead.phone}</small>
              </td>
              <td>
                <span>{lead.company ?? "—"}</span>
                <small>
                  {lead.product_id
                    ? `Товар: ${lead.product_id.slice(0, 8)}…`
                    : ""}
                </small>
              </td>
              <td>{formatDate(lead.created_at)}</td>
              <td>
                <StatusBadge status={lead.status} />
              </td>
              <td>
                <LeadAction lead={lead} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
