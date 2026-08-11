import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { apiClient } from "@/shared/api/client";
import { getUserErrorMessage } from "@/shared/api/errors";
import type { Lead, LeadType } from "@/shared/types/api";
import { Modal } from "@/shared/ui/modal";

const formSchema = z.object({
  name: z.string().trim().min(2, "Вкажіть ім’я").max(120),
  phone: z
    .string()
    .trim()
    .regex(/^\+?[0-9 ()-]{10,20}$/, "Вкажіть коректний номер"),
  company: z.string().trim().max(180).optional(),
});

type FormValues = z.infer<typeof formSchema>;

const titles: Record<LeadType, string> = {
  callback: "Замовити дзвінок",
  quick_buy: "Купити в один клік",
  wholesale: "Запит для гуртових клієнтів",
};

export function LeadDialog({
  open,
  type,
  productId,
  onClose,
}: {
  open: boolean;
  type: LeadType;
  productId?: string;
  onClose: () => void;
}) {
  const [submitted, setSubmitted] = useState(false);
  const [requestError, setRequestError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: { name: "", phone: "+380", company: "" },
  });

  const close = () => {
    reset();
    setSubmitted(false);
    setRequestError(null);
    onClose();
  };

  const submit = handleSubmit(async (values) => {
    if (type === "wholesale" && !values.company) {
      setRequestError("Для гуртового запиту вкажіть компанію");
      return;
    }

    setRequestError(null);
    try {
      await apiClient<Lead>("/leads", {
        method: "POST",
        body: JSON.stringify({
          type,
          name: values.name,
          phone: values.phone,
          company: type === "wholesale" ? values.company : null,
          product_id: type === "quick_buy" ? productId : null,
        }),
      });
      setSubmitted(true);
    } catch (error) {
      setRequestError(getUserErrorMessage(error, "Не вдалося надіслати запит"));
    }
  });

  return (
    <Modal onClose={close} open={open} title={titles[type]}>
      {submitted ? (
        <div className="success-message" role="status">
          <strong>Дякуємо!</strong>
          <p>Менеджер зв’яжеться з вами найближчим робочим часом.</p>
          <button
            className="button button--primary"
            onClick={close}
            type="button"
          >
            Готово
          </button>
        </div>
      ) : (
        <form className="form-stack" onSubmit={submit}>
          <label className="field">
            <span>Ім’я</span>
            <input autoComplete="name" {...register("name")} />
            {errors.name ? <small>{errors.name.message}</small> : null}
          </label>
          <label className="field">
            <span>Телефон</span>
            <input autoComplete="tel" inputMode="tel" {...register("phone")} />
            {errors.phone ? <small>{errors.phone.message}</small> : null}
          </label>
          {type === "wholesale" ? (
            <label className="field">
              <span>Компанія</span>
              <input autoComplete="organization" {...register("company")} />
            </label>
          ) : null}
          {requestError ? (
            <p className="form-error" role="alert">
              {requestError}
            </p>
          ) : null}
          <button
            className="button button--primary button--wide"
            disabled={isSubmitting}
            type="submit"
          >
            {isSubmitting ? "Надсилаємо…" : "Надіслати"}
          </button>
          <small className="form-note">
            Надсилаючи форму, ви погоджуєтесь на обробку контактних даних.
          </small>
        </form>
      )}
    </Modal>
  );
}
