import { DashboardView } from "@/modules/admin/components/dashboard-view";
import { LeadsView } from "@/modules/admin/components/leads-view";
import { OrdersView } from "@/modules/admin/components/orders-view";
import { ProductsView } from "@/modules/admin/components/products-view";
import { AdminReviewsView } from "@/modules/catalog/components/admin-reviews-view";
import { AdminBoardRequestsView } from "@/modules/custom-boards/components/admin-board-requests-view";
import { AdminCompaniesView } from "@/modules/customers/components/admin-companies-view";
import { useDocumentTitle } from "@/shared/lib/use-document-title";

function PageHeader({
  eyebrow,
  title,
  description,
}: {
  eyebrow: string;
  title: string;
  description?: string;
}) {
  useDocumentTitle(title);
  return (
    <header className="admin-page__header">
      <div>
        <span className="eyebrow">{eyebrow}</span>
        <h1>{title}</h1>
      </div>
      {description ? <p>{description}</p> : null}
    </header>
  );
}

export function AdminDashboardPage() {
  return (
    <div className="admin-page">
      <PageHeader eyebrow="Стан магазину" title="Огляд" />
      <DashboardView />
    </div>
  );
}

export function AdminProductsPage() {
  return (
    <div className="admin-page">
      <PageHeader
        eyebrow="Каталог"
        title="Товари"
        description="Створення та редагування товарів, цін і доступності."
      />
      <ProductsView />
    </div>
  );
}

export function AdminOrdersPage() {
  return (
    <div className="admin-page">
      <PageHeader
        eyebrow="Продажі"
        title="Замовлення"
        description="Статуси змінюються лише за дозволеним backend-процесом."
      />
      <OrdersView />
    </div>
  );
}

export function AdminLeadsPage() {
  return (
    <div className="admin-page">
      <PageHeader
        eyebrow="Комунікація"
        title="Звернення"
        description="Дзвінки, швидкі покупки та гуртові запити."
      />
      <LeadsView />
    </div>
  );
}

export function AdminReviewsPage() {
  return (
    <div className="admin-page">
      <PageHeader
        eyebrow="Контент"
        title="Відгуки"
        description="Публікуйте перевірені відгуки або відхиляйте некоректні."
      />
      <AdminReviewsView />
    </div>
  );
}

export function AdminCompaniesPage() {
  return (
    <div className="admin-page">
      <PageHeader
        eyebrow="B2B"
        title="Компанії"
        description="Перевіряйте реквізити клієнтів перед доступом до гуртових умов."
      />
      <AdminCompaniesView />
    </div>
  );
}

export function AdminCustomBoardsPage() {
  return (
    <div className="admin-page">
      <PageHeader
        eyebrow="Індивідуальні проєкти"
        title="Щити на замовлення"
        description="Керуйте запитами на розрахунок та збирання щитів."
      />
      <AdminBoardRequestsView />
    </div>
  );
}
