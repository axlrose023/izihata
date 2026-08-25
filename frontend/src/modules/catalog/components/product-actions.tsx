import {
  GitCompareArrows,
  Heart,
  Minus,
  Plus,
  ShoppingCart,
} from "lucide-react";
import { useState } from "react";

import { useCartStore } from "@/modules/cart/store";
import { useCollectionStore } from "@/modules/collections/store";
import { LeadAction } from "@/modules/leads/components/lead-action";
import type { Product } from "@/shared/types/api";

import { StockSubscriptionForm } from "./stock-subscription-form";

export function ProductActions({ product }: { product: Product }) {
  const add = useCartStore((state) => state.add);
  const favorites = useCollectionStore((state) => state.favorites);
  const compare = useCollectionStore((state) => state.compare);
  const toggleFavorite = useCollectionStore((state) => state.toggleFavorite);
  const toggleCompare = useCollectionStore((state) => state.toggleCompare);
  const [quantity, setQuantity] = useState(1);
  const unavailable = product.stock_status === "out_of_stock";
  const changeQuantity = (value: number) =>
    setQuantity(Math.max(1, Math.min(99, value)));

  return (
    <div className="product-actions-panel">
      {!unavailable ? (
        <label className="product-quantity">
          <span>Кількість</span>
          <span className="product-quantity__control">
            <button
              aria-label="Зменшити кількість товару"
              disabled={quantity === 1}
              onClick={() => changeQuantity(quantity - 1)}
              type="button"
            >
              <Minus size={15} />
            </button>
            <input
              aria-label="Кількість товару"
              inputMode="numeric"
              max={99}
              min={1}
              onChange={(event) => {
                const value = Number(event.currentTarget.value);
                changeQuantity(Number.isFinite(value) ? value : 1);
              }}
              type="number"
              value={quantity}
            />
            <button
              aria-label="Збільшити кількість товару"
              disabled={quantity === 99}
              onClick={() => changeQuantity(quantity + 1)}
              type="button"
            >
              <Plus size={15} />
            </button>
          </span>
        </label>
      ) : null}
      {unavailable ? (
        <StockSubscriptionForm slug={product.slug} />
      ) : (
        <>
          <button
            className="button button--primary button--wide"
            onClick={() => add(product, quantity)}
            type="button"
          >
            <ShoppingCart size={19} /> Додати в кошик
          </button>
          <LeadAction
            className="button button--outline button--wide"
            label="Купити в один клік"
            productId={product.id}
            type="quick_buy"
          />
        </>
      )}
      <div className="product-secondary-actions">
        <button
          aria-pressed={favorites.includes(product.id)}
          onClick={() => toggleFavorite(product.id)}
          type="button"
        >
          <Heart size={18} />
          {favorites.includes(product.id) ? "В обраному" : "В обране"}
        </button>
        <button
          aria-pressed={compare.includes(product.id)}
          onClick={() => toggleCompare(product.id)}
          type="button"
        >
          <GitCompareArrows size={18} />
          {compare.includes(product.id) ? "У порівнянні" : "Порівняти"}
        </button>
      </div>
    </div>
  );
}
