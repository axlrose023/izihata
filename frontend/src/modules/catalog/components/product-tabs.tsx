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
interface ProductTabsProps {
  tabs: ProductTab[];
  activeTab?: string;
  onActiveTabChange?: (tabId: string) => void;
}

export function ProductTabs({
  tabs,
  activeTab,
  onActiveTabChange,
}: ProductTabsProps) {
  const [uncontrolledActive, setUncontrolledActive] = useState(tabs[0]?.id);
  const active = activeTab ?? uncontrolledActive;
  const base = useId();
  if (!tabs.length) return null;

  const activate = (tabId: string) => {
    setUncontrolledActive(tabId);
    onActiveTabChange?.(tabId);
  };

  return (
    <div className="product-tabs">
      <div
        aria-label="Розділи товару"
        className="product-tabs__list"
        role="tablist"
      >
        {tabs.map((tab) => (
          <button
            aria-controls={`${base}-${tab.id}-panel`}
            aria-selected={tab.id === active}
            id={`${base}-${tab.id}-tab`}
            key={tab.id}
            onClick={() => activate(tab.id)}
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
