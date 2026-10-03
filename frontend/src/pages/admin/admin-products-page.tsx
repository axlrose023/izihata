import { ProductsView } from "@/modules/admin/components/products-view";
import { AdminPage } from "@/modules/admin/components/admin-page";

export function AdminProductsPage() {
  return (
    <AdminPage
      eyebrow="Каталог"
      title="Товари"
      description="Створення та редагування товарів, цін і доступності."
    >
      <ProductsView />
    </AdminPage>
  );
}
