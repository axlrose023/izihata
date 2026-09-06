import { Minus, Plus, ShoppingBag, Trash2, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { ProductVisual } from "@/modules/catalog/components/product-visual";
import { apiClient } from "@/shared/api/client";
import { buildQuery } from "@/shared/api/query";
import { formatMoney } from "@/shared/lib/format";
import { useBodyScrollLock } from "@/shared/lib/use-body-scroll-lock";
import type { Product } from "@/shared/types/api";

import { cartCount, useCartStore } from "../store";

export function CartDrawer() {
  const { lines, isOpen, add, close, remove, setQuantity } = useCartStore();
  const [recommendations, setRecommendations] = useState<Product[]>([]);
  const recommendationKey = useMemo(() => {
    if (!isOpen || !lines.length) return null;
    return lines.map((line) => line.product.id).join(",");
  }, [isOpen, lines]);
  useBodyScrollLock(isOpen);
  const total = lines.reduce(
    (sum, line) => sum + Number(line.product.price) * line.quantity,
    0,
  );

  useEffect(() => {
    if (!recommendationKey) {
      return;
    }
    const controller = new AbortController();
    // "Bought together" is curated in the admin panel, not inferred here.
    void apiClient<Product[]>(
      `/catalog/recommendations${buildQuery({ id: recommendationKey.split(",") })}`,
      { signal: controller.signal },
    )
      .then((result) => {
        setRecommendations(result.slice(0, 3));
      })
      .catch((error: unknown) => {
        if (!(error instanceof DOMException && error.name === "AbortError")) {
          setRecommendations([]);
        }
      });
    return () => controller.abort();
  }, [recommendationKey]);

  if (!isOpen) return null;

  return (
    <div className="drawer" data-open>
      <button
        aria-label="Закрити кошик"
        className="drawer__backdrop"
        onClick={close}
        type="button"
      />
      <aside aria-label="Кошик" className="drawer__panel">
        <header className="drawer__header">
          <div>
            <span className="eyebrow">Ваше замовлення</span>
            <h2>Кошик · {cartCount(lines)}</h2>
          </div>
          <button aria-label="Закрити" className="icon-button" onClick={close}>
            <X size={20} />
          </button>
        </header>
        {lines.length ? (
          <>
            <div className="drawer__items">
              {lines.map(({ product, quantity }) => (
                <article className="cart-line" key={product.id}>
                  <div className="cart-line__visual">
                    <ProductVisual iconSize={25} product={product} />
                  </div>
                  <div className="cart-line__content">
                    <Link to={`/products/${product.slug}`} onClick={close}>
                      {product.name}
                    </Link>
                    <strong>{formatMoney(product.price)}</strong>
                    <div className="quantity-control">
                      <button
                        aria-label="Зменшити кількість"
                        onClick={() => setQuantity(product.id, quantity - 1)}
                        type="button"
                      >
                        <Minus size={15} />
                      </button>
                      <span>{quantity}</span>
                      <button
                        aria-label="Збільшити кількість"
                        onClick={() => setQuantity(product.id, quantity + 1)}
                        type="button"
                      >
                        <Plus size={15} />
                      </button>
                    </div>
                  </div>
                  <button
                    aria-label="Видалити товар"
                    className="cart-line__remove"
                    onClick={() => remove(product.id)}
                    type="button"
                  >
                    <Trash2 size={17} />
                  </button>
                </article>
              ))}
            </div>
            {recommendations.length ? (
              <section className="cart-recommendations">
                <strong>З цим купують</strong>
                {recommendations.map((product) => (
                  <article key={product.id}>
                    <div className="cart-recommendations__visual">
                      <ProductVisual iconSize={28} product={product} />
                    </div>
                    <div>
                      <Link to={`/products/${product.slug}`} onClick={close}>
                        {product.name}
                      </Link>
                      <span>{formatMoney(product.price)}</span>
                    </div>
                    <button
                      aria-label={`Додати ${product.name}`}
                      onClick={() => add(product)}
                      type="button"
                    >
                      <Plus size={16} />
                    </button>
                  </article>
                ))}
              </section>
            ) : null}
            <footer className="drawer__footer">
              <div className="drawer__total">
                <span>Попередня сума</span>
                <strong>{formatMoney(total)}</strong>
              </div>
              <p>Точну ціну та знижку розрахує сервер перед оформленням.</p>
              <Link
                className="button button--primary button--wide"
                to="/checkout"
                onClick={close}
              >
                Оформити замовлення
              </Link>
            </footer>
          </>
        ) : (
          <div className="drawer__empty">
            <ShoppingBag size={42} />
            <h3>Кошик порожній</h3>
            <p>Додайте потрібні товари з каталогу.</p>
            <Link
              className="button button--primary"
              to="/catalog"
              onClick={close}
            >
              До каталогу
            </Link>
          </div>
        )}
      </aside>
    </div>
  );
}
