import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { createProductReview } from "@/modules/catalog/api/catalog-api";
import { getUserErrorMessage } from "@/shared/api/errors";
import type { ProductReview } from "@/shared/types/api";

import { ReviewStars } from "./review-stars";

const schema = z.object({
  author: z.string().trim().min(2, "Вкажіть ім’я").max(120),
  email: z.string().trim().email("Вкажіть коректний email").max(254),
  rating: z.coerce.number().int().min(1).max(5),
  text: z.string().trim().min(10, "Напишіть щонайменше 10 символів").max(4000),
});

type FormValues = z.input<typeof schema>;
type Values = z.output<typeof schema>;

export function ProductReviews({
  reviews,
  productSlug,
}: {
  reviews: ProductReview[];
  productSlug: string;
}) {
  const [submitted, setSubmitted] = useState(false);
  const [requestError, setRequestError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormValues, unknown, Values>({
    resolver: zodResolver(schema),
    defaultValues: { rating: 5 },
  });

  const submit = handleSubmit(async (values) => {
    setRequestError(null);
    try {
      await createProductReview(productSlug, values);
      reset({ rating: 5 });
      setSubmitted(true);
    } catch (error) {
      setRequestError(
        getUserErrorMessage(error, "Не вдалося надіслати відгук"),
      );
    }
  });

  return (
    <section className="product-reviews">
      <div className="section-heading">
        <div>
          <span className="eyebrow">Досвід покупців</span>
          <h2>Відгуки</h2>
        </div>
      </div>
      {reviews.length ? (
        <div className="product-reviews__list">
          {reviews.map((review) => (
            <article key={review.id}>
              <header>
                <strong>{review.author}</strong>
                <ReviewStars rating={review.rating} />
              </header>
              <p>{review.text}</p>
            </article>
          ))}
        </div>
      ) : (
        <p className="product-reviews__empty">
          Ще немає відгуків. Поділіться першим досвідом.
        </p>
      )}
      <form className="product-review-form form-stack" onSubmit={submit}>
        <h3>Залишити відгук</h3>
        <div className="product-review-form__contacts">
          <label className="field">
            <span>Ім’я</span>
            <input autoComplete="name" {...register("author")} />
            {errors.author ? <small>{errors.author.message}</small> : null}
          </label>
          <label className="field">
            <span>Email</span>
            <input autoComplete="email" type="email" {...register("email")} />
            {errors.email ? <small>{errors.email.message}</small> : null}
          </label>
        </div>
        <label className="field">
          <span>Оцінка</span>
          <select aria-label="Оцінка" {...register("rating")}>
            <option value="5">5 — чудово</option>
            <option value="4">4 — добре</option>
            <option value="3">3 — нормально</option>
            <option value="2">2 — є зауваження</option>
            <option value="1">1 — погано</option>
          </select>
        </label>
        <label className="field">
          <span>Ваш відгук</span>
          <textarea rows={4} {...register("text")} />
          {errors.text ? <small>{errors.text.message}</small> : null}
        </label>
        {submitted ? (
          <p className="success-message" role="status">
            Дякуємо! Відгук з’явиться після перевірки.
          </p>
        ) : null}
        {requestError ? (
          <p className="form-error" role="alert">
            {requestError}
          </p>
        ) : null}
        <button
          className="button button--primary"
          disabled={isSubmitting}
          type="submit"
        >
          {isSubmitting ? "Надсилаємо…" : "Надіслати відгук"}
        </button>
      </form>
    </section>
  );
}
