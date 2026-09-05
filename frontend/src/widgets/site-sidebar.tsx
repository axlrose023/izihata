import { useQuery } from "@tanstack/react-query";
import {
  ChevronLeft,
  ChevronRight,
  GitCompareArrows,
  Heart,
  LayoutGrid,
  MessageCircle,
  PackageCheck,
  PanelsTopLeft,
  Percent,
  Phone,
  ShoppingCart,
  Sparkles,
  Tags,
  UserRound,
  X,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { cartCount, useCartStore } from "@/modules/cart/store";
import { categoriesQuery } from "@/modules/catalog/api/catalog-queries";
import { useCollectionStore } from "@/modules/collections/store";
import { useCustomerAuth } from "@/modules/customers/customer-auth-context";
import { LeadAction } from "@/modules/leads/components/lead-action";
import { storeInfo } from "@/shared/config/store-info";
import { CategoryIcon } from "@/shared/ui/category-icon";
import { Logo } from "@/shared/ui/logo";

const shortcuts = [
  { to: "/catalog/sale", label: "Акції та знижки", icon: Percent },
  { to: "/catalog/new", label: "Новинки", icon: Sparkles },
  { to: "/brands", label: "Виробники", icon: Tags },
  { to: "/catalog?in_stock=true", label: "В наявності", icon: PackageCheck },
  { to: "/advisors", label: "Підбір товарів", icon: LayoutGrid },
  { to: "/custom-boards", label: "Щити", icon: PanelsTopLeft },
];

export function SiteSidebar({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const [showCatalog, setShowCatalog] = useState(false);
  const categories = useQuery(categoriesQuery()).data ?? [];
  const lines = useCartStore((state) => state.lines);
  const openCart = useCartStore((state) => state.open);
  const favoriteCount = useCollectionStore((state) => state.favorites.length);
  const compareCount = useCollectionStore((state) => state.compare.length);
  const { status } = useCustomerAuth();
  const authenticated = status === "authenticated";

  // The menu always reopens at the top level, so closing resets the drill-down.
  const close = useCallback(() => {
    setShowCatalog(false);
    onClose();
  }, [onClose]);

  useEffect(() => {
    if (!open) return;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") close();
    };
    document.addEventListener("keydown", closeOnEscape);
    return () => document.removeEventListener("keydown", closeOnEscape);
  }, [close, open]);

  if (!open) return null;

  return (
    <div className="site-sidebar" data-open>
      <button
        aria-label="Закрити меню"
        className="site-sidebar__backdrop"
        onClick={close}
        type="button"
      />
      <aside aria-label="Головне меню" className="site-sidebar__panel">
        <div className="site-sidebar__head">
          <Logo />
          <button
            aria-label="Закрити меню"
            className="icon-button"
            onClick={close}
            type="button"
          >
            <X size={20} />
          </button>
        </div>

        {showCatalog ? (
          <>
            <button
              className="site-sidebar__back"
              onClick={() => setShowCatalog(false)}
              type="button"
            >
              <ChevronLeft size={18} /> Каталог товарів
            </button>
            <nav className="site-sidebar__categories">
              <Link onClick={close} to="/catalog">
                <LayoutGrid size={19} />
                <span>Усі товари</span>
              </Link>
              {categories.map((category) => (
                <Link
                  key={category.id}
                  onClick={close}
                  to={`/catalog/${category.slug}`}
                >
                  <CategoryIcon size={19} slug={category.slug} />
                  <span>{category.name}</span>
                  <small>{category.product_count}</small>
                </Link>
              ))}
            </nav>
          </>
        ) : (
          <>
            <Link
              className="site-sidebar__auth"
              onClick={close}
              to={authenticated ? "/account" : "/account/login"}
            >
              <UserRound size={22} />
              <span>
                <strong>
                  {authenticated ? "Особистий кабінет" : "Увійти"}
                </strong>
                <small>
                  {authenticated
                    ? "Замовлення, компанія та гуртові умови"
                    : "Авторизуйтесь, щоб бачити історію замовлень"}
                </small>
              </span>
            </Link>

            <button
              aria-expanded={false}
              className="site-sidebar__catalog"
              onClick={() => setShowCatalog(true)}
              type="button"
            >
              <LayoutGrid size={20} />
              <span>Каталог товарів</span>
              <ChevronRight size={18} />
            </button>

            <div className="site-sidebar__section">
              <nav className="site-sidebar__links">
                {shortcuts.map(({ to, label, icon: Icon }) => (
                  <Link key={label} onClick={close} to={to}>
                    <Icon size={18} /> {label}
                  </Link>
                ))}
              </nav>
            </div>

            <div className="site-sidebar__section">
              <nav className="site-sidebar__links">
                <button
                  onClick={() => {
                    close();
                    openCart();
                  }}
                  type="button"
                >
                  <ShoppingCart size={18} /> Кошик
                  {lines.length ? <b>{cartCount(lines)}</b> : null}
                </button>
                <Link onClick={close} to="/favorites">
                  <Heart size={18} /> Обране
                  {favoriteCount ? <b>{favoriteCount}</b> : null}
                </Link>
                <Link onClick={close} to="/compare">
                  <GitCompareArrows size={18} /> Порівняння
                  {compareCount ? <b>{compareCount}</b> : null}
                </Link>
              </nav>
            </div>

            <div className="site-sidebar__contacts">
              <a href={storeInfo.phone.href}>
                <Phone size={15} /> {storeInfo.phone.label}
              </a>
              <span>
                <MessageCircle size={15} /> {storeInfo.messengers}
              </span>
              <span>{storeInfo.schedule}</span>
              <LeadAction
                className="button button--primary button--wide"
                label="Замовити дзвінок"
                type="callback"
              />
            </div>
          </>
        )}
      </aside>
    </div>
  );
}
