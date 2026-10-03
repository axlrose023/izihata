import { LeadsView } from "@/modules/admin/components/leads-view";
import { AdminPage } from "@/modules/admin/components/admin-page";

export function AdminLeadsPage() {
  return (
    <AdminPage
      eyebrow="Комунікація"
      title="Звернення"
      description="Дзвінки, швидкі покупки та гуртові запити."
    >
      <LeadsView />
    </AdminPage>
  );
}
