import { AdminReviewsView } from "@/modules/catalog/components/admin-reviews-view";
import { AdminPage } from "@/modules/admin/components/admin-page";

export function AdminReviewsPage() {
  return (
    <AdminPage
      eyebrow="Контент"
      title="Відгуки"
      description="Публікуйте перевірені відгуки або відхиляйте некоректні."
    >
      <AdminReviewsView />
    </AdminPage>
  );
}
