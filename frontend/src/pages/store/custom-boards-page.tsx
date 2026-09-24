import { CustomBoardForm } from "@/modules/custom-boards/components/custom-board-form";
import { useDocumentTitle } from "@/shared/lib/use-document-title";

export function CustomBoardsPage() {
  useDocumentTitle("Щити на замовлення");

  return <CustomBoardForm />;
}
