import { Star } from "lucide-react";

export function ProductRating({
  rating,
  reviews,
}: {
  rating: string;
  reviews: number;
}) {
  const value = Math.max(0, Math.min(5, Number(rating) || 0));
  const rounded = Math.round(value);

  return (
    <span
      aria-label={`Рейтинг ${value.toFixed(1)} з 5, відгуків: ${reviews}`}
      className="product-rating"
    >
      <span aria-hidden="true" className="product-rating__stars">
        {Array.from({ length: 5 }, (_, index) => (
          <Star
            fill={index < rounded ? "currentColor" : "none"}
            key={index}
            size={13}
          />
        ))}
      </span>
      <span>{value.toFixed(1)}</span>
      <small>({reviews})</small>
    </span>
  );
}
