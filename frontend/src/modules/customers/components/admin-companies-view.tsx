import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useAuth } from "@/modules/auth/auth-provider";
import { getUserErrorMessage } from "@/shared/api/errors";
import { formatDate } from "@/shared/lib/format";
import type {
  AdminCompany,
  CompanyStatus,
  Paginated,
} from "@/shared/types/api";
import { ErrorNotice } from "@/shared/ui/error-notice";
import { StatusBadge } from "@/shared/ui/status-badge";

const labels: Record<CompanyStatus, string> = {
  pending: "Очікує",
  approved: "Підтвердити",
  rejected: "Відхилити",
};

function CompanyReview({ company }: { company: AdminCompany }) {
  const { request } = useAuth();
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: (status: "approved" | "rejected") =>
      request<AdminCompany>(`/admin/customers/companies/${company.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          status,
          manager_name: status === "approved" ? company.manager_name : null,
          cumulative_discount_rate:
            status === "approved" ? company.cumulative_discount_rate : "0",
        }),
      }),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["admin", "companies"] }),
  });
  if (company.status !== "pending") return <span>—</span>;
  return (
    <div className="status-action">
      <select
        aria-label={`Рішення для ${company.name}`}
        defaultValue=""
        disabled={mutation.isPending}
        onChange={(event) => {
          const value = event.target.value as "approved" | "rejected" | "";
          if (value) mutation.mutate(value);
        }}
      >
        <option disabled value="">
          Рішення…
        </option>
        <option value="approved">{labels.approved}</option>
        <option value="rejected">{labels.rejected}</option>
      </select>
      {mutation.isError ? (
        <small>
          {getUserErrorMessage(mutation.error, "Не вдалося оновити компанію")}
        </small>
      ) : null}
    </div>
  );
}

export function AdminCompaniesView() {
  const { request } = useAuth();
  const result = useQuery({
    queryKey: ["admin", "companies"],
    queryFn: () =>
      request<Paginated<AdminCompany>>(
        "/admin/customers/companies?page_size=100",
      ),
  });
  if (result.isPending)
    return <div className="admin-loader">Завантажуємо компанії…</div>;
  if (result.isError)
    return (
      <ErrorNotice
        className="admin-error"
        error={result.error}
        fallback="Не вдалося завантажити компанії."
        onRetry={() => void result.refetch()}
      />
    );
  return (
    <div className="admin-table-wrap">
      <table className="admin-table">
        <thead>
          <tr>
            <th>Компанія</th>
            <th>Контакт</th>
            <th>Статус</th>
            <th>Знижка</th>
            <th>Створено</th>
            <th>Дія</th>
          </tr>
        </thead>
        <tbody>
          {result.data.items.map((company) => (
            <tr key={company.id}>
              <td>
                <strong>{company.name}</strong>
                <small>
                  {company.kind === "fop" ? "ФОП" : "Юридична особа"} ·{" "}
                  {company.edrpou}
                </small>
              </td>
              <td>
                <span>{company.customer_name}</span>
                <small>{company.customer_email}</small>
              </td>
              <td>
                <StatusBadge status={company.status} />
              </td>
              <td>
                {(Number(company.cumulative_discount_rate) * 100).toFixed(0)}%
              </td>
              <td>{formatDate(company.created_at)}</td>
              <td>
                <CompanyReview company={company} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
