import { useEffect, useState } from "react";

import { cartQuantityOf, useCartStore } from "@/modules/cart/store";
import { LeadAction } from "@/modules/leads/components/lead-action";

import { formatMoney, saleUnitLabel } from "@/shared/lib/format";
import type { Product } from "@/shared/types/api";

/**
 * Липка панель покупки (артборд Product). З'являється, коли основний блок
 * із кнопками вийшов з екрана, щоб ціна й «У кошик» лишались під рукою.
 */
export function ProductStickyBar({
  product,
  watch,
}: {
  product: Product;
  watch: React.RefObject<HTMLElement | null>;
}) {
  const [shown, setShown] = useState(false);
  const addToCart = useCartStore((state) => state.add);
  const openCart = useCartStore((state) => state.open);
  const inCart = useCartStore((state) =>
    cartQuantityOf(state.lines, product.id),
  );

  useEffect(() => {
    const target = watch.current;
    if (!target) return;
    // Позицію рахуємо з живого елемента на кожній прокрутці: IntersectionObserver
    // повідомляє лише про перетин, і якщо воно сталося під час початкових зсувів
    // розкладки, панель лишалась прихованою назавжди — саме так і було на
    // мобільному, де зображення товару підвантажується пізніше.
    let frame = 0;
    const measure = () => {
      frame = 0;
      setShown(target.getBoundingClientRect().bottom <= 0);
    };
    const schedule = () => {
      if (!frame) frame = requestAnimationFrame(measure);
    };
    measure();
    window.addEventListener("scroll", schedule, { passive: true });
    window.addEventListener("resize", schedule);
    return () => {
      if (frame) cancelAnimationFrame(frame);
      window.removeEventListener("scroll", schedule);
      window.removeEventListener("resize", schedule);
    };
  }, [watch]);

  return (
    <div
      aria-hidden={!shown}
      className="product-sticky-bar"
      data-shown={shown || undefined}
    >
      <div className="container product-sticky-bar__inner">
        <div className="product-sticky-bar__title">
          <strong>{product.name}</strong>
          <small>
            {product.brand} · {product.sku}
          </small>
        </div>
        <span className="product-sticky-bar__price">
          {formatMoney(product.price)}
          <small>/ {saleUnitLabel(product.sale_unit)}</small>
        </span>
        <div className="product-sticky-bar__actions">
          <button
            className="button button--primary"
            onClick={() => (inCart ? openCart() : addToCart(product))}
            type="button"
          >
            {inCart ? "У кошику" : "У кошик"}
          </button>
          <LeadAction
            className="button button--outline"
            label="Купити в 1 клік"
            productId={product.id}
            type="quick_buy"
          />
        </div>
      </div>
    </div>
  );
}
