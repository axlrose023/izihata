import {
  Calculator,
  ChevronDown,
  GitCompareArrows,
  Heart,
  House,
  LayoutGrid,
  Menu,
  MapPin,
  MessageCircle,
  PanelsTopLeft,
  Phone,
  ShoppingCart,
  UserRound,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { useState, type CSSProperties } from "react";
import { Link, useLocation } from "react-router-dom";

import { categoriesQuery } from "@/modules/catalog/api/catalog-queries";
import { cartCount, useCartStore } from "@/modules/cart/store";
import { preloadCartDrawer } from "@/modules/cart/components/load-cart-drawer";
import { ProductSearch } from "@/modules/catalog/components/product-search";
import { useCollectionStore } from "@/modules/collections/store";
import { LeadAction } from "@/modules/leads/components/lead-action";
import { useCustomerAuth } from "@/modules/customers/customer-auth-context";
import {
  formatMoney,
  pluralizePositions,
  pluralizeProducts,
} from "@/shared/lib/format";
import { CategoryIcon } from "@/shared/ui/category-icon";
import { Logo } from "@/shared/ui/logo";
import { storeInfo } from "@/shared/config/store-info";
import { SiteSidebar } from "./site-sidebar";

export function SiteHeader() {
  const [menuOpen, setMenuOpen] = useState(false);
  const [catalogMenuOpen, setCatalogMenuOpen] = useState(false);
  const lines = useCartStore((state) => state.lines);
  const openCart = useCartStore((state) => state.open);
  const favoriteCount = useCollectionStore((state) => state.favorites.length);
  const compareCount = useCollectionStore((state) => state.compare.length);
  const categoriesResult = useQuery(categoriesQuery());
  const categories = categoriesResult.data ?? [];
  const { status: customerStatus } = useCustomerAuth();
  const cartTotal = lines.reduce(
    (sum, line) => sum + Number(line.product.price) * line.quantity,
    0,
  );
  const { pathname } = useLocation();
  const isCatalogRoute =
    pathname === "/catalog" || pathname.startsWith("/catalog/");

  return (
    <header className="site-header" data-variant="store">
      <div className="top-strip">
        <div className="container top-strip__inner">
          <div>
            <span className="top-strip__address">
              <MapPin size={13} /> {storeInfo.address}
            </span>
            <a href={storeInfo.phone.href}>
              <Phone size={13} /> {storeInfo.phone.label}
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
        <Logo inverse />
        <ProductSearch key={pathname} />
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
            <span>Підбір</span>
          </Link>
          <Link
            aria-label={`Обране: ${favoriteCount}`}
            className="header-actions__favorites"
            to="/favorites"
          >
            <Heart />
            <span>Обране</span>
            {favoriteCount ? <b>{favoriteCount}</b> : null}
          </Link>
          <Link
            aria-label={`Порівняння: ${compareCount}`}
            className="header-actions__compare"
            to="/compare"
          >
            <GitCompareArrows />
            <span>Порівняння</span>
            {compareCount ? <b>{compareCount}</b> : null}
          </Link>
          <button
            aria-label={`Кошик: ${cartCount(lines)}`}
            className="header-cart"
            onClick={openCart}
            onFocus={preloadCartDrawer}
            onPointerEnter={preloadCartDrawer}
            onPointerDown={preloadCartDrawer}
            type="button"
          >
            <ShoppingCart />
            {lines.length ? (
              <span className="header-cart__summary">
                <span>{pluralizePositions(cartCount(lines))}</span>
                <strong>{formatMoney(cartTotal)}</strong>
              </span>
            ) : (
              <span className="header-cart__label">Кошик</span>
            )}
            {lines.length ? <b>{cartCount(lines)}</b> : null}
          </button>
        </div>
      </div>
      {menuOpen ? (
        <SiteSidebar
          categories={categories}
          onClose={() => setMenuOpen(false)}
          open
        />
      ) : null}
      <nav className="catalog-nav">
        <div className="container catalog-nav__inner">
          <div
            className="catalog-nav__all"
            onBlur={(event) => {
              if (
                !event.currentTarget.contains(
                  event.relatedTarget as Node | null,
                )
              ) {
                setCatalogMenuOpen(false);
              }
            }}
            onKeyDown={(event) => {
              if (event.key === "Escape") setCatalogMenuOpen(false);
            }}
            onMouseEnter={() => setCatalogMenuOpen(true)}
            onMouseLeave={() => setCatalogMenuOpen(false)}
          >
            <Link
              aria-controls={
                catalogMenuOpen ? "catalog-category-menu" : undefined
              }
              aria-expanded={catalogMenuOpen}
              className="catalog-nav__primary"
              onClick={() => setCatalogMenuOpen(false)}
              onFocus={() => setCatalogMenuOpen(true)}
              to="/catalog"
            >
              <Menu size={18} /> Усі товари <ChevronDown size={14} />
            </Link>
            {catalogMenuOpen ? (
              <nav
                aria-label="Категорії товарів"
                className="catalog-mega-menu"
                id="catalog-category-menu"
              >
                <div className="catalog-mega-menu__panel">
                  <div className="catalog-mega-menu__head">
                    <strong>Категорії каталогу</strong>
                    <Link
                      onClick={() => setCatalogMenuOpen(false)}
                      to="/catalog"
                    >
                      Переглянути всі товари <span aria-hidden="true">→</span>
                    </Link>
                  </div>
                  {categoriesResult.isPending ? (
                    <p className="catalog-mega-menu__state" role="status">
                      Завантажуємо категорії…
                    </p>
                  ) : categoriesResult.isError ? (
                    <p className="catalog-mega-menu__state" role="status">
                      Не вдалося завантажити категорії.
                    </p>
                  ) : (
                    <div className="catalog-mega-menu__grid">
                      {categories.map((category) => (
                        <Link
                          className="catalog-mega-menu__category"
                          key={category.id}
                          onClick={() => setCatalogMenuOpen(false)}
                          style={
                            {
                              "--category-accent": category.accent,
                            } as CSSProperties
                          }
                          to={`/catalog/${category.slug}`}
                        >
                          <CategoryIcon size={23} slug={category.slug} />
                          <span>
                            <strong>{category.name}</strong>
                            <small>
                              {pluralizeProducts(category.product_count)}
                            </small>
                          </span>
                        </Link>
                      ))}
                    </div>
                  )}
                </div>
              </nav>
            ) : null}
          </div>
          <Link to="/catalog?sort=popular">Популярне</Link>
          <Link to="/catalog/new">Новинки</Link>
          <Link className="catalog-nav__sale" to="/catalog/sale">
            Акції
          </Link>
          <Link to="/catalog?in_stock=true">В наявності</Link>
          <Link to="/advisors">Підбір товарів</Link>
          <Link to="/custom-boards">
            <PanelsTopLeft size={17} /> Щити
          </Link>
          <LeadAction
            className="nav-callback"
            label="Замовити дзвінок"
            type="callback"
          />
          <Link className="nav-b2b" to="/account">
            Для бізнесу · B2B
          </Link>
        </div>
      </nav>
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
          onFocus={preloadCartDrawer}
          onPointerEnter={preloadCartDrawer}
          onPointerDown={preloadCartDrawer}
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
