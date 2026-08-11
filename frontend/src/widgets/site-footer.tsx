import { Link } from "react-router-dom";

import { LeadAction } from "@/modules/leads/components/lead-action";
import { Logo } from "@/shared/ui/logo";

export function SiteFooter() {
  return (
    <footer className="site-footer">
      <div className="container site-footer__grid">
        <div className="site-footer__brand">
          <Logo inverse />
          <p>
            Практичний каталог електротоварів з прозорою наявністю та точним
            серверним розрахунком замовлення.
          </p>
          <LeadAction
            className="button button--light"
            label="Гуртовий запит"
            type="wholesale"
          />
        </div>
        <div>
          <h3>Каталог</h3>
          <Link to="/catalog">Усі товари</Link>
          <Link to="/catalog?sort=popular">Популярне</Link>
          <Link to="/catalog?in_stock=true">В наявності</Link>
        </div>
        <div>
          <h3>Покупцю</h3>
          <Link to="/checkout">Оформлення</Link>
          <Link to="/favorites">Обране</Link>
          <Link to="/compare">Порівняння</Link>
        </div>
        <div>
          <h3>Зв’язок</h3>
          <span>Залиште номер, і менеджер зв’яжеться з вами.</span>
          <LeadAction label="Замовити дзвінок" type="callback" />
        </div>
      </div>
      <div className="container site-footer__bottom">
        <span>© {new Date().getFullYear()} IZI HATA</span>
        <div>
          <span>Ціни в замовленні підтверджує сервер.</span>
          <Link to="/admin/login">Адмін-панель</Link>
        </div>
      </div>
    </footer>
  );
}
