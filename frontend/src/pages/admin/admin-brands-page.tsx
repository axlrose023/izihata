import { AdminBrandsView } from "@/modules/catalog/components/admin-brands-view";
import { AdminPage } from "@/modules/admin/components/admin-page";

export function AdminBrandsPage() {
  return (
    <AdminPage
      eyebrow="Каталог"
      title="Бренди"
      description="Логотипи та порядок виробників у каталозі й на головній сторінці."
    >
      <AdminBrandsView />
    </AdminPage>
  );
}
