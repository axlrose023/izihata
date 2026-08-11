import type { ProductReview } from "@/shared/types/api";

import { ReviewStars } from "./review-stars";

export function TestimonialsSection({ reviews }: { reviews: ProductReview[] }) {
  if (!reviews.length) return null;

  return (
    <section className="section container testimonials-section">
      <div className="section-heading">
        <div>
          <span className="eyebrow">Досвід клієнтів</span>
          <h2>Що кажуть покупці</h2>
        </div>
      </div>
      <div className="testimonial-grid">
        {reviews.map((review) => (
          <article key={review.id}>
            <ReviewStars rating={review.rating} />
            <p>{review.text}</p>
            <strong>{review.author}</strong>
          </article>
        ))}
      </div>
    </section>
  );
}
