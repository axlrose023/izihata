import { formatDate } from "@/shared/lib/format";
import type { ProductReview } from "@/shared/types/api";
import { Carousel } from "@/shared/ui/carousel";

import { ReviewStars } from "./review-stars";

export function TestimonialsSection({ reviews }: { reviews: ProductReview[] }) {
  if (!reviews.length) return null;

  return (
    <section className="section container testimonials-section">
      <div className="section-heading">
        <div>
          <span className="eyebrow">Досвід клієнтів</span>
          <h2>Відгуки наших клієнтів</h2>
        </div>
      </div>
      <Carousel ariaLabel="Відгуки клієнтів" autoplayMs={10_000}>
        {reviews.map((review) => (
          <article className="carousel__item testimonial" key={review.id}>
            <div className="testimonial__head">
              <strong>{review.author}</strong>
              <span>{formatDate(review.created_at)}</span>
              <ReviewStars rating={review.rating} />
            </div>
            <p>{review.text}</p>
          </article>
        ))}
      </Carousel>
    </section>
  );
}
