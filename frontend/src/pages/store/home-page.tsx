import { useQueries } from "@tanstack/react-query";
import { BadgeCheck, Calculator, CreditCard, Truck } from "lucide-react";
import { Link } from "react-router-dom";

import { PopularProducts } from "@/modules/catalog/components/popular-products";
import { SectionCards } from "@/modules/catalog/components/section-cards";
import {
  brandsQuery,
  categoriesQuery,
  sectionsQuery,
} from "@/modules/catalog/api/catalog-queries";
import { useDocumentTitle } from "@/shared/lib/use-document-title";

export function HomePage() {
  useDocumentTitle();
  const [sectionsResult, categoriesResult, brandsResult] = useQueries({
    queries: [sectionsQuery(), categoriesQuery(), brandsQuery()],
  });
  const sections = sectionsResult.data ?? [];
  const categories = categoriesResult.data ?? [];
  const brands = brandsResult.data ?? [];
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
            <h1>Все для щита, кабелю й освітлення</h1>
            <p>
              Фільтруйте за номіналом, перерізом, IP і брендом. Наявність і
              термін відправлення видно ще в каталозі.
            </p>
            <div className="hero__actions">
              <Link className="button button--primary" to="/catalog">
                Перейти в каталог
              </Link>
              <Link className="button button--outline" to="/advisors">
                Підібрати за параметрами
              </Link>
            </div>
            <dl className="hero__metrics">
              <div>
                <dt>[час]</dt>
                <dd>відправка того ж дня</dd>
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
            {sections.slice(0, 3).map((section, index) => (
              <div key={section.id}>
                <Link
                  className="hero__directory-heading"
                  to={`/sections/${section.slug}`}
                >
                  {["Монтаж", "Захист і керування", "Живлення й системи"][
                    index
                  ] ?? section.name}
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

      <section aria-label="Переваги оформлення" className="trust-strip">
        <div className="container trust-strip__grid">
          <div>
            <Truck />
            <p>
              <strong>Відправимо сьогодні</strong>
              <span>замовлення до [час відсічення]</span>
            </p>
          </div>
          <div>
            <Calculator />
            <p>
              <strong>Гуртові ціни</strong>
              <span>B2B-кабінет</span>
            </p>
          </div>
          <div>
            <BadgeCheck />
            <p>
              <strong>Паспорти й сертифікати</strong>
              <span>PDF у картці товару</span>
            </p>
          </div>
          <div>
            <CreditCard />
            <p>
              <strong>Картка, рахунок, післяплата</strong>
              <span>без комісії</span>
            </p>
          </div>
        </div>
      </section>

      <PopularProducts />

      <section className="container home-entry-points">
        <Link to="/advisors">
          <span className="eyebrow">Підбір за параметрами</span>
          <strong>Переріз, номінал, потужність</strong>
          <span>Знайдемо сумісні товари за розрахунком →</span>
        </Link>
        <Link to="/custom-boards">
          <span className="eyebrow">Щити на замовлення</span>
          <strong>Зберемо щит під ваш проєкт</strong>
          <span>Залиште специфікацію для прорахунку →</span>
        </Link>
      </section>
    </>
  );
}
