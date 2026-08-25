import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { createCustomerCompany } from "@/modules/customers/api/customer-api";
import { customerKeys } from "@/modules/customers/api/customer-queries";
import { getUserErrorMessage } from "@/shared/api/errors";

const schema = z.object({
  kind: z.enum(["fop", "legal"]),
  name: z.string().trim().min(2, "Вкажіть назву").max(180),
  edrpou: z
    .string()
    .trim()
    .regex(/^\d{8,10}$/, "ЄДРПОУ: 8–10 цифр"),
});

type Values = z.infer<typeof schema>;

export function CustomerCompanyForm() {
  const queryClient = useQueryClient();
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { kind: "legal" },
  });
  const mutation = useMutation({
    mutationFn: createCustomerCompany,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: customerKeys.profile() });
    },
  });

  const submit = handleSubmit((values) => mutation.mutate(values));
  return (
    <form className="customer-company-form form-stack" onSubmit={submit}>
      <div>
        <h2>Підключити бізнес-умови</h2>
        <p>
          Після перевірки компанії застосовуватимуться гуртові ціни та
          накопичувальна знижка.
        </p>
      </div>
      <div className="form-grid">
        <label className="field">
          <span>Тип</span>
          <select {...register("kind")}>
            <option value="legal">Юридична особа</option>
            <option value="fop">ФОП</option>
          </select>
        </label>
        <label className="field">
          <span>ЄДРПОУ / ІПН</span>
          <input inputMode="numeric" {...register("edrpou")} />
          {errors.edrpou ? <small>{errors.edrpou.message}</small> : null}
        </label>
      </div>
      <label className="field">
        <span>Назва компанії або ФОП</span>
        <input autoComplete="organization" {...register("name")} />
        {errors.name ? <small>{errors.name.message}</small> : null}
      </label>
      {mutation.isError ? (
        <p className="form-error" role="alert">
          {getUserErrorMessage(
            mutation.error,
            "Не вдалося подати дані компанії",
          )}
        </p>
      ) : null}
      <button
        className="button button--primary"
        disabled={mutation.isPending}
        type="submit"
      >
        {mutation.isPending ? "Надсилаємо…" : "Надіслати на перевірку"}
      </button>
    </form>
  );
}
