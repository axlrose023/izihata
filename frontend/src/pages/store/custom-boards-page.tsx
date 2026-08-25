import { useQuery } from "@tanstack/react-query";

import { boardPortfolioQuery } from "@/modules/custom-boards/api/custom-board-queries";
import { CustomBoardForm } from "@/modules/custom-boards/components/custom-board-form";
import { useDocumentTitle } from "@/shared/lib/use-document-title";
import { ErrorNotice } from "@/shared/ui/error-notice";

export function CustomBoardsPage() {
  const portfolioResult = useQuery(boardPortfolioQuery());
  useDocumentTitle("Щити на замовлення");

  return (
    <div className="container custom-boards-page">
      <header className="custom-boards-page__header">
        <span className="eyebrow">Щити на замовлення</span>
        <h1>Спроєктуємо та зберемо щит під ваш об’єкт</h1>
        <p>
          Заповніть базові параметри, отримайте орієнтир вартості та надішліть
          запит на точний розрахунок.
        </p>
      </header>
      <div className="custom-boards-page__layout">
        <CustomBoardForm />
        <aside>
          <span className="eyebrow">Як це працює</span>
          <ol>
            <li>Описуєте об’єкт і навантаження.</li>
            <li>Отримуєте стартову оцінку.</li>
            <li>Менеджер уточнює технічне завдання.</li>
            <li>Погоджуємо комплектацію та збираємо щит.</li>
          </ol>
        </aside>
      </div>
      {portfolioResult.isError ? (
        <ErrorNotice
          error={portfolioResult.error}
          fallback="Не вдалося завантажити приклади робіт."
          onRetry={() => void portfolioResult.refetch()}
        />
      ) : null}
      {portfolioResult.data?.length ? (
        <section className="custom-board-portfolio">
          <div className="section-heading">
            <div>
              <span className="eyebrow">Приклади робіт</span>
              <h2>Портфоліо</h2>
            </div>
          </div>
          <div className="custom-board-portfolio__grid">
            {portfolioResult.data.map((item) => (
              <article key={item.id}>
                <img alt={item.title} loading="lazy" src={item.image_url} />
                <div>
                  <h3>{item.title}</h3>
                  <p>{item.description}</p>
                </div>
              </article>
            ))}
          </div>
        </section>
      ) : null}
    </div>
  );
}
