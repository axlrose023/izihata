import {
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
  X,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";

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
          className="mobile-menu-button icon-button"
          onClick={() => setMenuOpen((value) => !value)}
          type="button"
        >
          {menuOpen ? <X /> : <Menu />}
        </button>
        <Logo />
        <ProductSearch />
        <div className="header-actions">
          <Link
            aria-label="Особистий кабінет"
            className="header-actions__account"
            to="/account"
          >
            <UserRound />
            {customerStatus === "authenticated" ? <b>Кабінет</b> : null}
          </Link>
          <Link aria-label={`Обране: ${favoriteCount}`} to="/favorites">
            <Heart />
            {favoriteCount ? <b>{favoriteCount}</b> : null}
          </Link>
          <Link aria-label={`Порівняння: ${compareCount}`} to="/compare">
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
      <nav className="catalog-nav" data-open={menuOpen || undefined}>
        <div className="container catalog-nav__inner">
          <Link
            className="catalog-nav__primary"
            to="/catalog"
            onClick={() => setMenuOpen(false)}
          >
            <Menu size={18} /> Усі товари
          </Link>
          <Link to="/catalog?sort=popular" onClick={() => setMenuOpen(false)}>
            Популярне
          </Link>
          <Link to="/catalog?sort=newest" onClick={() => setMenuOpen(false)}>
            Новинки
          </Link>
          <Link to="/catalog?in_stock=true" onClick={() => setMenuOpen(false)}>
            В наявності
          </Link>
          <Link to="/advisors" onClick={() => setMenuOpen(false)}>
            Підбір товарів
          </Link>
          <Link to="/custom-boards" onClick={() => setMenuOpen(false)}>
            <PanelsTopLeft size={17} /> Щити
          </Link>
          <Link to="/account" onClick={() => setMenuOpen(false)}>
            Для бізнесу
          </Link>
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
        <Link to="/">
          <House size={20} />
          <span>Головна</span>
        </Link>
        <Link to="/catalog">
          <LayoutGrid size={20} />
          <span>Каталог</span>
        </Link>
        <Link to="/favorites">
          <Heart size={20} />
          <span>Обране</span>
          {favoriteCount ? <b>{favoriteCount}</b> : null}
        </Link>
        <Link to="/account">
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
