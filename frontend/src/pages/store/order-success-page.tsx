import { CheckCircle2 } from "lucide-react";
import { Link, useSearchParams } from "react-router-dom";

import { formatMoney } from "@/shared/lib/format";
import { useDocumentTitle } from "@/shared/lib/use-document-title";

export function OrderSuccessPage() {
  useDocumentTitle("Замовлення прийняте");
  const [params] = useSearchParams();
  const rawNumber = params.get("number") ?? "";
  const rawTotal = params.get("total") ?? "";
  const rawPayment = params.get("payment") ?? "";
  const number = /^IZI-\d{8}-[A-F0-9]{10}$/.test(rawNumber) ? rawNumber : null;
  const total =
    Number.isFinite(Number(rawTotal)) && Number(rawTotal) >= 0
      ? rawTotal
      : null;
  const payment = ["cash_on_delivery", "card", "invoice"].includes(rawPayment)
    ? rawPayment
    : null;

  return (
    <div className="container success-page">
      <CheckCircle2 size={64} />
      <span className="eyebrow">Замовлення прийняте</span>
      <h1>Дякуємо за замовлення!</h1>
      {number ? (
        <p>
          Номер замовлення: <strong>{number}</strong>
        </p>
      ) : null}
      {total ? (
        <p>
          Сума: <strong>{formatMoney(total)}</strong>
        </p>
      ) : null}
      {payment === "card" ? (
        <p className="inline-note">
          Менеджер уточнить спосіб оплати після підтвердження.
        </p>
      ) : null}
      {payment === "invoice" ? (
        <p className="inline-note">
          Менеджер перевірить реквізити перед підготовкою рахунку.
        </p>
      ) : null}
      <p>Менеджер перевірить деталі та зв’яжеться з вами.</p>
      <div className="success-page__actions">
        <Link className="button button--primary" to="/catalog">
          Продовжити покупки
        </Link>
        <Link className="button button--outline" to="/">
          На головну
        </Link>
      </div>
    </div>
  );
}
