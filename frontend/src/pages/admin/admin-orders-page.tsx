import { OrdersView } from "@/modules/admin/components/orders-view";
import { AdminPage } from "@/modules/admin/components/admin-page";

export function AdminOrdersPage() {
  return (
    <AdminPage
      eyebrow="Продажі"
      title="Замовлення"
      description="Статуси змінюються лише за дозволеним backend-процесом."
    >
      <OrdersView />
    </AdminPage>
  );
}
