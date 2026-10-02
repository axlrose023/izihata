import { Check, Truck, UserRound } from "lucide-react";
import { Link, useLocation, useSearchParams } from "react-router-dom";

import { formatMoney } from "@/shared/lib/format";
import { useDocumentTitle } from "@/shared/lib/use-document-title";

export function OrderSuccessPage() {
  useDocumentTitle("Замовлення прийняте");
  const [params] = useSearchParams();
  const accountOrder = useLocation().state?.accountOrder === true;
  const deliveryMethod = params.get("delivery");
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
      <div className="success-page__main">
        <section className="success-card">
          <span className="success-card__icon">
            <Check size={26} />
          </span>
          <div>
            <h1>Замовлення прийнято</h1>
            <p>
              Ми отримали замовлення. Менеджер зателефонує протягом робочого
              дня, щоб узгодити деталі та час відправлення.
            </p>
            {payment === "card" ? (
              <p className="inline-note">
                Спосіб оплати підтвердимо під час дзвінка.
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
              {accountOrder ? (
                <Link className="button button--dark" to="/account">
                  Переглянути замовлення в кабінеті
                </Link>
              ) : null}
              <Link className="button button--outline" to="/#catalog">
                Повернутися в каталог
              </Link>
            </div>
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
                  ? "Очікує підтвердження менеджером"
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
