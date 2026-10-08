import { ArrowUpRight, Phone } from "lucide-react";
import type { ReactNode } from "react";
import { Link, NavLink } from "react-router-dom";

import { LeadAction } from "@/modules/leads/components/lead-action";
import { storeInfo } from "@/shared/config/store-info";
import { storePolicyPages } from "@/shared/config/store-policy-pages";
import { usePageMeta } from "@/shared/lib/use-page-meta";

type PolicyPage = (typeof storePolicyPages)[keyof typeof storePolicyPages];

function PolicyLayout({
  page,
  children,
}: {
  page: PolicyPage;
  children: ReactNode;
}) {
  usePageMeta({ title: page.title, description: page.description });

  return (
    <div className="container policy-page">
      <nav aria-label="Навігаційний ланцюжок" className="breadcrumbs">
        <Link to="/">Головна</Link>
        <span aria-hidden="true">/</span>
        <span aria-current="page">{page.title}</span>
      </nav>
      <header className="policy-page__heading">
        <span className="eyebrow">Інформація для покупця</span>
        <h1>{page.title}</h1>
        <p>{page.description}</p>
      </header>
      <div className="policy-page__layout">
        <aside className="policy-page__sidebar">
          <nav
            aria-label="Інформація для покупця"
            className="policy-navigation"
          >
            {Object.values(storePolicyPages).map((item) => (
              <NavLink end key={item.path} to={item.path}>
                <span>{item.title}</span>
                <ArrowUpRight aria-hidden="true" size={18} />
              </NavLink>
            ))}
          </nav>
        </aside>
        <article className="policy-content">
          {children}
          <section
            className="policy-contact"
            aria-labelledby="policy-contact-heading"
          >
            <h2 id="policy-contact-heading">Потрібна допомога?</h2>
            <p>Зв’яжіться з нами щодо замовлення, доставки або повернення.</p>
            <a href={storeInfo.phone.href}>
              <Phone aria-hidden="true" size={17} /> {storeInfo.phone.label}
            </a>
            <span>{storeInfo.schedule}</span>
            <LeadAction
              className="button button--outline button--wide"
              label="Зв’язатися з менеджером"
              type="callback"
            />
          </section>
        </article>
      </div>
    </div>
  );
}

function PolicySection({
  id,
  title,
  children,
}: {
  id: string;
  title: string;
  children: ReactNode;
}) {
  return (
    <section aria-labelledby={id}>
      <h2 id={id}>{title}</h2>
      {children}
    </section>
  );
}

export function DeliveryPaymentPage() {
  return (
    <PolicyLayout page={storePolicyPages.delivery}>
      <PolicySection id="delivery" title="Доставка">
        <h3>Нова пошта</h3>
        <p>
          Відправляємо замовлення Україною: у відділення, поштомати або
          кур’єром. Вартість перевезення визначається тарифами Нової пошти.
        </p>
        <h3>Кур’єрська доставка Києвом</h3>
        <p>Можливість, вартість і час доставки погодьте з менеджером.</p>
        <h3>Самовивіз</h3>
        <p>
          Забрати замовлення можна з пункту видачі: {storeInfo.address}. Перед
          поїздкою узгодьте готовність замовлення та місце отримання.
        </p>
        <p className="policy-note">Графік роботи: {storeInfo.schedule}.</p>
      </PolicySection>
      <PolicySection id="payment" title="Оплата">
        <h3>Безготівковий розрахунок</h3>
        <p>
          Оплата за рахунком для фізичних осіб, ФОП і юридичних осіб. Компанія є
          платником ПДВ на загальних підставах. Для виставлення рахунку вкажіть
          реквізити під час оформлення замовлення.
        </p>
        <h3>Оплата під час отримання</h3>
        <p>
          Розрахунок у пункті видачі або післяплата. Доступність способу та
          комісію перевізника погодьте перед відправленням.
        </p>
        <h3>Оплата онлайн</h3>
        <p>
          Через LiqPay: Visa, Mastercard, Google Pay та Apple Pay. Оплата
          здійснюється після підтвердження замовлення.
        </p>
      </PolicySection>
    </PolicyLayout>
  );
}

export function WarrantyReturnPage() {
  return (
    <PolicyLayout page={storePolicyPages.warranty}>
      <PolicySection id="warranty" title="Гарантійні умови">
        <p>
          Діє гарантія виробника. Звертайтеся до офіційного сервісного центру в
          Україні або до IZI HATA.
        </p>
        <h3>Підстави для відмови в гарантійному ремонті</h3>
        <ul>
          <li>Пошкоджені гарантійні пломби.</li>
          <li>Наявні пошкодження через зовнішній вплив.</li>
          <li>Порушено вимоги інструкції.</li>
          <li>Товар самовільно розбирали, ремонтували або змінювали.</li>
          <li>Немає підтвердження придбання.</li>
          <li>
            Неможливо ідентифікувати серійний номер, якщо він передбачений.
          </li>
        </ul>
        <h3>На що гарантія не поширюється</h3>
        <p>На пошкодження від неналежного використання або експлуатації.</p>
      </PolicySection>
      <PolicySection id="returns" title="Повернення товару та коштів">
        <p>
          Відповідно до Закону України «Про захист прав споживачів» фізичні
          особи можуть повернути або обміняти придбаний товар протягом 14 днів,
          не враховуючи день покупки. Ця умова не поширюється на юридичних осіб.
        </p>
        <h3>Повернення товару належної якості</h3>
        <p>
          Повернення можливе, якщо товар не підійшов за формою, розміром,
          габаритами, кольором, фасоном або з інших причин не може
          використовуватися за призначенням, за таких умов:
        </p>
        <ul>
          <li>
            Товар не був у користуванні та не має пошкоджень; збережені його
            товарний вигляд, споживчі властивості, упаковка, пломби та ярлики.
          </li>
          <li>Товар повертається в повній комплектації.</li>
          <li>
            Додано копію видаткової накладної або іншого розрахункового
            документа та заповнену заяву на повернення.
          </li>
          <li>
            Додано супровідні документи до товару, якщо вони були: паспорт,
            декларацію відповідності, інструкцію тощо.
          </li>
        </ul>
        <h3>Особливості повернення окремих товарів</h3>
        <p>
          Для товарів належної якості можливість повернення залежить від
          товарної категорії та вимог законодавства. Зокрема, це стосується:
        </p>
        <ul>
          <li>
            Кабельно-провідникової продукції, відрізаної або нарізаної під
            розмір.
          </li>
          <li>Витратних матеріалів.</li>
          <li>Труб, зокрема для прокладання кабелю, та металорукава.</li>
          <li>Товар, виготовлений або привезений під замовлення.</li>
          <li>
            Товар з індивідуальними характеристиками, обраними на прохання
            покупця, якщо його параметри відрізняються від зазначених на сайті.
          </li>
        </ul>
        <p>
          Обмеження застосовуються у випадках, передбачених законодавством, і не
          скасовують прав покупця щодо товару з недоліками. Повний перелік
          товарів, які не підлягають поверненню, визначає Кабінет Міністрів
          України.
        </p>
        <h3>Як оформити повернення або обмін</h3>
        <ol>
          <li>Заповніть заяву на повернення.</li>
          <li>
            Передайте товар разом із документами: надішліть поштою або принесіть
            до пункту видачі.
          </li>
          <li>
            Після отримання та перевірки товару повернемо кошти або надамо товар
            на заміну. Обробка звернення займає до 30 календарних днів; якщо
            законодавством для конкретного випадку встановлено коротший строк,
            діє коротший строк.
          </li>
        </ol>
        <p>
          Кошти повертаємо банківським переказом на рахунок покупця. Доставку
          товару належної якості до продавця оплачує покупець; ця сума не
          компенсується.
        </p>
      </PolicySection>
      <PolicySection id="warranty-claims" title="Гарантійні випадки">
        <p>
          Якщо протягом гарантійного строку в товарі виявлено недоліки,
          зверніться до продавця з вимогами, передбаченими Законом України «Про
          захист прав споживачів». Для розгляду звернення надайте документи,
          передбачені чинним законодавством.
        </p>
        <p>
          Строк безоплатного усунення недоліків починається з дня, коли товар
          фізично надійшов до продавця.
        </p>
        <p>
          Гарантійні вимоги не поширюються на недоліки, що виникли після
          передання товару через порушення правил експлуатації чи зберігання,
          дії третіх осіб або обставини непереборної сили.
        </p>
      </PolicySection>
      <PolicySection id="payment-refunds" title="Повернення онлайн-платежів">
        <p>
          Повідомте менеджеру номер замовлення та дані платежу. За потреби
          уточнимо реквізити для повернення.
        </p>
        <LeadAction
          className="button button--primary"
          label="Обговорити повернення"
          type="callback"
        />
      </PolicySection>
    </PolicyLayout>
  );
}

export function TermsOfUsePage() {
  return (
    <PolicyLayout page={storePolicyPages.terms}>
      <PolicySection id="general" title="Загальні умови">
        <p>
          Ці умови описують користування сайтом izihata.com.ua, кабінетом і
          формами замовлення. Користуйтеся сайтом законно та надавайте
          достовірну інформацію. Актуальна редакція розміщена на цій сторінці;
          зміни не скасовують уже погоджених умов замовлення.
        </p>
      </PolicySection>
      <PolicySection id="contact" title="Зв’язок із магазином">
        <p>
          Телефон: <a href={storeInfo.phone.href}>{storeInfo.phone.label}</a>.
          Безкоштовно з будь-яких телефонів України. Також можна замовити
          дзвінок через форму на сайті.
        </p>
        <p>Адреса пункту видачі: {storeInfo.address}.</p>
        <p>Графік роботи: {storeInfo.schedule}.</p>
        <p>
          Загальні питання:{" "}
          <a href={`mailto:${storeInfo.email.support}`}>
            {storeInfo.email.support}
          </a>
          . Пропозиції постачальників:{" "}
          <a href={`mailto:${storeInfo.email.partners}`}>
            {storeInfo.email.partners}
          </a>
          .
        </p>
      </PolicySection>
      <PolicySection id="prices" title="Ціни та наявність товарів">
        <p>
          Каталог оновлюється. Перед оплатою погоджуємо наявність, склад і суму
          замовлення. Зміни або заміну товару узгоджуємо з покупцем.
        </p>
      </PolicySection>
      <PolicySection id="ordering" title="Оформлення замовлення">
        <ol>
          <li>Додайте товари в кошик і перевірте кількість.</li>
          <li>
            Вкажіть контакти, доставку, оплату й реквізити компанії за потреби.
          </li>
          <li>Ознайомтеся з умовами та підтвердьте замовлення.</li>
        </ol>
        <p>
          Оформлення доступне з кабінетом або без реєстрації. Прийняття
          замовлення до виконання підтверджує магазин.
        </p>
      </PolicySection>
      <PolicySection id="terms-delivery" title="Доставка товару">
        <p>
          <Link to={storePolicyPages.delivery.path}>
            Способи доставки та оплати
          </Link>
          .
        </p>
      </PolicySection>
      <PolicySection id="terms-returns" title="Повернення товару">
        <p>
          <Link to={storePolicyPages.warranty.path}>
            Гарантійне обслуговування, обмін і повернення коштів
          </Link>
          .
        </p>
      </PolicySection>
      <PolicySection
        id="personal-data"
        title="Конфіденційність і захист персональних даних"
      >
        <p>
          Контакти та реквізити використовуємо для кабінету, обробки звернень і
          виконання замовлень. Необхідні дані передаємо перевізникам і платіжним
          сервісам для обраних вами послуг та у випадках, визначених законом.
          Для уточнення або зміни даних зверніться до нас.
        </p>
      </PolicySection>
      <PolicySection
        id="browser-storage"
        title="Cookies і збереження даних у браузері"
      >
        <p>
          Сайт зберігає кошик, обране, порівняння та дані сесії у браузері. Ви
          можете очистити або обмежити збереження в його налаштуваннях; тоді ці
          функції можуть працювати інакше.
        </p>
      </PolicySection>
      <PolicySection id="final" title="Прикінцеві положення">
        <p>
          Застосовується законодавство України. Звернення розглядаємо через
          менеджера. Ці умови не обмежують законних прав споживача.
        </p>
      </PolicySection>
    </PolicyLayout>
  );
}
