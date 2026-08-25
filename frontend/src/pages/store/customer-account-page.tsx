import { useQueries } from "@tanstack/react-query";
import { Building2, LogOut, ReceiptText, UserRound } from "lucide-react";
import { useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";

import {
  customerOrdersQuery,
  customerProfileQuery,
} from "@/modules/customers/api/customer-queries";
import { CustomerCompanyForm } from "@/modules/customers/components/customer-company-form";
import { useCustomerAuth } from "@/modules/customers/customer-auth-context";
import { formatDate, formatMoney } from "@/shared/lib/format";
import { useDocumentTitle } from "@/shared/lib/use-document-title";
import { ErrorNotice } from "@/shared/ui/error-notice";
import { StatusBadge } from "@/shared/ui/status-badge";

export function CustomerAccountPage() {
  const { logout, restore, status } = useCustomerAuth();
  const navigate = useNavigate();
  const [profileResult, ordersResult] = useQueries({
    queries: [
      { ...customerProfileQuery(), enabled: status === "authenticated" },
      { ...customerOrdersQuery(), enabled: status === "authenticated" },
    ],
  });
  useDocumentTitle("Особистий кабінет");

  useEffect(() => {
    void restore();
  }, [restore]);

  if (status === "idle" || status === "loading") {
    return <div className="page-loader">Відкриваємо кабінет…</div>;
  }
  if (status === "unavailable") {
    return (
      <ErrorNotice
        className="container service-notice"
        error={null}
        fallback="Не вдалося перевірити сесію. Спробуйте ще раз."
        onRetry={() => void restore()}
      />
    );
  }
  if (status === "guest") {
    return (
      <div className="container customer-account-page customer-account-page--guest">
        <span className="eyebrow">Особистий кабінет</span>
        <h1>Керуйте замовленнями та бізнес-умовами</h1>
        <p>Увійдіть або створіть акаунт, щоб бачити історію замовлень.</p>
        <div>
          <Link className="button button--primary" to="/account/login">
            Увійти
          </Link>
          <Link
            className="button button--outline"
            to="/account/login?mode=register"
          >
            Створити акаунт
          </Link>
        </div>
      </div>
    );
  }
  if (profileResult.isPending || ordersResult.isPending) {
    return <div className="page-loader">Завантажуємо дані кабінету…</div>;
  }
  if (
    profileResult.isError ||
    ordersResult.isError ||
    !profileResult.data ||
    !ordersResult.data
  ) {
    return (
      <ErrorNotice
        className="container service-notice"
        error={profileResult.error ?? ordersResult.error}
        fallback="Не вдалося завантажити кабінет."
        onRetry={() => {
          void profileResult.refetch();
          void ordersResult.refetch();
        }}
      />
    );
  }

  const profile = profileResult.data;
  const company = profile.company;
  const signOut = async () => {
    await logout();
    navigate("/", { replace: true });
  };

  return (
    <div className="container customer-account-page">
      <header className="customer-account-page__header">
        <div>
          <span className="eyebrow">Особистий кабінет</span>
          <h1>{profile.full_name}</h1>
          <p>
            {profile.email}
            {profile.phone ? ` · ${profile.phone}` : ""}
          </p>
        </div>
        <button
          className="button button--outline"
          onClick={() => void signOut()}
          type="button"
        >
          <LogOut size={17} /> Вийти
        </button>
      </header>
      <div className="customer-account-grid">
        <section className="customer-account-card">
          <UserRound aria-hidden="true" />
          <h2>Роздрібний та бізнес-режим</h2>
          <p>
            Роздрібні ціни доступні завжди. Гуртові автоматично застосовуються
            до кошика після схвалення компанії.
          </p>
          {company ? (
            <div className="customer-company-status">
              <div>
                <strong>{company.name}</strong>
                <span>
                  {company.kind === "fop" ? "ФОП" : "Юридична особа"} ·{" "}
                  {company.edrpou}
                </span>
              </div>
              <StatusBadge status={company.status} />
              {company.status === "approved" ? (
                <p>
                  Накопичувальна знижка:{" "}
                  {(Number(company.cumulative_discount_rate) * 100).toFixed(0)}%
                  {company.manager_name
                    ? ` · менеджер: ${company.manager_name}`
                    : ""}
                </p>
              ) : (
                <p>Менеджер перевіряє реквізити. Повідомимо про результат.</p>
              )}
            </div>
          ) : (
            <CustomerCompanyForm />
          )}
        </section>
        <section className="customer-account-card">
          <Building2 aria-hidden="true" />
          <h2>Умови для бізнесу</h2>
          <ul>
            <li>Гуртові ціни доступні після підтвердження компанії.</li>
            <li>Фінальна ціна завжди перераховується сервером у кошику.</li>
            <li>Для рахунку оберіть оплату за безготівковим розрахунком.</li>
          </ul>
        </section>
      </div>
      <section className="customer-orders">
        <div className="section-heading">
          <div>
            <span className="eyebrow">Історія покупок</span>
            <h2>Замовлення</h2>
          </div>
        </div>
        {ordersResult.data.items.length ? (
          <div className="customer-orders__list">
            {ordersResult.data.items.map((order) => (
              <article key={order.id}>
                <ReceiptText aria-hidden="true" />
                <div>
                  <strong>{order.number}</strong>
                  <span>{formatDate(order.created_at)}</span>
                </div>
                <StatusBadge status={order.status} />
                <strong>{formatMoney(order.total)}</strong>
              </article>
            ))}
          </div>
        ) : (
          <p className="customer-orders__empty">
            Тут з’являться ваші оформлені замовлення.
          </p>
        )}
      </section>
    </div>
  );
}
