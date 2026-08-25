import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { createStockSubscription } from "@/modules/catalog/api/catalog-api";
import { getUserErrorMessage } from "@/shared/api/errors";

const schema = z.object({
  email: z.string().trim().email("Вкажіть коректний email").max(254),
});

type Values = z.infer<typeof schema>;

export function StockSubscriptionForm({ slug }: { slug: string }) {
  const [submitted, setSubmitted] = useState(false);
  const [requestError, setRequestError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<Values>({ resolver: zodResolver(schema) });

  const submit = handleSubmit(async ({ email }) => {
    setRequestError(null);
    try {
      await createStockSubscription(slug, email);
      setSubmitted(true);
    } catch (error) {
      setRequestError(
        getUserErrorMessage(error, "Не вдалося оформити сповіщення"),
      );
    }
  });

  if (submitted) {
    return (
      <p className="product-stock-subscription__success" role="status">
        Повідомимо на email, щойно товар з’явиться в наявності.
      </p>
    );
  }

  return (
    <form className="product-stock-subscription" onSubmit={submit}>
      <strong>Повідомити про наявність</strong>
      <p>Залиште email — надішлемо лише одне сповіщення про цей товар.</p>
      <div>
        <input
          aria-label="Email для сповіщення"
          autoComplete="email"
          placeholder="you@example.com"
          type="email"
          {...register("email")}
        />
        <button
          className="button button--outline"
          disabled={isSubmitting}
          type="submit"
        >
          {isSubmitting ? "Надсилаємо…" : "Повідомити"}
        </button>
      </div>
      {errors.email ? (
        <small className="form-error">{errors.email.message}</small>
      ) : null}
      {requestError ? (
        <small className="form-error" role="alert">
          {requestError}
        </small>
      ) : null}
    </form>
  );
}
