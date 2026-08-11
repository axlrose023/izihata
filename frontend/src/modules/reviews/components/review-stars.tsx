import { Star } from "lucide-react";

export function ReviewStars({ rating }: { rating: number }) {
  const normalized = Math.max(1, Math.min(5, Math.round(rating)));

  return (
    <span
      aria-label={`Оцінка ${normalized} з 5`}
      className="review-stars"
      role="img"
    >
      {Array.from({ length: 5 }, (_, index) => (
        <Star
          aria-hidden="true"
          fill={index < normalized ? "currentColor" : "none"}
          key={index}
          size={15}
        />
      ))}
    </span>
  );
}
