import { zodResolver } from "@hookform/resolvers/zod";
import { useQuery } from "@tanstack/react-query";
import { Check, LoaderCircle, ShoppingBag } from "lucide-react";
import { useEffect, useState } from "react";
import { Controller, useForm, useWatch } from "react-hook-form";
import { useNavigate } from "react-router-dom";
import { z } from "zod";

import { MAX_CART_LINES, useCartStore } from "@/modules/cart/store";
import { ProductVisual } from "@/modules/catalog/components/product-visual";
import { DeliveryAutocomplete } from "@/modules/checkout/components/delivery-autocomplete";
import { useCustomerAuth } from "@/modules/customers/customer-auth-context";
import { apiClient } from "@/shared/api/client";
import {
  clearOrderRetry,
  orderRetryKey,
} from "@/modules/checkout/lib/order-retry";
import { ApiError, getUserErrorMessage } from "@/shared/api/errors";
import { useDebouncedValue } from "@/shared/lib/use-debounced-value";
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

const checkoutSchema = (requireEmail: boolean) =>
  z
    .object({
      customer_name: z.string().trim().min(2, "Вкажіть ім’я").max(120),
      email: z.string().trim().max(254),
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
      if (requireEmail && !z.email().safeParse(values.email).success) {
        context.addIssue({
          code: "custom",
          path: ["email"],
          message: values.email ? "Вкажіть коректний email" : "Вкажіть email",
        });
      }
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

type CheckoutValues = z.infer<ReturnType<typeof checkoutSchema>>;

export function CheckoutForm() {
  const navigate = useNavigate();
  const {
    status: customerStatus,
    sessionVersion,
    restore,
    request: customerRequest,
  } = useCustomerAuth();
  const lines = useCartStore((state) => state.lines);
  const clearCart = useCartStore((state) => state.clear);
  const [promoInput, setPromoInput] = useState("");
  const [promoCode, setPromoCode] = useState<string | null>(null);
  const [selectedCityRef, setSelectedCityRef] = useState<string | null>(null);
  const [selectedPointRef, setSelectedPointRef] = useState<string | null>(null);
  const [manualDelivery, setManualDelivery] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [sessionNotice, setSessionNotice] = useState<string | null>(null);
  const sessionReady =
    customerStatus === "guest" || customerStatus === "authenticated";

  useEffect(() => {
    if (customerStatus === "idle") void restore();
  }, [customerStatus, restore]);

  const {
    register,
    control,
    handleSubmit,
    setError,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<CheckoutValues>({
    resolver: zodResolver(checkoutSchema(customerStatus !== "authenticated")),
    defaultValues: {
      customer_name: "",
      email: "",
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
  const deferredCity = useDebouncedValue(city.trim(), 300);
  const deferredPoint = useDebouncedValue(point.trim(), 300);
  const isNovaPoshta = deliveryMethod !== "pickup";
  const cities = useQuery({
    queryKey: ["delivery", "cities", deferredCity],
    enabled:
      isNovaPoshta &&
      !manualDelivery &&
      selectedCityRef === null &&
      deferredCity.length >= 2,
    queryFn: ({ signal }) =>
      apiClient<DeliveryCityOption[]>(
        `/delivery/cities?${new URLSearchParams({ search: deferredCity })}`,
        { signal },
      ),
  });
  const pointKind =
    deliveryMethod === "nova_poshta_locker" ? "locker" : "branch";
  const points = useQuery({
    queryKey: ["delivery", "points", selectedCityRef, pointKind, deferredPoint],
    enabled:
      isNovaPoshta &&
      !manualDelivery &&
      selectedCityRef !== null &&
      selectedPointRef === null,
    queryFn: ({ signal }) =>
      apiClient<DeliveryPointOption[]>(
        `/delivery/points?${new URLSearchParams({
          city_ref: selectedCityRef ?? "",
          kind: pointKind,
          ...(deferredPoint ? { search: deferredPoint } : {}),
        })}`,
        { signal },
      ),
  });
  const canEnterManually = manualDelivery || cities.isError || points.isError;
  const tooManyItems = lines.length > MAX_CART_LINES;
  const items = lines.map((line) => ({
    product_id: line.product.id,
    quantity: line.quantity,
  }));
  // Quantity edits happen in bursts; only the settled basket is re-quoted.
  const serializedItems = JSON.stringify(items);
  const quotedItems = useDebouncedValue(serializedItems, 350);
  const quoteIsStale = serializedItems !== quotedItems;
  const quote = useQuery({
    queryKey: ["quote", sessionVersion, customerStatus, quotedItems, promoCode],
    enabled: items.length > 0 && !tooManyItems && sessionReady,
    queryFn: async ({ signal }) => {
      const send =
        customerStatus === "authenticated" ? customerRequest : apiClient;
      try {
        return await send<Quote>("/checkout/quote", {
          method: "POST",
          signal,
          body: JSON.stringify({
            items: JSON.parse(quotedItems) as typeof items,
            promo_code: promoCode,
          }),
        });
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) {
          setSessionNotice(
            "Сесія завершилася. Увійдіть повторно або оформіть замовлення як гість.",
          );
        }
        throw error;
      }
    },
  });

  if (!lines.length) {
    return (
      <EmptyState
        actionHref="/#catalog"
        actionLabel="Перейти до каталогу"
        description="Спочатку додайте хоча б один товар."
        title="Немає що оформлювати"
      />
    );
  }

  const submit = handleSubmit(async (values) => {
    if (
      values.delivery_method !== "pickup" &&
      !canEnterManually &&
      !selectedCityRef
    ) {
      setError("city", { message: "Оберіть місто зі списку" });
      return;
    }
    if (
      values.delivery_method !== "pickup" &&
      !canEnterManually &&
      !selectedPointRef
    ) {
      setError("point", { message: "Оберіть відділення зі списку" });
      return;
    }
    if (
      !sessionReady ||
      !quote.data ||
      quoteIsStale ||
      quote.isFetching ||
      quote.isError
    ) {
      setSubmitError("Дочекайтеся розрахунку замовлення");
      return;
    }
    const payload = {
      items,
      promo_code: promoCode,
      customer_name: values.customer_name,
      email: customerStatus === "authenticated" ? undefined : values.email,
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
    setSubmitError(null);
    try {
      const retryKey = await orderRetryKey(
        JSON.stringify({
          ...payload,
          authenticated: customerStatus === "authenticated",
        }),
      );
      const send =
        customerStatus === "authenticated" ? customerRequest : apiClient;
      const order = await send<Order>("/orders", {
        method: "POST",
        headers: { "Idempotency-Key": retryKey },
        body: JSON.stringify({ ...payload, expected_total: quote.data.total }),
      });
      clearOrderRetry();
      clearCart();
      navigate(
        `/order/success?number=${encodeURIComponent(order.number)}&total=${encodeURIComponent(order.total)}&payment=${order.payment_method}&delivery=${order.delivery.method}`,
        { state: { accountOrder: customerStatus === "authenticated" } },
      );
    } catch (error) {
      if (error instanceof ApiError && error.code === "quote_changed")
        await quote.refetch();
      if (error instanceof ApiError && error.code === "idempotency_conflict")
        clearOrderRetry();
      setSubmitError(
        getUserErrorMessage(error, "Не вдалося створити замовлення"),
      );
    }
  });

  return (
    <div className="checkout-layout">
      <form className="checkout-form" id="checkout-form" onSubmit={submit}>
        {sessionNotice ? <p role="alert">{sessionNotice}</p> : null}
        {customerStatus === "unavailable" ? (
          <p role="alert">
            Не вдалося перевірити сесію. Повторіть перевірку, щоб зберегти умови
            вашого акаунта.
            <button type="button" onClick={() => void restore()}>
              Перевірити сесію
            </button>
          </p>
        ) : null}
        <section className="checkout-card checkout-card--contacts">
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
              {customerStatus !== "authenticated" ? (
                <label className="field checkout-email-field">
                  <span>Email</span>
                  <input
                    autoComplete="email"
                    inputMode="email"
                    required
                    type="email"
                    {...register("email")}
                  />
                  {errors.email ? <small>{errors.email.message}</small> : null}
                </label>
              ) : null}
            </div>
          </div>
        </section>

        <section className="checkout-card checkout-card--delivery">
          <span className="checkout-step">02</span>
          <div>
            <h2>Доставка</h2>
            <div className="choice-grid">
              {deliveryOptions.map((option) => (
                <label key={option.value}>
                  <input
                    type="radio"
                    value={option.value}
                    onChange={(event) => {
                      setValue(
                        "delivery_method",
                        event.target.value as typeof option.value,
                      );
                      setValue("point", "");
                      setSelectedCityRef(null);
                      setSelectedPointRef(null);
                    }}
                    checked={deliveryMethod === option.value}
                  />
                  <span>
                    <strong className="checkout-delivery-choice__title">
                      {option.value === "pickup" ? null : (
                        <em aria-hidden="true" className="nova-poshta-mark">
                          НП
                        </em>
                      )}
                      {option.label}
                    </strong>
                    <small>{option.detail}</small>
                  </span>
                </label>
              ))}
            </div>
            {deliveryMethod !== "pickup" ? (
              <div className="form-grid">
                <label className="field">
                  <span>Місто</span>
                  <Controller
                    control={control}
                    name="city"
                    render={({ field }) => (
                      <DeliveryAutocomplete
                        emptyMessage="Місто не знайдено"
                        isLoading={cities.isFetching}
                        minimumQueryLength={2}
                        onChange={(value) => {
                          if (canEnterManually) setManualDelivery(true);
                          field.onChange(value);
                          setSelectedCityRef(null);
                          setSelectedPointRef(null);
                          setValue("point", "");
                        }}
                        onSelect={(option) => {
                          setManualDelivery(false);
                          field.onChange(option.label);
                          setSelectedCityRef(option.ref);
                          setSelectedPointRef(null);
                          setValue("point", "");
                        }}
                        options={cities.data ?? []}
                        suggestionsEnabled={!manualDelivery}
                        placeholder="Почніть вводити місто й оберіть зі списку"
                        value={field.value}
                      />
                    )}
                  />
                  {errors.city ? <small>{errors.city.message}</small> : null}
                </label>
                <label className="field">
                  <span>
                    {deliveryMethod === "nova_poshta_locker"
                      ? "Поштомат"
                      : "Відділення"}
                  </span>
                  <Controller
                    control={control}
                    name="point"
                    render={({ field }) => (
                      <DeliveryAutocomplete
                        disabled={!selectedCityRef && !canEnterManually}
                        emptyMessage={
                          deliveryMethod === "nova_poshta_locker"
                            ? "Поштомат не знайдено"
                            : "Відділення не знайдено"
                        }
                        isLoading={points.isFetching}
                        onChange={(value) => {
                          if (canEnterManually) setManualDelivery(true);
                          field.onChange(value);
                          setSelectedPointRef(null);
                        }}
                        onSelect={(option) => {
                          field.onChange(option.name);
                          setSelectedPointRef(option.ref);
                        }}
                        options={points.data ?? []}
                        suggestionsEnabled={!manualDelivery}
                        placeholder={
                          selectedCityRef
                            ? `Почніть вводити номер або адресу й оберіть ${
                                deliveryMethod === "nova_poshta_locker"
                                  ? "поштомат"
                                  : "відділення"
                              } зі списку`
                            : "Спочатку оберіть місто зі списку"
                        }
                        value={field.value}
                      />
                    )}
                  />
                  {errors.point ? <small>{errors.point.message}</small> : null}
                </label>
              </div>
            ) : (
              <p className="inline-note">
                Менеджер підтвердить адресу і час самовивозу.
              </p>
            )}
            {manualDelivery ? (
              <p className="delivery-fallback-note" role="status">
                Адресу введено вручну. Менеджер перевірить пункт доставки.
              </p>
            ) : cities.error || points.error ? (
              <p className="delivery-fallback-note" role="status">
                {getUserErrorMessage(
                  cities.error ?? points.error,
                  "Не вдалося завантажити підказки. Введіть адресу вручну.",
                )}
              </p>
            ) : null}
          </div>
        </section>

        <section className="checkout-card checkout-card--payment">
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
      </form>

      <aside className="order-summary">
        <div className="order-summary__title">
          <ShoppingBag size={20} />
          <h2>Ваше замовлення</h2>
        </div>
        {tooManyItems ? (
          <p className="form-error" role="alert">
            У замовленні може бути до {MAX_CART_LINES} різних товарів.
            <button
              type="button"
              onClick={() => useCartStore.getState().open()}
            >
              Редагувати кошик
            </button>
          </p>
        ) : null}
        <div className="order-summary__items">
          {lines.map((line) => {
            const priced =
              !quoteIsStale && !quote.isError
                ? quote.data?.items.find(
                    (item) => item.product_id === line.product.id,
                  )
                : undefined;
            return (
              <div className="order-summary__line" key={line.product.id}>
                <span className="order-summary__visual">
                  <ProductVisual
                    imageSizes="80px"
                    iconSize={20}
                    product={line.product}
                  />
                </span>
                <span className="order-summary__line-name">
                  {line.product.name}
                  <small>
                    {priced ? formatMoney(priced.unit_price) : "—"} ×{" "}
                    {line.quantity}
                    {line.product.sale_unit === "meter" ? " м" : " шт"}
                  </small>
                </span>
                <strong>{priced ? formatMoney(priced.total) : "—"}</strong>
              </div>
            );
          })}
        </div>
        <div className="promo-form">
          <input
            aria-label="Промокод"
            onChange={(event) => {
              setPromoInput(event.target.value);
              if (promoCode) setPromoCode(null);
            }}
            placeholder="Промокод"
            value={promoInput}
          />
          <button
            onClick={() => {
              const nextCode = promoInput.trim().toUpperCase() || null;
              if (nextCode === promoCode) void quote.refetch();
              else setPromoCode(nextCode);
            }}
            type="button"
          >
            Застосувати
          </button>
        </div>
        {promoCode ? (
          <button
            type="button"
            onClick={() => {
              setPromoCode(null);
              setPromoInput("");
            }}
          >
            Прибрати промокод {promoCode}
          </button>
        ) : null}
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
            <span>
              Доставка <b>за тарифом</b>
            </span>
            <strong>
              До сплати <b>{formatMoney(quote.data.total)}</b>
            </strong>
          </div>
        ) : null}
        {submitError ? (
          <p className="form-error" role="alert">
            {submitError}
          </p>
        ) : null}
        <button
          className="button button--primary button--wide checkout-submit"
          disabled={
            isSubmitting ||
            !sessionReady ||
            quote.isFetching ||
            quote.isError ||
            !quote.data ||
            quoteIsStale ||
            tooManyItems
          }
          form="checkout-form"
          type="submit"
        >
          {isSubmitting || quoteIsStale ? (
            <LoaderCircle className="spin" size={19} />
          ) : (
            <Check size={19} />
          )}
          {isSubmitting ? "Створюємо замовлення…" : "Підтвердити замовлення"}
        </button>
        <p className="checkout-consent">
          Натискаючи кнопку, ви погоджуєтесь з умовами доставки, оплати та
          повернення.
        </p>
        <div className="checkout-assurances">
          <span>Умови доставки й повернення уточнить менеджер</span>
          <span>Оплата після підтвердження замовлення</span>
        </div>
      </aside>
    </div>
  );
}
