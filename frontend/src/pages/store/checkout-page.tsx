import { CheckoutForm } from "@/modules/checkout/components/checkout-form";
import { useDocumentTitle } from "@/shared/lib/use-document-title";

export function CheckoutPage() {
  useDocumentTitle("Оформлення замовлення");
  return (
    <div className="container checkout-page">
      <h1 className="sr-only">Оформлення замовлення</h1>
      <CheckoutForm />
    </div>
  );
}
