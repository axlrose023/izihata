import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import {
  createBoardRequest,
  estimateBoard,
  type BoardConfiguration,
} from "@/modules/custom-boards/api/custom-board-api";
import { getUserErrorMessage } from "@/shared/api/errors";
import { formatMoney } from "@/shared/lib/format";

const schema = z.object({
  application: z.enum(["apartment", "house", "industrial"]),
  groups_count: z.coerce
    .number()
    .int()
    .min(1, "Вкажіть кількість груп")
    .max(200),
  ip_class: z
    .string()
    .trim()
    .regex(/^IP\d{2}$/i, "Формат: IP20, IP54 тощо"),
  automation_brand: z.string().trim().max(120).optional(),
  budget: z
    .string()
    .trim()
    .regex(/^\d*(\.\d{1,2})?$/, "Вкажіть суму числом")
    .optional(),
  customer_name: z.string().trim().min(2, "Вкажіть ім’я").max(120),
  phone: z
    .string()
    .trim()
    .regex(/^\+?[0-9 ()-]{8,24}$/, "Вкажіть коректний телефон"),
  email: z.union([
    z.literal(""),
    z.string().trim().email("Вкажіть коректний email"),
  ]),
  details: z.string().trim().max(4000).optional(),
});
const configurationSchema = schema.pick({
  application: true,
  groups_count: true,
  ip_class: true,
  automation_brand: true,
  budget: true,
});

type FormValues = z.input<typeof schema>;
type Values = z.output<typeof schema>;

function configuration(
  values: z.output<typeof configurationSchema>,
): BoardConfiguration {
  return {
    application: values.application,
    groups_count: values.groups_count,
    ip_class: values.ip_class.toUpperCase(),
    automation_brand: values.automation_brand || undefined,
    budget: values.budget || undefined,
  };
}

export function CustomBoardForm() {
  const [submitted, setSubmitted] = useState(false);
  const {
    register,
    handleSubmit,
    getValues,
    trigger,
    formState: { errors },
  } = useForm<FormValues, unknown, Values>({
    resolver: zodResolver(schema),
    defaultValues: {
      application: "apartment",
      groups_count: 12,
      ip_class: "IP31",
      phone: "+380",
    },
  });
  const estimateMutation = useMutation({ mutationFn: estimateBoard });
  const requestMutation = useMutation({
    mutationFn: createBoardRequest,
    onSuccess: () => setSubmitted(true),
  });

  const getEstimate = async () => {
    const valid = await trigger([
      "application",
      "groups_count",
      "ip_class",
      "automation_brand",
      "budget",
    ]);
    if (!valid) return;
    const result = configurationSchema.safeParse(getValues());
    if (!result.success) return;
    estimateMutation.mutate(configuration(result.data));
  };
  const submit = handleSubmit((values) =>
    requestMutation.mutate({
      ...configuration(values),
      customer_name: values.customer_name,
      phone: values.phone,
      email: values.email || undefined,
      details: values.details || undefined,
    }),
  );

  if (submitted) {
    return (
      <div
        className="custom-board-form custom-board-form__success"
        role="status"
      >
        <strong>Запит прийнято.</strong>
        <p>Менеджер підготує пропозицію у вказаний строк.</p>
      </div>
    );
  }

  return (
    <form className="custom-board-form form-stack" onSubmit={submit}>
      <div className="form-grid">
        <label className="field">
          <span>Тип об’єкта</span>
          <select {...register("application")}>
            <option value="apartment">Квартира</option>
            <option value="house">Будинок</option>
            <option value="industrial">Комерційний об’єкт</option>
          </select>
        </label>
        <label className="field">
          <span>Кількість груп</span>
          <input
            inputMode="numeric"
            min="1"
            type="number"
            {...register("groups_count")}
          />
          {errors.groups_count ? (
            <small>{errors.groups_count.message}</small>
          ) : null}
        </label>
        <label className="field">
          <span>Ступінь захисту</span>
          <input placeholder="IP31" {...register("ip_class")} />
          {errors.ip_class ? <small>{errors.ip_class.message}</small> : null}
        </label>
        <label className="field">
          <span>Бренд автоматики</span>
          <input
            placeholder="Наприклад, ABB"
            {...register("automation_brand")}
          />
        </label>
        <label className="field">
          <span>Орієнтовний бюджет, ₴</span>
          <input inputMode="decimal" {...register("budget")} />
          {errors.budget ? <small>{errors.budget.message}</small> : null}
        </label>
      </div>
      <button
        className="button button--outline"
        disabled={estimateMutation.isPending}
        onClick={getEstimate}
        type="button"
      >
        {estimateMutation.isPending ? "Оцінюємо…" : "Оцінити комплектацію"}
      </button>
      {estimateMutation.isError ? (
        <p className="form-error" role="alert">
          {getUserErrorMessage(
            estimateMutation.error,
            "Не вдалося розрахувати вартість",
          )}
        </p>
      ) : null}
      {estimateMutation.data ? (
        <div className="custom-board-estimate">
          <strong>
            Від {formatMoney(estimateMutation.data.starting_price)}
          </strong>
          <span>
            Відповідь до {estimateMutation.data.response_sla_hours} год.
          </span>
          <ul>
            {estimateMutation.data.suggested_components.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
          <small>{estimateMutation.data.reference_notice}</small>
        </div>
      ) : null}
      <div className="form-grid">
        <label className="field">
          <span>Ім’я</span>
          <input autoComplete="name" {...register("customer_name")} />
          {errors.customer_name ? (
            <small>{errors.customer_name.message}</small>
          ) : null}
        </label>
        <label className="field">
          <span>Телефон</span>
          <input autoComplete="tel" inputMode="tel" {...register("phone")} />
          {errors.phone ? <small>{errors.phone.message}</small> : null}
        </label>
      </div>
      <label className="field">
        <span>Email (необов’язково)</span>
        <input autoComplete="email" type="email" {...register("email")} />
        {errors.email ? <small>{errors.email.message}</small> : null}
      </label>
      <label className="field">
        <span>Деталі проєкту</span>
        <textarea rows={4} {...register("details")} />
      </label>
      {requestMutation.isError ? (
        <p className="form-error" role="alert">
          {getUserErrorMessage(
            requestMutation.error,
            "Не вдалося надіслати запит",
          )}
        </p>
      ) : null}
      <button
        className="button button--primary"
        disabled={requestMutation.isPending}
        type="submit"
      >
        {requestMutation.isPending ? "Надсилаємо…" : "Надіслати запит"}
      </button>
    </form>
  );
}
