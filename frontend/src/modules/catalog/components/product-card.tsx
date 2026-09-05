import { Check, GitCompareArrows, Heart, ShoppingCart } from "lucide-react";
import { Link } from "react-router-dom";

import { cartQuantityOf, useCartStore } from "@/modules/cart/store";
import { useCollectionStore } from "@/modules/collections/store";
import { LeadAction } from "@/modules/leads/components/lead-action";
import { discountPercent, formatMoney } from "@/shared/lib/format";
import type { Product } from "@/shared/types/api";
import { ProductRating } from "@/shared/ui/product-rating";
import { StatusBadge } from "@/shared/ui/status-badge";

import { ProductVisual } from "./product-visual";

const badgeLabels: Record<NonNullable<Product["badge"]>, string> = {
  top: "Хіт",
  new: "Новинка",
  sale: "Акція",
  promotion: "Промо",
  clearance: "Уцінка",
  recommended: "Рекомендуємо",
};

export function ProductCard({ product }: { product: Product }) {
  const add = useCartStore((state) => state.add);
  const openCart = useCartStore((state) => state.open);
  const inCart = useCartStore((state) =>
    cartQuantityOf(state.lines, product.id),
  );
  const favorites = useCollectionStore((state) => state.favorites);
  const compare = useCollectionStore((state) => state.compare);
  const toggleFavorite = useCollectionStore((state) => state.toggleFavorite);
  const toggleCompare = useCollectionStore((state) => state.toggleCompare);
  const isFavorite = favorites.includes(product.id);
  const isCompared = compare.includes(product.id);
  const specs = Object.entries(product.specs).slice(0, 2);
  const unavailable = product.stock_status === "out_of_stock";
  const discount = discountPercent(product.price, product.old_price);

  return (
    <article
      className="product-card"
      data-in-cart={inCart ? "true" : undefined}
    >
      <div className="product-card__visual">
        {product.badge ? (
          <span className="product-card__badge" data-badge={product.badge}>
            {badgeLabels[product.badge]}
          </span>
        ) : null}
        <div className="product-card__actions">
          <button
            aria-label={isFavorite ? "Прибрати з обраного" : "Додати в обране"}
            aria-pressed={isFavorite}
            className="icon-button"
            onClick={() => toggleFavorite(product.id)}
            type="button"
          >
            <Heart size={18} />
          </button>
          <button
            aria-label={
              isCompared ? "Прибрати з порівняння" : "Додати до порівняння"
            }
            aria-pressed={isCompared}
            className="icon-button"
            onClick={() => toggleCompare(product.id)}
            type="button"
          >
            <GitCompareArrows size={18} />
          </button>
        </div>
        <ProductVisual iconSize={72} product={product} />
      </div>
      <div className="product-card__body">
        <div className="product-card__meta">
          <span className="eyebrow">
            {product.brand} · {product.sku}
          </span>
          <StatusBadge status={product.stock_status} />
        </div>
        <h3 className="product-card__name">
          <Link to={`/products/${product.slug}`}>{product.name}</Link>
        </h3>
        {inCart ? (
          <span className="product-card__in-cart">
            <Check size={14} /> У кошику: {inCart} шт.
          </span>
        ) : null}
        {specs.length ? (
          <dl className="product-card__specs">
            {specs.map(([key, value]) => (
              <div key={key}>
                <dt>{key}</dt>
                <dd>{value}</dd>
              </div>
            ))}
          </dl>
        ) : null}
        <ProductRating
          rating={product.rating}
          reviews={product.reviews_count}
        />
        <div className="product-card__footer">
          <div className="price-stack">
            <strong>{formatMoney(product.price)}</strong>
            {product.old_price ? (
              <span className="price-stack__was">
                <del>{formatMoney(product.old_price)}</del>
                {discount ? (
                  <b className="price-discount">−{discount}%</b>
                ) : null}
              </span>
            ) : null}
          </div>
          <div className="product-card__buy-actions">
            {!unavailable ? (
              <>
                <button
                  aria-label={inCart ? "Перейти в кошик" : "Додати в кошик"}
                  className="cart-add"
                  data-in-cart={inCart ? "true" : undefined}
                  onClick={() => (inCart ? openCart() : add(product))}
                  type="button"
                >
                  {inCart ? <Check size={19} /> : <ShoppingCart size={19} />}
                  <span>{inCart ? "У кошику" : "В кошик"}</span>
                </button>
                <LeadAction
                  className="quick-buy-button"
                  label="1 клік"
                  productId={product.id}
                  type="quick_buy"
                />
              </>
            ) : (
              <Link
                className="quick-buy-button"
                to={`/products/${product.slug}`}
              >
                Повідомити
              </Link>
            )}
          </div>
        </div>
      </div>
    </article>
  );
}
