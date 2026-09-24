import { Check, Phone } from "lucide-react";

import { storeInfo } from "@/shared/config/store-info";
import { Logo } from "@/shared/ui/logo";

export function CheckoutHeader({ complete = false }: { complete?: boolean }) {
  const steps = ["Кошик", "Оформлення", "Готово"];

  return (
    <header className="checkout-header">
      <div className="container checkout-header__inner">
        <Logo inverse />
        <ol aria-label="Етапи оформлення" className="checkout-progress">
          {steps.map((step, index) => {
            const active = complete ? index === 2 : index === 1;
            const done = complete ? index < 2 : index === 0;
            return (
              <li
                className={active ? "is-active" : done ? "is-done" : undefined}
                key={step}
              >
                <span>{done ? <Check size={11} /> : index + 1}</span>
                {step}
              </li>
            );
          })}
        </ol>
        <a className="checkout-header__phone" href={storeInfo.phone.href}>
          <Phone size={15} />
          {storeInfo.phone.label}
        </a>
      </div>
    </header>
  );
}
