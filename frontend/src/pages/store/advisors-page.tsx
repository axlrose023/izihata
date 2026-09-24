import { LoadAdvisor } from "@/modules/advisors/components/load-advisor";
import { useDocumentTitle } from "@/shared/lib/use-document-title";

export function AdvisorsPage() {
  useDocumentTitle("Калькулятори та підбір");
  return (
    <div className="container advisors-page">
      <LoadAdvisor />
    </div>
  );
}
