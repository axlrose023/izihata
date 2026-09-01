import {
  Calculator,
  GitCompareArrows,
  Heart,
  House,
  LayoutGrid,
  Menu,
  MessageCircle,
  PanelsTopLeft,
  Phone,
  ShoppingCart,
  UserRound,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useLocation } from "react-router-dom";

import { SiteSidebar } from "./site-sidebar";

import { cartCount, useCartStore } from "@/modules/cart/store";
import { ProductSearch } from "@/modules/catalog/components/product-search";
import { categoriesQuery } from "@/modules/catalog/api/catalog-queries";
import { useCollectionStore } from "@/modules/collections/store";
import { LeadAction } from "@/modules/leads/components/lead-action";
import { useCustomerAuth } from "@/modules/customers/customer-auth-context";
import { Logo } from "@/shared/ui/logo";
import { storeInfo } from "@/shared/config/store-info";

export function SiteHeader() {
  const [menuOpen, setMenuOpen] = useState(false);
  const lines = useCartStore((state) => state.lines);
  const openCart = useCartStore((state) => state.open);
  const favoriteCount = useCollectionStore((state) => state.favorites.length);
  const compareCount = useCollectionStore((state) => state.compare.length);
  const categories = useQuery(categoriesQuery()).data ?? [];
  const { status: customerStatus } = useCustomerAuth();
  const { pathname } = useLocation();
  const isCatalogRoute =
    pathname === "/catalog" || pathname.startsWith("/catalog/");

  return (
    <header className="site-header">
      <div className="top-strip">
        <div className="container top-strip__inner">
          <div>
            <a href={storeInfo.phone.href}>
              <Phone size={13} /> {storeInfo.phone.label} — безкоштовно
            </a>
            <span>
              <MessageCircle size={13} /> {storeInfo.messengers}
            </span>
          </div>
          <span>{storeInfo.schedule}</span>
        </div>
      </div>
      <div className="container header-main">
        <button
          aria-expanded={menuOpen}
          aria-label="Відкрити меню"
          className="menu-button"
          onClick={() => setMenuOpen(true)}
          type="button"
        >
          <Menu size={20} />
          <span>Меню</span>
        </button>
        <Logo />
        <ProductSearch />
        <div className="header-actions">
          <Link
            aria-label={
              customerStatus === "authenticated"
                ? "Особистий кабінет"
                : "Увійти до кабінету"
            }
            className="header-actions__account"
            to={
              customerStatus === "authenticated" ? "/account" : "/account/login"
            }
          >
            <UserRound />
            <span>
              {customerStatus === "authenticated" ? "Кабінет" : "Увійти"}
            </span>
          </Link>
          <Link
            aria-label="Підбір товарів і калькулятори"
            className="header-actions__advisors"
            title="Підбір товарів"
            to="/advisors"
          >
            <Calculator />
          </Link>
          <Link
            aria-label={`Обране: ${favoriteCount}`}
            className="header-actions__favorites"
            to="/favorites"
          >
            <Heart />
            {favoriteCount ? <b>{favoriteCount}</b> : null}
          </Link>
          <Link
            aria-label={`Порівняння: ${compareCount}`}
            className="header-actions__compare"
            to="/compare"
          >
            <GitCompareArrows />
            {compareCount ? <b>{compareCount}</b> : null}
          </Link>
          <button
            aria-label={`Кошик: ${cartCount(lines)}`}
            onClick={openCart}
            type="button"
          >
            <ShoppingCart />
            {lines.length ? <b>{cartCount(lines)}</b> : null}
          </button>
        </div>
      </div>
      <SiteSidebar onClose={() => setMenuOpen(false)} open={menuOpen} />
      <nav className="catalog-nav">
        <div className="container catalog-nav__inner">
          <Link className="catalog-nav__primary" to="/catalog">
            <Menu size={18} /> Усі товари
          </Link>
          <Link to="/catalog?sort=popular">Популярне</Link>
          <Link to="/catalog?sort=newest">Новинки</Link>
          <Link to="/catalog?in_stock=true">В наявності</Link>
          <Link to="/advisors">Підбір товарів</Link>
          <Link to="/custom-boards">
            <PanelsTopLeft size={17} /> Щити
          </Link>
          <Link to="/account">Для бізнесу</Link>
          <LeadAction
            className="nav-callback"
            label="Замовити дзвінок"
            type="callback"
          />
        </div>
      </nav>
      {categories.length ? (
        <nav aria-label="Категорії товарів" className="category-quick-nav">
          <div className="container">
            {categories.map((category) => (
              <Link key={category.id} to={`/catalog/${category.slug}`}>
                {category.name}
              </Link>
            ))}
          </div>
        </nav>
      ) : null}
      <nav aria-label="Мобільна навігація" className="mobile-bottom-nav">
        <Link aria-current={pathname === "/" ? "page" : undefined} to="/">
          <House size={20} />
          <span>Головна</span>
        </Link>
        <Link aria-current={isCatalogRoute ? "page" : undefined} to="/catalog">
          <LayoutGrid size={20} />
          <span>Каталог</span>
        </Link>
        <Link
          aria-current={pathname === "/favorites" ? "page" : undefined}
          to="/favorites"
        >
          <Heart size={20} />
          <span>Обране</span>
          {favoriteCount ? <b>{favoriteCount}</b> : null}
        </Link>
        <Link
          aria-current={pathname.startsWith("/account") ? "page" : undefined}
          to="/account"
        >
          <UserRound size={20} />
          <span>Кабінет</span>
        </Link>
        <button
          aria-label={`Кошик: ${cartCount(lines)}`}
          onClick={openCart}
          type="button"
        >
          <ShoppingCart size={20} />
          <span>Кошик</span>
          {lines.length ? <b>{cartCount(lines)}</b> : null}
        </button>
      </nav>
    </header>
  );
}
