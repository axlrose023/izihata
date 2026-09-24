import { useId, useState } from "react";
import type { ReactNode } from "react";

export interface ProductTab {
  id: string;
  label: string;
  content: ReactNode;
}

/**
 * Вкладки на сторінці товару (артборд Product). Усі панелі лишаються в DOM —
 * приховані отримують `hidden`, тож вміст доступний пошуку й не перезбирається
 * при кожному переході.
 */
export function ProductTabs({ tabs }: { tabs: ProductTab[] }) {
  const [active, setActive] = useState(tabs[0]?.id);
  const base = useId();
  if (!tabs.length) return null;

  return (
    <div className="product-tabs">
      <div aria-label="Розділи товару" className="product-tabs__list" role="tablist">
        {tabs.map((tab) => (
          <button
            aria-controls={`${base}-${tab.id}-panel`}
            aria-selected={tab.id === active}
            id={`${base}-${tab.id}-tab`}
            key={tab.id}
            onClick={() => setActive(tab.id)}
            role="tab"
            type="button"
          >
            {tab.label}
          </button>
        ))}
      </div>
      {tabs.map((tab) => (
        <div
          aria-labelledby={`${base}-${tab.id}-tab`}
          hidden={tab.id !== active}
          id={`${base}-${tab.id}-panel`}
          key={tab.id}
          role="tabpanel"
          tabIndex={0}
        >
          {tab.content}
        </div>
      ))}
    </div>
  );
}
