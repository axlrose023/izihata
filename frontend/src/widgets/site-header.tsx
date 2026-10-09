import {
  Calculator,
  ChevronDown,
  ChevronRight,
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
import { useEffect, useRef, useState } from "react";
import { Link, useLocation } from "react-router-dom";

import { categoriesQuery } from "@/modules/catalog/api/catalog-queries";
import { cartCount, useCartStore } from "@/modules/cart/store";
import { preloadCartDrawer } from "@/modules/cart/components/load-cart-drawer";
import { ProductSearch } from "@/modules/catalog/components/product-search";
import { availableSubcategories } from "@/modules/catalog/lib/subcategory-order";
import { useCollectionStore } from "@/modules/collections/store";
import { LeadAction } from "@/modules/leads/components/lead-action";
import { useCustomerAuth } from "@/modules/customers/customer-auth-context";
import { formatMoney, pluralizePositions } from "@/shared/lib/format";
import { Logo } from "@/shared/ui/logo";
import type { Category } from "@/shared/types/api";
import { storeInfo } from "@/shared/config/store-info";
import { SiteSidebar } from "./site-sidebar";

export function SiteHeader() {
  const [menuOpen, setMenuOpen] = useState(false);
  const [catalogMenuOpen, setCatalogMenuOpen] = useState(false);
  const [catalogCategorySlug, setCatalogCategorySlug] = useState<string | null>(
    null,
  );
  const catalogMenuRef = useRef<HTMLDivElement>(null);
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
  const routeCategorySlug = pathname.match(/^\/catalog\/([^/]+)$/)?.[1];
  const routeCategory = categories.find(
    (category) => category.slug === routeCategorySlug,
  );
  const categoryWithMostSubcategories = categories.reduce<Category | undefined>(
    (best, category) =>
      !best ||
      availableSubcategories(category.slug, category.subcategories).length >
        availableSubcategories(best.slug, best.subcategories).length
        ? category
        : best,
    undefined,
  );
  const activeCategory =
    categories.find((category) => category.slug === catalogCategorySlug) ??
    routeCategory ??
    categoryWithMostSubcategories;
  const activeSubcategories = activeCategory
    ? availableSubcategories(activeCategory.slug, activeCategory.subcategories)
    : [];
  const openCatalogMenu = () => {
    setCatalogCategorySlug(
      routeCategory?.slug ?? categoryWithMostSubcategories?.slug ?? null,
    );
    setCatalogMenuOpen(true);
  };

  useEffect(() => {
    if (!catalogMenuOpen) return;

    const closeOnOutsideClick = (event: PointerEvent) => {
      if (!catalogMenuRef.current?.contains(event.target as Node)) {
        setCatalogMenuOpen(false);
      }
    };

    document.addEventListener("pointerdown", closeOnOutsideClick);
    return () =>
      document.removeEventListener("pointerdown", closeOnOutsideClick);
  }, [catalogMenuOpen]);

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
            ref={catalogMenuRef}
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
          >
            <button
              aria-controls={
                catalogMenuOpen ? "catalog-category-menu" : undefined
              }
              aria-expanded={catalogMenuOpen}
              className="catalog-nav__primary"
              onClick={() =>
                catalogMenuOpen ? setCatalogMenuOpen(false) : openCatalogMenu()
              }
              type="button"
            >
              <Menu size={18} /> Усі товари <ChevronDown size={14} />
            </button>
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
                    <div className="catalog-mega-menu__body">
                      <div
                        aria-label="Категорії каталогу"
                        className="catalog-mega-menu__roots"
                        role="group"
                      >
                        {categories.map((category) => (
                          <button
                            aria-pressed={
                              activeCategory?.slug === category.slug
                            }
                            className="catalog-mega-menu__root"
                            key={category.id}
                            onClick={() =>
                              setCatalogCategorySlug(category.slug)
                            }
                            onFocus={() =>
                              setCatalogCategorySlug(category.slug)
                            }
                            onMouseEnter={() =>
                              setCatalogCategorySlug(category.slug)
                            }
                            type="button"
                          >
                            <span>{category.name}</span>
                            <ChevronRight aria-hidden="true" size={15} />
                          </button>
                        ))}
                      </div>
                      <section
                        aria-label={`Підкатегорії ${activeCategory?.name ?? ""}`}
                        className="catalog-mega-menu__subcategories"
                      >
                        {activeCategory ? (
                          <>
                            <div className="catalog-mega-menu__subhead">
                              <strong>{activeCategory.name}</strong>
                              <Link
                                onClick={() => setCatalogMenuOpen(false)}
                                to={`/catalog/${activeCategory.slug}`}
                              >
                                Усі товари розділу{" "}
                                <span aria-hidden="true">→</span>
                              </Link>
                            </div>
                            {activeSubcategories.length ? (
                              <div className="catalog-mega-menu__subgrid">
                                {activeSubcategories.map((subcategory) => (
                                  <Link
                                    className="catalog-mega-menu__subcategory"
                                    key={subcategory.id}
                                    onClick={() => setCatalogMenuOpen(false)}
                                    to={`/catalog/${activeCategory.slug}?subcategory=${encodeURIComponent(subcategory.slug)}`}
                                  >
                                    {subcategory.name}
                                  </Link>
                                ))}
                              </div>
                            ) : (
                              <p className="catalog-mega-menu__state">
                                У цьому розділі поки немає підкатегорій.
                              </p>
                            )}
                          </>
                        ) : (
                          <p className="catalog-mega-menu__state">
                            Категорії поки недоступні.
                          </p>
                        )}
                      </section>
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
