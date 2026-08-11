import {
  GitCompareArrows,
  Heart,
  House,
  LayoutGrid,
  Menu,
  ShoppingCart,
  X,
} from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

import { cartCount, useCartStore } from "@/modules/cart/store";
import { ProductSearch } from "@/modules/catalog/components/product-search";
import { useCollectionStore } from "@/modules/collections/store";
import { LeadAction } from "@/modules/leads/components/lead-action";
import { Logo } from "@/shared/ui/logo";

export function SiteHeader() {
  const [menuOpen, setMenuOpen] = useState(false);
  const lines = useCartStore((state) => state.lines);
  const openCart = useCartStore((state) => state.open);
  const favoriteCount = useCollectionStore((state) => state.favorites.length);
  const compareCount = useCollectionStore((state) => state.compare.length);

  return (
    <header className="site-header">
      <div className="top-strip">
        <div className="container top-strip__inner">
          <span>Електротовари для дому, монтажу й бізнесу</span>
          <span>Актуальна наявність і прозорий розрахунок</span>
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
          <LeadAction
            className="nav-callback"
            label="Замовити дзвінок"
            type="callback"
          />
        </div>
      </nav>
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
