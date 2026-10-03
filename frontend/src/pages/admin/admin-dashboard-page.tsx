import { DashboardView } from "@/modules/admin/components/dashboard-view";
import { AdminPage } from "@/modules/admin/components/admin-page";

export function AdminDashboardPage() {
  return (
    <AdminPage eyebrow="Стан магазину" title="Огляд">
      <DashboardView />
    </AdminPage>
  );
}
