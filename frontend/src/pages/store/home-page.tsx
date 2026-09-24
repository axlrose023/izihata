import { useQueries } from "@tanstack/react-query";
import { useState } from "react";
import { Calculator, PackageCheck, ShoppingBag, Truck } from "lucide-react";
import { Link } from "react-router-dom";

import { BrandRail } from "@/modules/catalog/components/brand-rail";
import { PopularProducts } from "@/modules/catalog/components/popular-products";
import { SectionCards } from "@/modules/catalog/components/section-cards";
import {
  brandsQuery,
  categoriesQuery,
  featuredReviewsQuery,
  sectionsQuery,
} from "@/modules/catalog/api/catalog-queries";
import { LeadAction } from "@/modules/leads/components/lead-action";
import { useDocumentTitle } from "@/shared/lib/use-document-title";
import { CategoryIcon } from "@/shared/ui/category-icon";
import { TestimonialsSection } from "@/modules/reviews/components/testimonials-section";
import { pluralizeProducts } from "@/shared/lib/format";

export function HomePage() {
  const [allCategoriesShown, setAllCategoriesShown] = useState(false);
  useDocumentTitle();
  const [sectionsResult, categoriesResult, reviewsResult, brandsResult] =
    useQueries({
      queries: [
        sectionsQuery(),
        categoriesQuery(),
        featuredReviewsQuery(),
        brandsQuery(),
      ],
    });
  const sections = sectionsResult.data ?? [];
  const categories = categoriesResult.data ?? [];
  const brands = brandsResult.data ?? [];
  const productTotal = sections.reduce(
    (sum, section) => sum + section.product_count,
    0,
  );
  const unavailable = sectionsResult.isError || categoriesResult.isError;

  return (
    <>
      <section className="hero">
        <div className="container hero__grid">
          <div className="hero__content">
            <span className="hero__kicker">
              {categories.length} категорій · {brands.length} брендів · склад у
              Києві
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
            <dl className="hero__metrics">
              <div>
                <dt>{productTotal.toLocaleString("uk-UA")}</dt>
                <dd>товарів у наявності</dd>
              </div>
              <div>
                <dt>{brands.length}</dt>
                <dd>брендів на складі</dd>
              </div>
              <div>
                <dt>B2B</dt>
                <dd>гуртові ціни</dd>
              </div>
            </dl>
          </div>
          <nav aria-label="Розділи каталогу" className="hero__directory">
            {sections.map((section) => (
              <div key={section.id}>
                <Link
                  className="hero__directory-heading"
                  to={`/sections/${section.slug}`}
                >
                  {section.name}
                </Link>
                <ul>
                  {section.categories.map((category) => (
                    <li key={category.id}>
                      <Link to={`/catalog/${category.slug}`}>
                        {category.name}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </nav>
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
            <h2>За чим підбираємо рішення</h2>
          </div>
          <Link to="/catalog">Дивитися все →</Link>
        </div>
        <SectionCards sections={sections} />
      </section>

      <section className="section container">
        <div className="section-heading">
          <div>
            <span className="eyebrow">Усі категорії</span>
            <h2>Каталог товарів</h2>
          </div>
          <Link to="/catalog">Дивитися все →</Link>
        </div>
        <div className="category-grid">
          {(allCategoriesShown ? categories : categories.slice(0, 5)).map(
            (category) => (
              <Link
                className="category-card"
                key={category.id}
                style={{ "--accent": category.accent } as React.CSSProperties}
                to={`/catalog/${category.slug}`}
              >
                <CategoryIcon size={38} slug={category.slug} />
                <strong>{category.name}</strong>
                <span>{pluralizeProducts(category.product_count)}</span>
              </Link>
            ),
          )}
        </div>
        {categories.length > 5 ? (
          <button
            aria-expanded={allCategoriesShown}
            className="show-all-button"
            onClick={() => setAllCategoriesShown((value) => !value)}
            type="button"
          >
            {allCategoriesShown
              ? "Згорнути"
              : `Показати всі напрями (${categories.length})`}
          </button>
        ) : null}
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

      <PopularProducts />

      <BrandRail />

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

      <TestimonialsSection reviews={reviewsResult.data ?? []} />

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
