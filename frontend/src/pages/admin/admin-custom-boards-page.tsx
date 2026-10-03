import { AdminBoardRequestsView } from "@/modules/custom-boards/components/admin-board-requests-view";
import { AdminPage } from "@/modules/admin/components/admin-page";

export function AdminCustomBoardsPage() {
  return (
    <AdminPage
      eyebrow="Індивідуальні проєкти"
      title="Щити на замовлення"
      description="Керуйте запитами на розрахунок та збирання щитів."
    >
      <AdminBoardRequestsView />
    </AdminPage>
  );
}
