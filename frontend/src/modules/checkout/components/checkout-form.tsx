import { zodResolver } from "@hookform/resolvers/zod";
import { useQuery } from "@tanstack/react-query";
import { Check, LoaderCircle, ShoppingBag } from "lucide-react";
import { useDeferredValue, useState } from "react";
import { useForm, useWatch } from "react-hook-form";
import { useNavigate } from "react-router-dom";
import { z } from "zod";

import { useCartStore } from "@/modules/cart/store";
import { apiClient } from "@/shared/api/client";
import { getUserErrorMessage } from "@/shared/api/errors";
import { formatMoney } from "@/shared/lib/format";
import type {
  DeliveryCityOption,
  DeliveryPointOption,
  Order,
  Quote,
} from "@/shared/types/api";
import { EmptyState } from "@/shared/ui/empty-state";

const deliveryOptions = [
  {
    value: "nova_poshta_branch",
    label: "Нова пошта",
    detail: "Відділення",
  },
  {
    value: "nova_poshta_locker",
    label: "Нова пошта",
    detail: "Поштомат",
  },
  { value: "pickup", label: "Самовивіз", detail: "За погодженням" },
] as const;

const checkoutSchema = z
  .object({
    customer_name: z.string().trim().min(2, "Вкажіть ім’я").max(120),
    phone: z
      .string()
      .trim()
      .regex(/^\+?[0-9 ()-]{10,20}$/, "Вкажіть коректний номер"),
    delivery_method: z.enum([
      "nova_poshta_branch",
      "nova_poshta_locker",
      "pickup",
    ]),
    city: z.string().trim().max(120),
    point: z.string().trim().max(200),
    payment_method: z.enum(["cash_on_delivery", "card", "invoice"]),
    company_name: z.string().trim().max(180),
    edrpou: z.string().trim(),
  })
  .superRefine((values, context) => {
    if (values.delivery_method !== "pickup") {
      if (values.city.length < 2) {
        context.addIssue({
          code: "custom",
          path: ["city"],
          message: "Вкажіть місто",
        });
      }
      if (!values.point) {
        context.addIssue({
          code: "custom",
          path: ["point"],
          message: "Вкажіть відділення",
        });
      }
    }
    if (values.payment_method === "invoice") {
      if (values.company_name.length < 2) {
        context.addIssue({
          code: "custom",
          path: ["company_name"],
          message: "Вкажіть компанію",
        });
      }
      if (!/^\d{8,10}$/.test(values.edrpou)) {
        context.addIssue({
          code: "custom",
          path: ["edrpou"],
          message: "ЄДРПОУ: 8–10 цифр",
        });
      }
    }
  });

type CheckoutValues = z.infer<typeof checkoutSchema>;

export function CheckoutForm() {
  const navigate = useNavigate();
  const lines = useCartStore((state) => state.lines);
  const clearCart = useCartStore((state) => state.clear);
  const [promoInput, setPromoInput] = useState("");
  const [promoCode, setPromoCode] = useState<string | null>(null);
  const [selectedCityRef, setSelectedCityRef] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [idempotency, setIdempotency] = useState<{
    fingerprint: string;
    key: string;
  } | null>(null);
  const {
    register,
    control,
    handleSubmit,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<CheckoutValues>({
    resolver: zodResolver(checkoutSchema),
    defaultValues: {
      customer_name: "",
      phone: "+380",
      delivery_method: "nova_poshta_branch",
      city: "",
      point: "",
      payment_method: "cash_on_delivery",
      company_name: "",
      edrpou: "",
    },
  });
  const deliveryMethod = useWatch({ control, name: "delivery_method" });
  const paymentMethod = useWatch({ control, name: "payment_method" });
  const city = useWatch({ control, name: "city" });
  const point = useWatch({ control, name: "point" });
  const deferredCity = useDeferredValue(city.trim());
  const deferredPoint = useDeferredValue(point.trim());
  const cityField = register("city");
  const pointField = register("point");
  const deliveryMethodField = register("delivery_method");
  const isNovaPoshta = deliveryMethod !== "pickup";
  const cities = useQuery({
    queryKey: ["delivery", "cities", deferredCity],
    enabled: isNovaPoshta && deferredCity.length >= 2,
    queryFn: () =>
      apiClient<DeliveryCityOption[]>(
        `/delivery/cities?${new URLSearchParams({ search: deferredCity })}`,
      ),
  });
  const pointKind =
    deliveryMethod === "nova_poshta_locker" ? "locker" : "branch";
  const points = useQuery({
    queryKey: ["delivery", "points", selectedCityRef, pointKind, deferredPoint],
    enabled: isNovaPoshta && selectedCityRef !== null,
    queryFn: () =>
      apiClient<DeliveryPointOption[]>(
        `/delivery/points?${new URLSearchParams({
          city_ref: selectedCityRef ?? "",
          kind: pointKind,
          ...(deferredPoint ? { search: deferredPoint } : {}),
        })}`,
      ),
  });
  const items = lines.map((line) => ({
    product_id: line.product.id,
    quantity: line.quantity,
  }));
  const quote = useQuery({
    queryKey: ["quote", items, promoCode],
    enabled: items.length > 0,
    queryFn: () =>
      apiClient<Quote>("/checkout/quote", {
        method: "POST",
        body: JSON.stringify({ items, promo_code: promoCode }),
      }),
  });

  if (!lines.length) {
    return (
      <EmptyState
        actionHref="/catalog"
        actionLabel="Перейти до каталогу"
        description="Спочатку додайте хоча б один товар."
        title="Немає що оформлювати"
      />
    );
  }

  const submit = handleSubmit(async (values) => {
    if (!quote.data) {
      setSubmitError("Дочекайтеся розрахунку замовлення");
      return;
    }
    const payload = {
      items,
      promo_code: promoCode,
      customer_name: values.customer_name,
      phone: values.phone,
      delivery: {
        method: values.delivery_method,
        city: values.delivery_method === "pickup" ? null : values.city,
        point: values.delivery_method === "pickup" ? null : values.point,
      },
      payment_method: values.payment_method,
      company:
        values.payment_method === "invoice"
          ? { name: values.company_name, edrpou: values.edrpou }
          : null,
    };
    const fingerprint = JSON.stringify(payload);
    const requestIdentity =
      idempotency?.fingerprint === fingerprint
        ? idempotency
        : { fingerprint, key: crypto.randomUUID() };
    if (requestIdentity !== idempotency) setIdempotency(requestIdentity);
    setSubmitError(null);
    try {
      const order = await apiClient<Order>("/orders", {
        method: "POST",
        headers: { "Idempotency-Key": requestIdentity.key },
        body: fingerprint,
      });
      clearCart();
      navigate(
        `/order/success?number=${encodeURIComponent(order.number)}&total=${encodeURIComponent(order.total)}&payment=${order.payment_method}`,
      );
    } catch (error) {
      setSubmitError(
        getUserErrorMessage(error, "Не вдалося створити замовлення"),
      );
    }
  });

  return (
    <div className="checkout-layout">
      <form className="checkout-form" onSubmit={submit}>
        <section className="checkout-card">
          <span className="checkout-step">01</span>
          <div>
            <h2>Контактні дані</h2>
            <div className="form-grid">
              <label className="field">
                <span>Ім’я та прізвище</span>
                <input autoComplete="name" {...register("customer_name")} />
                {errors.customer_name ? (
                  <small>{errors.customer_name.message}</small>
                ) : null}
              </label>
              <label className="field">
                <span>Телефон</span>
                <input
                  autoComplete="tel"
                  inputMode="tel"
                  {...register("phone")}
                />
                {errors.phone ? <small>{errors.phone.message}</small> : null}
              </label>
            </div>
          </div>
        </section>

        <section className="checkout-card">
          <span className="checkout-step">02</span>
          <div>
            <h2>Доставка</h2>
            <div className="choice-grid">
              {deliveryOptions.map((option) => (
                <label key={option.value}>
                  <input
                    type="radio"
                    value={option.value}
                    {...deliveryMethodField}
                    onChange={(event) => {
                      void deliveryMethodField.onChange(event);
                      setValue("point", "");
                    }}
                  />
                  <span>
                    {option.label}
                    <br />
                    <small>{option.detail}</small>
                  </span>
                </label>
              ))}
            </div>
            {deliveryMethod !== "pickup" ? (
              <div className="form-grid">
                <label className="field">
                  <span>Місто</span>
                  <input
                    {...cityField}
                    autoComplete="address-level2"
                    list="nova-poshta-cities"
                    onChange={(event) => {
                      void cityField.onChange(event);
                      const selected = cities.data?.find(
                        (option) =>
                          option.label === event.target.value ||
                          option.name === event.target.value,
                      );
                      setSelectedCityRef(selected?.ref ?? null);
                      setValue("point", "");
                    }}
                    placeholder="Почніть вводити населений пункт"
                  />
                  <datalist id="nova-poshta-cities">
                    {cities.data?.map((option) => (
                      <option key={option.ref} value={option.label} />
                    ))}
                  </datalist>
                  {errors.city ? <small>{errors.city.message}</small> : null}
                </label>
                <label className="field">
                  <span>
                    {deliveryMethod === "nova_poshta_locker"
                      ? "Поштомат"
                      : "Відділення"}
                  </span>
                  <input
                    {...pointField}
                    list="nova-poshta-points"
                    placeholder={
                      selectedCityRef
                        ? "Оберіть зі списку або уточніть пошук"
                        : city.trim().length >= 2
                          ? "Можна ввести вручну"
                          : "Спочатку вкажіть місто"
                    }
                  />
                  <datalist id="nova-poshta-points">
                    {points.data?.map((option) => (
                      <option
                        key={option.ref}
                        label={option.label}
                        value={option.name}
                      />
                    ))}
                  </datalist>
                  {errors.point ? <small>{errors.point.message}</small> : null}
                </label>
              </div>
            ) : (
              <p className="inline-note">
                Менеджер підтвердить адресу і час самовивозу.
              </p>
            )}
            {cities.error || points.error ? (
              <p className="delivery-fallback-note" role="status">
                {getUserErrorMessage(
                  cities.error ?? points.error,
                  "Не вдалося завантажити підказки. Введіть адресу вручну.",
                )}
              </p>
            ) : null}
          </div>
        </section>

        <section className="checkout-card">
          <span className="checkout-step">03</span>
          <div>
            <h2>Оплата</h2>
            <div className="choice-grid">
              <label>
                <input
                  type="radio"
                  value="cash_on_delivery"
                  {...register("payment_method")}
                />
                <span>При отриманні</span>
              </label>
              <label>
                <input
                  type="radio"
                  value="card"
                  {...register("payment_method")}
                />
                <span>
                  Карткою
                  <br />
                  <small>Після підтвердження</small>
                </span>
              </label>
              <label>
                <input
                  type="radio"
                  value="invoice"
                  {...register("payment_method")}
                />
                <span>Рахунок для ТОВ/ФОП</span>
              </label>
            </div>
            {paymentMethod === "invoice" ? (
              <div className="form-grid">
                <label className="field">
                  <span>Назва компанії</span>
                  <input
                    autoComplete="organization"
                    {...register("company_name")}
                  />
                  {errors.company_name ? (
                    <small>{errors.company_name.message}</small>
                  ) : null}
                </label>
                <label className="field">
                  <span>ЄДРПОУ</span>
                  <input inputMode="numeric" {...register("edrpou")} />
                  {errors.edrpou ? (
                    <small>{errors.edrpou.message}</small>
                  ) : null}
                </label>
              </div>
            ) : null}
          </div>
        </section>
        {submitError ? (
          <p className="form-error" role="alert">
            {submitError}
          </p>
        ) : null}
        <button
          className="button button--primary button--wide checkout-submit"
          disabled={isSubmitting || quote.isLoading || !quote.data}
          type="submit"
        >
          {isSubmitting ? (
            <LoaderCircle className="spin" size={19} />
          ) : (
            <Check size={19} />
          )}
          {isSubmitting ? "Створюємо замовлення…" : "Підтвердити замовлення"}
        </button>
      </form>

      <aside className="order-summary">
        <div className="order-summary__title">
          <ShoppingBag size={20} />
          <h2>Ваше замовлення</h2>
        </div>
        <div className="order-summary__items">
          {lines.map((line) => (
            <div key={line.product.id}>
              <span>
                {line.product.name}
                <small>{line.quantity} шт.</small>
              </span>
              <strong>
                {formatMoney(Number(line.product.price) * line.quantity)}
              </strong>
            </div>
          ))}
        </div>
        <div className="promo-form">
          <input
            aria-label="Промокод"
            onChange={(event) => setPromoInput(event.target.value)}
            placeholder="Промокод"
            value={promoInput}
          />
          <button
            onClick={() =>
              setPromoCode(promoInput.trim().toUpperCase() || null)
            }
            type="button"
          >
            Застосувати
          </button>
        </div>
        {quote.error ? (
          <p className="form-error" role="alert">
            {getUserErrorMessage(quote.error, "Помилка розрахунку")}
          </p>
        ) : null}
        {quote.data?.promotion ? (
          <p className="promo-success" role="status">
            Промокод {quote.data.promotion.code} застосовано
          </p>
        ) : null}
        {quote.isLoading ? (
          <p className="order-summary__loading">
            <LoaderCircle className="spin" /> Розраховуємо…
          </p>
        ) : quote.data ? (
          <div className="order-totals">
            <span>
              Товари <b>{formatMoney(quote.data.subtotal)}</b>
            </span>
            {Number(quote.data.discount) > 0 ? (
              <span>
                Знижка <b>−{formatMoney(quote.data.discount)}</b>
              </span>
            ) : null}
            <strong>
              Разом <b>{formatMoney(quote.data.total)}</b>
            </strong>
          </div>
        ) : null}
      </aside>
    </div>
  );
}
