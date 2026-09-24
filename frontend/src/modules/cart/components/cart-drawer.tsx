import { Minus, Plus, ShoppingCart, Trash2, X } from "lucide-react";
import { Link } from "react-router-dom";

import { ProductVisual } from "@/modules/catalog/components/product-visual";
import {
  formatMoney,
  pluralizePositions,
  saleUnitLabel,
} from "@/shared/lib/format";
import { useBodyScrollLock } from "@/shared/lib/use-body-scroll-lock";
import { useCloseOnEscape } from "@/shared/lib/use-close-on-escape";
import type { Product } from "@/shared/types/api";

import { cartCount, useCartStore } from "../store";

export function CartDrawer() {
  const { lines, isOpen, close, remove, setQuantity } = useCartStore();
  useBodyScrollLock(isOpen);
  useCloseOnEscape(isOpen, close);
  const total = lines.reduce(
    (sum, line) => sum + Number(line.product.price) * line.quantity,
    0,
  );

  if (!isOpen) return null;

  return (
    <div className="drawer" data-open>
      <button
        aria-label="Закрити кошик"
        className="drawer__backdrop"
        onClick={close}
        type="button"
      />
      <aside
        aria-label="Кошик"
        aria-modal="true"
        className="drawer__panel"
        role="dialog"
      >
        <header className="drawer__header">
          <ShoppingCart aria-hidden="true" />
          <h2>Кошик</h2>
          <span className="drawer__count">
            {pluralizePositions(cartCount(lines))}
          </span>
          <button
            aria-label="Закрити"
            className="drawer__close"
            onClick={close}
            type="button"
          >
            <X size={20} />
          </button>
        </header>
        {lines.length ? (
          <>
            <section
              className="drawer__delivery-progress"
              aria-label="Умови доставки"
            >
              <div>
                <span>
                  До безкоштовної доставки <strong>[залишок] ₴</strong>
                </span>
                <span>поріг [поріг] ₴</span>
              </div>
              <span aria-hidden="true">
                <i />
              </span>
            </section>
            <div className="drawer__items">
              {lines.map(({ product, quantity }) => (
                <article className="cart-line" key={product.id}>
                  <div className="cart-line__visual">
                    <ProductVisual iconSize={25} product={product} />
                  </div>
                  <div className="cart-line__content">
                    <div className="cart-line__top">
                      <div>
                        <span className="eyebrow">{product.brand}</span>
                        <Link to={`/products/${product.slug}`} onClick={close}>
                          {product.name}
                        </Link>
                        <small>{product.sku}</small>
                      </div>
                      <button
                        aria-label="Видалити товар"
                        className="cart-line__remove"
                        onClick={() => remove(product.id)}
                        type="button"
                      >
                        <Trash2 size={17} />
                      </button>
                    </div>
                    <div className="cart-line__bottom">
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
                        <small>{saleUnitLabel(product.sale_unit)}</small>
                      </div>
                      <div>
                        <strong>
                          {formatMoney(Number(product.price) * quantity)}
                        </strong>
                        <small>
                          {formatMoney(product.price)} × {quantity}
                          {saleUnitLabel(product.sale_unit)}
                        </small>
                      </div>
                    </div>
                  </div>
                </article>
              ))}
            </div>
            <footer className="drawer__footer">
              <div className="drawer__totals">
                <span>
                  Товари, {pluralizePositions(cartCount(lines))}
                  <b>{formatMoney(total)}</b>
                </span>
                <span>
                  Доставка <b>за тарифом перевізника</b>
                </span>
                <strong>
                  До сплати <b>{formatMoney(total)}</b>
                </strong>
              </div>
              <Link
                className="button button--primary button--wide"
                to="/checkout"
                onClick={close}
              >
                Оформити замовлення
              </Link>
              <button
                className="button button--outline button--wide"
                onClick={close}
                type="button"
              >
                Продовжити покупки
              </button>
            </footer>
          </>
        ) : (
          <div className="drawer__empty">
            <ShoppingCart size={42} />
            <h3>У кошику поки порожньо</h3>
            <p>
              Почніть з категорії або підберіть номінал автомата за
              навантаженням.
            </p>
            <Link
              className="button button--primary"
              to="/catalog"
              onClick={close}
            >
              Перейти в каталог
            </Link>
            <Link
              className="button button--outline"
              to="/advisors"
              onClick={close}
            >
              Підібрати за параметрами
            </Link>
          </div>
        )}
      </aside>
    </div>
  );
}
