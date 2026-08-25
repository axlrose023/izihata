import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useAuth } from "@/modules/auth/auth-provider";
import { getUserErrorMessage } from "@/shared/api/errors";
import { formatDate } from "@/shared/lib/format";
import type {
  AdminProductReview,
  Paginated,
  ReviewStatus,
} from "@/shared/types/api";
import { ErrorNotice } from "@/shared/ui/error-notice";
import { StatusBadge } from "@/shared/ui/status-badge";

function ModerateReview({ review }: { review: AdminProductReview }) {
  const { request } = useAuth();
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: (status: Exclude<ReviewStatus, "pending">) =>
      request<void>(`/admin/catalog/reviews/${review.id}`, {
        method: "PATCH",
        body: JSON.stringify({ status, is_featured: status === "published" }),
      }),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["admin", "reviews"] }),
  });
  return (
    <div className="status-action">
      <select
        aria-label={`Модерація відгуку ${review.author}`}
        defaultValue=""
        disabled={mutation.isPending}
        onChange={(event) => {
          const value = event.target.value as
            Exclude<ReviewStatus, "pending"> | "";
          if (value) mutation.mutate(value);
        }}
      >
        <option disabled value="">
          Змінити…
        </option>
        <option value="published">Опублікувати</option>
        <option value="rejected">Відхилити</option>
      </select>
      {mutation.isError ? (
        <small>
          {getUserErrorMessage(mutation.error, "Не вдалося змінити відгук")}
        </small>
      ) : null}
    </div>
  );
}

export function AdminReviewsView() {
  const { request } = useAuth();
  const result = useQuery({
    queryKey: ["admin", "reviews"],
    queryFn: () =>
      request<Paginated<AdminProductReview>>(
        "/admin/catalog/reviews?page_size=100",
      ),
  });
  if (result.isPending)
    return <div className="admin-loader">Завантажуємо відгуки…</div>;
  if (result.isError)
    return (
      <ErrorNotice
        className="admin-error"
        error={result.error}
        fallback="Не вдалося завантажити відгуки."
        onRetry={() => void result.refetch()}
      />
    );
  return (
    <div className="admin-table-wrap">
      <table className="admin-table">
        <thead>
          <tr>
            <th>Товар і автор</th>
            <th>Відгук</th>
            <th>Створено</th>
            <th>Статус</th>
            <th>Дія</th>
          </tr>
        </thead>
        <tbody>
          {result.data.items.map((review) => (
            <tr key={review.id}>
              <td>
                <strong>{review.product_name}</strong>
                <small>
                  {review.author} · {review.email ?? "без email"} ·{" "}
                  {review.rating}/5
                </small>
              </td>
              <td>{review.text}</td>
              <td>{formatDate(review.created_at)}</td>
              <td>
                <StatusBadge status={review.status} />
              </td>
              <td>
                <ModerateReview review={review} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
