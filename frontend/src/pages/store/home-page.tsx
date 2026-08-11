import { useQueries } from "@tanstack/react-query";
import {
  Calculator,
  PackageCheck,
  ShieldCheck,
  ShoppingBag,
  Truck,
} from "lucide-react";
import { Link } from "react-router-dom";

import { ProductCard } from "@/modules/catalog/components/product-card";
import {
  categoriesQuery,
  productsQuery,
} from "@/modules/catalog/api/catalog-queries";
import { LeadAction } from "@/modules/leads/components/lead-action";
import { useDocumentTitle } from "@/shared/lib/use-document-title";
import { CategoryIcon } from "@/shared/ui/category-icon";

export function HomePage() {
  useDocumentTitle();
  const [categoriesResult, productsResult] = useQueries({
    queries: [
      categoriesQuery(),
      productsQuery({ page_size: 8, sort: "popular" }),
    ],
  });
  const categories = categoriesResult.data ?? [];
  const products = productsResult.data;
  const unavailable = categoriesResult.isError || productsResult.isError;

  return (
    <>
      <section className="hero">
        <div className="container hero__grid">
          <div className="hero__content">
            <span className="hero__kicker">
              Інтернет-магазин електротоварів
            </span>
            <h1>
              Правильна деталь для вашої мережі — <em>без зайвих кроків</em>
            </h1>
            <p>
              Автоматика, кабель, освітлення та монтажні системи з фільтрами за
              реальними характеристиками й точним серверним розрахунком.
            </p>
            <div className="hero__actions">
              <Link className="button button--primary" to="/catalog">
                Перейти до каталогу
              </Link>
              <LeadAction label="Потрібна консультація" type="callback" />
            </div>
            <div className="hero__facts">
              <span>
                <ShieldCheck /> Актуальна наявність
              </span>
              <span>
                <Truck /> Нова пошта / самовивіз
              </span>
              <span>
                <Calculator /> Ціна рахується сервером
              </span>
            </div>
          </div>
          <div className="hero__visual" aria-hidden="true">
            <div className="hero-panel">
              <div className="hero-panel__rail" />
              <div className="hero-panel__modules">
                <span data-size="wide" />
                <span />
                <span data-accent />
                <span />
                <span data-size="wide" />
              </div>
              <div className="hero-panel__wires">
                <i />
                <i />
                <i />
              </div>
            </div>
            <div className="hero__label">
              <strong>{categories.length} напрямів</strong>
              <span>Від автоматики до зарядних станцій</span>
            </div>
          </div>
        </div>
      </section>

      {unavailable ? (
        <div className="container service-notice" role="status">
          Каталог тимчасово оновлюється. Спробуйте перезавантажити сторінку
          трохи пізніше.
        </div>
      ) : null}

      <section className="section container">
        <div className="section-heading">
          <div>
            <span className="eyebrow">Оберіть напрям</span>
            <h2>Категорії товарів</h2>
          </div>
          <Link to="/catalog">Дивитися все →</Link>
        </div>
        <div className="category-grid">
          {categories.slice(0, 8).map((category) => (
            <Link
              className="category-card"
              key={category.id}
              style={{ "--accent": category.accent } as React.CSSProperties}
              to={`/catalog/${category.slug}`}
            >
              <CategoryIcon size={38} slug={category.slug} />
              <strong>{category.name}</strong>
              <span>{category.product_count} товарів</span>
            </Link>
          ))}
        </div>
        <div className="all-categories">
          <div className="all-categories__heading">
            <strong>Усі категорії</strong>
            <span>{categories.length} напрямів</span>
          </div>
          <div className="all-categories__grid">
            {categories.map((category) => (
              <Link key={category.id} to={`/catalog/${category.slug}`}>
                <CategoryIcon size={22} slug={category.slug} />
                <span>{category.name}</span>
              </Link>
            ))}
          </div>
        </div>
      </section>

      <section aria-label="Переваги оформлення" className="trust-strip">
        <div className="container trust-strip__grid">
          <span>
            <PackageCheck /> Актуальна наявність
          </span>
          <span>
            <Calculator /> Серверний розрахунок
          </span>
          <span>
            <Truck /> Нова пошта або самовивіз
          </span>
          <span>
            <ShoppingBag /> Замовлення без реєстрації
          </span>
        </div>
      </section>

      <section className="section section--tint">
        <div className="container">
          <div className="section-heading">
            <div>
              <span className="eyebrow">Вибір покупців</span>
              <h2>Популярні товари</h2>
            </div>
            <Link to="/catalog?sort=popular">Увесь каталог →</Link>
          </div>
          <div className="product-grid">
            {products?.items.map((product) => (
              <ProductCard key={product.id} product={product} />
            ))}
          </div>
        </div>
      </section>

      {products?.facets.brands.length ? (
        <section className="section container brands-section">
          <div className="section-heading">
            <div>
              <span className="eyebrow">Перевірені виробники</span>
              <h2>Бренди в каталозі</h2>
            </div>
          </div>
          <div className="brand-list">
            {products.facets.brands.map((brand) => (
              <Link
                key={brand.value}
                to={`/catalog?brand=${encodeURIComponent(brand.value)}`}
              >
                <strong>{brand.value}</strong>
                <span>{brand.count} товарів</span>
              </Link>
            ))}
          </div>
        </section>
      ) : null}

      <section className="section section--tint ordering-steps">
        <div className="container">
          <div className="section-heading">
            <div>
              <span className="eyebrow">Без зайвих дій</span>
              <h2>Як оформити замовлення</h2>
            </div>
          </div>
          <div className="ordering-steps__grid">
            <article>
              <span>01</span>
              <strong>Знайдіть товар</strong>
              <p>
                Пошук, категорії та технічні фільтри працюють з одним каталогом.
              </p>
            </article>
            <article>
              <span>02</span>
              <strong>Перевірте розрахунок</strong>
              <p>Ціни, кількість і промокод повторно перевіряє backend.</p>
            </article>
            <article>
              <span>03</span>
              <strong>Оберіть отримання</strong>
              <p>
                Нова пошта, поштомат або самовивіз — без обов’язкової
                реєстрації.
              </p>
            </article>
          </div>
        </div>
      </section>

      <section className="container business-banner">
        <div>
          <span className="eyebrow">Для бізнесу</span>
          <h2>Комплектуєте об’єкт або виробництво?</h2>
          <p>
            Залиште реквізити — менеджер уточнить обсяг і підготує пропозицію.
          </p>
        </div>
        <LeadAction
          className="button button--light"
          label="Отримати пропозицію"
          type="wholesale"
        />
      </section>
    </>
  );
}
