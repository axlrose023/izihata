import { AdminCompaniesView } from "@/modules/customers/components/admin-companies-view";
import { AdminPage } from "@/modules/admin/components/admin-page";

export function AdminCompaniesPage() {
  return (
    <AdminPage
      eyebrow="B2B"
      title="Компанії"
      description="Перевіряйте реквізити клієнтів перед доступом до гуртових умов."
    >
      <AdminCompaniesView />
    </AdminPage>
  );
}
