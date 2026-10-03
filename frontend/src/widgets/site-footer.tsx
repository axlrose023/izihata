import { Link } from "react-router-dom";
import { MapPin, MessageCircle, Phone } from "lucide-react";

import { LeadAction } from "@/modules/leads/components/lead-action";
import { Logo } from "@/shared/ui/logo";
import { storeInfo } from "@/shared/config/store-info";
import { storePolicyPages } from "@/shared/config/store-policy-pages";

export function SiteFooter() {
  return (
    <footer className="site-footer">
      <div className="container site-footer__grid">
        <div className="site-footer__brand">
          <Logo inverse />
          <p>
            Електротовари для дому, монтажу й бізнесу. Допоможемо підібрати
            обладнання та узгодити умови замовлення.
          </p>
          <LeadAction
            className="button button--light"
            label="Гуртовий запит"
            type="wholesale"
          />
        </div>
        <div>
          <h3>Допомога</h3>
          <Link to={storePolicyPages.delivery.path}>
            {storePolicyPages.delivery.title}
          </Link>
          <Link to={storePolicyPages.warranty.path}>
            {storePolicyPages.warranty.title}
          </Link>
          <LeadAction label="Потрібна консультація?" type="callback" />
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
          <Link to="/advisors">Калькулятори</Link>
          <Link to="/custom-boards">Щити на замовлення</Link>
          <Link to="/account">Особистий кабінет</Link>
          <Link to="/favorites">Обране</Link>
          <Link to="/compare">Порівняння</Link>
        </div>
        <div>
          <h3>Зв’язок</h3>
          <a href={storeInfo.phone.href}>
            <Phone size={14} /> {storeInfo.phone.label}
          </a>
          <span>
            <MessageCircle size={14} /> {storeInfo.messengers}
          </span>
          <span>
            <MapPin size={14} /> {storeInfo.address}
          </span>
          <LeadAction label="Замовити дзвінок" type="callback" />
        </div>
      </div>
      <div className="container site-footer__bottom">
        <span>© {new Date().getFullYear()} IZI HATA</span>
        <div>
          <Link to={storePolicyPages.terms.path}>
            {storePolicyPages.terms.title}
          </Link>
          <Link to="/admin/login">Адмін-панель</Link>
        </div>
      </div>
    </footer>
  );
}
