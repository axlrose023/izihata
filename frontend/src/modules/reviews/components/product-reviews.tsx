import type { ProductReview } from "@/shared/types/api";

import { ReviewStars } from "./review-stars";

export function ProductReviews({ reviews }: { reviews: ProductReview[] }) {
  if (!reviews.length) return null;

  return (
    <section className="product-reviews">
      <div className="section-heading">
        <div>
          <span className="eyebrow">Досвід покупців</span>
          <h2>Відгуки</h2>
        </div>
      </div>
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
    </section>
  );
}
