import { useQuery } from "@tanstack/react-query";
import { Check, Truck, UserRound } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  Link,
  useLocation,
  useNavigate,
  useSearchParams,
} from "react-router-dom";

import { paymentStatusQuery } from "@/modules/checkout/api/payment-api";
import { openWayForPayInvoice } from "@/modules/checkout/lib/wayforpay";
import { formatMoney } from "@/shared/lib/format";
import { useDocumentTitle } from "@/shared/lib/use-document-title";
import type { PaymentStatus } from "@/shared/types/api";

function paymentMessage(
  hasError: boolean,
  status: PaymentStatus | null,
  canResume: boolean,
): string {
  if (hasError)
    return "Не вдалося перевірити оплату. Замовлення збережено; оновіть сторінку або зв’яжіться з менеджером.";
  if (status === "paid")
    return "Оплату успішно отримано. Менеджер зв’яжеться з вами для узгодження доставки.";
  if (status === "refunded")
    return "Кошти за замовлення повернено. За деталями зверніться до менеджера.";
  if (status === "pending")
    return canResume
      ? "Оплату ще не підтверджено. Якщо ви закрили вікно, його можна відкрити знову."
      : "Оплату ще не підтверджено. Для повторної оплати зверніться до менеджера.";
  if (status === "failed")
    return canResume
      ? "Оплату не підтверджено. Ви можете повторити спробу або зв’язатися з менеджером."
      : "Оплату не підтверджено. Зверніться до менеджера щодо повторної оплати.";
  return "Спосіб оплати підтвердимо під час дзвінка.";
}

export function OrderSuccessPage() {
  useDocumentTitle("Замовлення прийняте");
  const [params] = useSearchParams();
  const location = useLocation();
  const navigate = useNavigate();
  const [isPaying, setIsPaying] = useState(false);
  const [paymentError, setPaymentError] = useState<string | null>(null);
  const openedAutomatically = useRef(false);
  const accountOrder = location.state?.accountOrder === true;
  const deliveryMethod = params.get("delivery");
  const rawNumber = params.get("number") ?? "";
  const rawTotal = params.get("total") ?? "";
  const rawPayment = params.get("payment") ?? "";
  const rawPaymentAttemptId = params.get("payment_attempt_id") ?? "";
  const number = /^IZI-\d{8}-[A-F0-9]{10}$/.test(rawNumber) ? rawNumber : null;
  const total =
    Number.isFinite(Number(rawTotal)) && Number(rawTotal) >= 0
      ? rawTotal
      : null;
  const payment = ["cash_on_delivery", "card", "invoice"].includes(rawPayment)
    ? rawPayment
    : null;
  const paymentAttemptId =
    /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(
      rawPaymentAttemptId,
    )
      ? rawPaymentAttemptId
      : null;
  const onlinePayment = useQuery({
    ...paymentStatusQuery(paymentAttemptId),
    enabled: payment === "card" && paymentAttemptId !== null,
    refetchInterval: (query) =>
      (!query.state.data || query.state.data.status === "pending") &&
      query.state.dataUpdateCount + query.state.errorUpdateCount < 80
        ? 1_500
        : false,
    refetchIntervalInBackground: false,
  });
  const paymentStatus = paymentAttemptId
    ? (onlinePayment.data?.status ?? "pending")
    : null;
  const invoiceUrl = onlinePayment.data?.invoice_url;
  const refetchPayment = onlinePayment.refetch;

  const resumePayment = useCallback(async () => {
    if (!invoiceUrl || isPaying) return;
    setIsPaying(true);
    setPaymentError(null);
    try {
      await openWayForPayInvoice(invoiceUrl);
      await refetchPayment();
    } catch {
      setPaymentError("Не вдалося відкрити платіжне вікно. Спробуйте ще раз.");
    } finally {
      setIsPaying(false);
    }
  }, [invoiceUrl, isPaying, refetchPayment]);

  useEffect(() => {
    if (
      location.state?.openPayment !== true ||
      openedAutomatically.current ||
      !onlinePayment.data?.invoice_url
    )
      return;
    openedAutomatically.current = true;
    navigate(`${location.pathname}${location.search}${location.hash}`, {
      replace: true,
      state: { accountOrder },
    });
    void resumePayment();
  }, [
    accountOrder,
    location,
    navigate,
    onlinePayment.data?.invoice_url,
    resumePayment,
  ]);

  return (
    <div className="container success-page">
      <div className="success-page__main">
        <section className="success-card">
          <span className="success-card__icon">
            <Check size={26} />
          </span>
          <div>
            <h1>Замовлення прийнято</h1>
            {onlinePayment.data?.is_test ? (
              <p className="inline-note" role="status">
                Тестова оплата WayForPay. Це не підтвердження справжньої
                покупки.
              </p>
            ) : null}
            <p>
              Ми отримали замовлення. Менеджер зателефонує протягом робочого
              дня, щоб узгодити деталі та час відправлення.
            </p>
            {payment === "card" ? (
              <p className="inline-note">
                {onlinePayment.isLoading
                  ? "Перевіряємо статус оплати…"
                  : paymentMessage(
                      onlinePayment.isError,
                      paymentStatus,
                      Boolean(invoiceUrl),
                    )}
              </p>
            ) : null}
            {payment === "invoice" ? (
              <p className="inline-note">
                Менеджер перевірить реквізити перед підготовкою рахунку.
              </p>
            ) : null}
            {!accountOrder ? (
              <p className="inline-note">
                Збережіть номер замовлення. Його стан і деталі повідомить
                менеджер; гостьове замовлення не додається до історії кабінету.
              </p>
            ) : null}
            <div className="success-page__actions">
              {payment === "card" && onlinePayment.data?.invoice_url ? (
                <button
                  className="button button--dark"
                  disabled={isPaying}
                  onClick={() => void resumePayment()}
                  type="button"
                >
                  {isPaying ? "Відкриваємо оплату…" : "Перейти до оплати"}
                </button>
              ) : null}
              {accountOrder ? (
                <Link className="button button--dark" to="/account">
                  Переглянути замовлення в кабінеті
                </Link>
              ) : null}
              <Link className="button button--outline" to="/#catalog">
                Повернутися в каталог
              </Link>
            </div>
            {paymentError ? <p role="alert">{paymentError}</p> : null}
          </div>
        </section>

        <section className="success-next-steps">
          <header>
            <strong>Що далі</strong>
            <span className="eyebrow">3 кроки</span>
          </header>
          <ol>
            <li>
              <span>1</span>
              <strong>Підтвердження менеджером</strong>
              <p>Уточнимо наявність і деталі замовлення.</p>
            </li>
            <li>
              <span>2</span>
              <strong>Комплектація й відправлення</strong>
              <p>Менеджер повідомить про стан відправлення.</p>
            </li>
            <li>
              <span>3</span>
              <strong>Отримання</strong>
              <p>Менеджер узгодить доступні для замовлення документи.</p>
            </li>
          </ol>
        </section>
      </div>

      <aside className="success-summary">
        <section>
          <span className="eyebrow">Номер замовлення</span>
          <strong>{number ?? "—"}</strong>
          <dl>
            <div>
              <dt>Товари</dt>
              <dd>{total ? formatMoney(total) : "—"}</dd>
            </div>
            <div>
              <dt>Доставка</dt>
              <dd>за тарифом</dd>
            </div>
            <div>
              <dt>{payment === "card" ? "Статус оплати" : "До сплати"}</dt>
              <dd>
                {payment === "card"
                  ? paymentStatus === "paid"
                    ? "Оплачено"
                    : paymentStatus === "refunded"
                      ? "Кошти повернено"
                      : paymentStatus === "pending"
                        ? "Очікує підтвердження WayForPay"
                        : paymentStatus === "failed"
                          ? "Не оплачено"
                          : "Очікує підтвердження менеджером"
                  : total
                    ? formatMoney(total)
                    : "—"}
              </dd>
            </div>
          </dl>
        </section>
        <section className="success-delivery">
          <strong>Доставка</strong>
          <p>
            <Truck size={17} />
            <span>
              <b>
                {deliveryMethod === "pickup"
                  ? "Самовивіз"
                  : deliveryMethod === "nova_poshta_locker"
                    ? "Поштомат Нової пошти"
                    : deliveryMethod === "nova_poshta_branch"
                      ? "Відділення Нової пошти"
                      : "Спосіб доставки"}
              </b>
              Деталі доставки підтвердить менеджер.
            </span>
          </p>
          <p>
            <UserRound size={17} />
            <span>
              <b>Контактні дані</b>
              Вказані під час оформлення.
            </span>
          </p>
        </section>
      </aside>
    </div>
  );
}
