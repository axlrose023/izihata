import { CustomerAuthForm } from "@/modules/customers/components/customer-auth-form";
import { useDocumentTitle } from "@/shared/lib/use-document-title";

export function CustomerAuthPage() {
  useDocumentTitle("Особистий кабінет");
  return (
    <div className="container customer-auth-page">
      <CustomerAuthForm />
    </div>
  );
}
