import { useQuery } from "@tanstack/react-query";
import {
  Banknote,
  ClipboardList,
  PackageCheck,
  PhoneCall,
  ReceiptText,
} from "lucide-react";

import { useAuth } from "@/modules/auth/auth-provider";
import { formatMoney } from "@/shared/lib/format";
import type { Dashboard } from "@/shared/types/api";
import { ErrorNotice } from "@/shared/ui/error-notice";

export function DashboardView() {
  const { request } = useAuth();
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["admin", "dashboard"],
    queryFn: () => request<Dashboard>("/admin/dashboard"),
  });

  if (isLoading)
    return <div className="admin-loader">Завантажуємо показники…</div>;
  if (error || !data)
    return (
      <ErrorNotice
        className="admin-error"
        error={error}
        fallback="Не вдалося отримати показники."
        onRetry={() => void refetch()}
      />
    );

  const cards = [
    {
      label: "Виторг за 7 днів",
      value: formatMoney(data.revenue_last_7_days),
      icon: Banknote,
    },
    {
      label: "Замовлень сьогодні",
      value: data.orders_today,
      icon: ClipboardList,
    },
    {
      label: "Середній чек",
      value: formatMoney(data.average_order_total),
      icon: ReceiptText,
    },
    {
      label: "Активних товарів",
      value: data.active_products,
      icon: PackageCheck,
    },
    { label: "Нових звернень", value: data.new_leads, icon: PhoneCall },
  ];
  return (
    <div className="metric-grid">
      {cards.map(({ label, value, icon: Icon }) => (
        <article className="metric-card" key={label}>
          <Icon size={22} />
          <span>{label}</span>
          <strong>{value}</strong>
        </article>
      ))}
    </div>
  );
}
