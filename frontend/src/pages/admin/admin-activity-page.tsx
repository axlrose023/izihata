import { AdminActivityView } from "@/modules/activity/components/admin-activity-view";
import { AdminPage } from "@/modules/admin/components/admin-page";

export function AdminActivityPage() {
  return (
    <AdminPage
      eyebrow="Відвідувачі"
      title="Активність"
      description="Хто заходив на сайт, коли востаннє й за яким номером можна передзвонити."
    >
      <AdminActivityView />
    </AdminPage>
  );
}
