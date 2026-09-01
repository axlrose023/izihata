import { useQuery } from "@tanstack/react-query";
import { Phone, Search } from "lucide-react";
import { useState } from "react";

import { useAuth } from "@/modules/auth/auth-provider";
import { buildQuery } from "@/shared/api/query";
import { useDebouncedValue } from "@/shared/lib/use-debounced-value";
import type { Paginated, SiteVisitor } from "@/shared/types/api";
import { ErrorNotice } from "@/shared/ui/error-notice";

function relativeTime(iso: string): string {
  const minutes = Math.max(
    0,
    Math.round((Date.now() - new Date(iso).getTime()) / 60_000),
  );
  if (minutes < 1) return "щойно";
  if (minutes < 60) return `${minutes} хв тому`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} год тому`;
  const days = Math.round(hours / 24);
  return days === 1 ? "вчора" : `${days} дн тому`;
}

export function AdminActivityView() {
  const { request } = useAuth();
  const [search, setSearch] = useState("");
  const [withContacts, setWithContacts] = useState(false);
  const [page, setPage] = useState(1);
  const debouncedSearch = useDebouncedValue(search.trim(), 350);
  const result = useQuery({
    queryKey: ["admin", "visitors", debouncedSearch, withContacts, page],
    queryFn: () =>
      request<Paginated<SiteVisitor>>(
        `/admin/activity/visitors${buildQuery({
          page,
          page_size: 50,
          ...(debouncedSearch.length >= 2 ? { search: debouncedSearch } : {}),
          ...(withContacts ? { with_contacts: true } : {}),
        })}`,
      ),
    refetchInterval: 60_000,
  });

  return (
    <div className="admin-activity">
      <div className="admin-activity__filters">
        <label className="admin-activity__search">
          <Search size={16} />
          <input
            aria-label="Пошук за телефоном або іменем"
            onChange={(event) => {
              setSearch(event.target.value);
              setPage(1);
            }}
            placeholder="Телефон або ім’я"
            value={search}
          />
        </label>
        <label className="admin-activity__toggle">
          <input
            checked={withContacts}
            onChange={(event) => {
              setWithContacts(event.target.checked);
              setPage(1);
            }}
            type="checkbox"
          />
          Лише з контактами
        </label>
      </div>

      {result.isPending ? (
        <div className="admin-loader">Завантажуємо активність…</div>
      ) : result.isError ? (
        <ErrorNotice
          className="admin-error"
          error={result.error}
          fallback="Не вдалося завантажити активність."
          onRetry={() => void result.refetch()}
        />
      ) : (
        <>
          <div className="admin-table-wrap">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>Відвідувач</th>
                  <th>Контакт</th>
                  <th>Був на сайті</th>
                  <th>Сторінок</th>
                  <th>Замовлень</th>
                  <th>Звернень</th>
                  <th>Остання сторінка</th>
                </tr>
              </thead>
              <tbody>
                {result.data.items.map((visitor) => (
                  <tr key={visitor.id}>
                    <td>
                      <strong>{visitor.name ?? "Гість"}</strong>
                      <small>
                        {visitor.is_registered
                          ? "Зареєстрований"
                          : "Без акаунта"}
                      </small>
                    </td>
                    <td>
                      {visitor.phone ? (
                        <a
                          className="admin-activity__call"
                          href={`tel:${visitor.phone}`}
                        >
                          <Phone size={14} /> {visitor.phone}
                        </a>
                      ) : (
                        <small>Не залишав</small>
                      )}
                    </td>
                    <td>
                      <span>{relativeTime(visitor.last_seen_at)}</span>
                      <small>
                        Вперше: {relativeTime(visitor.first_seen_at)}
                      </small>
                    </td>
                    <td>{visitor.page_views}</td>
                    <td>{visitor.orders_count}</td>
                    <td>{visitor.leads_count}</td>
                    <td>
                      <small>{visitor.last_path ?? "—"}</small>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {result.data.items.length === 0 ? (
            <p className="admin-activity__empty">
              Поки немає відвідувачів за цими умовами.
            </p>
          ) : null}
          {result.data.total_pages > 1 ? (
            <div className="pagination">
              <button
                disabled={!result.data.has_prev}
                onClick={() => setPage((value) => value - 1)}
                type="button"
              >
                ← Назад
              </button>
              <span>
                {result.data.page} / {result.data.total_pages}
              </span>
              <button
                disabled={!result.data.has_next}
                onClick={() => setPage((value) => value + 1)}
                type="button"
              >
                Далі →
              </button>
            </div>
          ) : null}
        </>
      )}
    </div>
  );
}
