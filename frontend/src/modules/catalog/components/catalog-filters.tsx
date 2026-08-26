import { Filter, X } from "lucide-react";
import { useEffect, useState } from "react";
import { Form, Link } from "react-router-dom";

import type {
  Category,
  ProductList,
  SaleUnit,
  StockStatus,
} from "@/shared/types/api";

const availabilityLabels: Record<StockStatus, string> = {
  in_stock_today: "Відправимо сьогодні",
  in_stock: "В наявності",
  preorder: "Під замовлення",
  out_of_stock: "Немає в наявності",
};

const saleUnitLabels: Record<SaleUnit, string> = {
  piece: "Поштучно",
  meter: "За метр",
  coil: "Бухтами",
};

export interface CatalogFilterQuery {
  search?: string;
  subcategory?: string;
  brand: string[];
  in_stock?: string;
  availability: string[];
  sale_unit: string[];
  min_price?: string;
  max_price?: string;
  spec: string[];
}

interface CatalogFiltersProps {
  action: string;
  categories: Category[];
  activeCategory?: Category;
  categoryIsRouteParam: boolean;
  facets: ProductList["facets"];
  query: CatalogFilterQuery;
}

export function CatalogFilters({
  action,
  categories,
  activeCategory,
  categoryIsRouteParam,
  facets,
  query,
}: CatalogFiltersProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [moreFiltersOpen, setMoreFiltersOpen] = useState(false);
  const activeBrands = new Set(query.brand);
  const activeSpecs = new Set(query.spec);
  const activeAvailability = new Set(query.availability);
  const activeSaleUnits = new Set(query.sale_unit);

  useEffect(() => {
    if (!isOpen) return;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setIsOpen(false);
    };
    document.addEventListener("keydown", closeOnEscape);
    return () => document.removeEventListener("keydown", closeOnEscape);
  }, [isOpen]);

  return (
    <>
      <button
        aria-controls="catalog-filters"
        aria-expanded={isOpen}
        className="catalog-filter-launcher"
        onClick={() => setIsOpen(true)}
        type="button"
      >
        <Filter size={18} /> Фільтри
      </button>
      {isOpen ? (
        <button
          aria-label="Закрити фільтри"
          className="catalog-filters-backdrop"
          onClick={() => setIsOpen(false)}
          type="button"
        />
      ) : null}
      <aside
        aria-label="Фільтри товарів"
        aria-modal={isOpen || undefined}
        className="filters"
        data-open={isOpen || undefined}
        id="catalog-filters"
        role={isOpen ? "dialog" : undefined}
      >
        <div className="filters__title">
          <Filter size={18} />
          <strong>Фільтри</strong>
          <Link to={action}>Скинути</Link>
          <button
            aria-label="Закрити фільтри"
            className="filters__close"
            onClick={() => setIsOpen(false)}
            type="button"
          >
            <X size={19} />
          </button>
        </div>
        <Form action={action} method="get" onSubmit={() => setIsOpen(false)}>
          {query.search ? (
            <input name="search" type="hidden" value={query.search} />
          ) : null}
          <fieldset>
            <legend>Категорія</legend>
            <select
              aria-label="Категорія"
              defaultValue={activeCategory?.slug ?? ""}
              disabled={categoryIsRouteParam}
              name="category"
            >
              <option value="">Усі категорії</option>
              {categories.map((item) => (
                <option key={item.id} value={item.slug}>
                  {item.name} ({item.product_count})
                </option>
              ))}
            </select>
          </fieldset>
          {activeCategory?.subcategories.length ? (
            <fieldset>
              <legend>Підкатегорія</legend>
              <select
                aria-label="Підкатегорія"
                defaultValue={query.subcategory ?? ""}
                name="subcategory"
              >
                <option value="">Усі</option>
                {activeCategory.subcategories.map((item) => (
                  <option key={item.id} value={item.slug}>
                    {item.name} ({item.product_count})
                  </option>
                ))}
              </select>
            </fieldset>
          ) : null}
          <fieldset>
            <legend>Ціна, ₴</legend>
            <div className="price-filter">
              <input
                aria-label="Мінімальна ціна"
                defaultValue={query.min_price}
                inputMode="decimal"
                min="0"
                name="min_price"
                placeholder={facets.price.minimum ?? "від"}
                type="number"
              />
              <input
                aria-label="Максимальна ціна"
                defaultValue={query.max_price}
                inputMode="decimal"
                min="0"
                name="max_price"
                placeholder={facets.price.maximum ?? "до"}
                type="number"
              />
            </div>
          </fieldset>
          <FacetOptions
            activeValues={activeBrands}
            label="Бренд"
            name="brand"
            options={facets.brands}
          />
          <FacetOptions
            activeValues={activeAvailability}
            label="Наявність"
            name="availability"
            options={facets.availability}
            optionLabel={(value) =>
              availabilityLabels[value as StockStatus] ?? value
            }
          />
          <div
            className="filters__secondary"
            data-open={moreFiltersOpen || undefined}
          >
            <FacetOptions
              activeValues={activeSaleUnits}
              label="Одиниця продажу"
              name="sale_unit"
              options={facets.sale_units}
              optionLabel={(value) =>
                saleUnitLabels[value as SaleUnit] ?? value
              }
            />
            {Object.entries(facets.specs)
              .filter(
                ([key]) =>
                  key.toLocaleLowerCase("uk") !== "серія" ||
                  activeBrands.size > 0,
              )
              .map(([key, options]) => {
                const isSeries = key.toLocaleLowerCase("uk") === "серія";
                return (
                  <fieldset key={key}>
                    <legend>{key}</legend>
                    {isSeries ? (
                      <p className="filter-series-note">
                        Вибір серії покаже всі сумісні елементи цього дизайну.
                      </p>
                    ) : null}
                    <div className="filter-options">
                      {options.map((option) => {
                        const value = `${key}:${option.value}`;
                        return (
                          <label key={value}>
                            <input
                              defaultChecked={activeSpecs.has(value)}
                              name="spec"
                              type="checkbox"
                              value={value}
                            />
                            <span>{option.value}</span>
                            <small>{option.count}</small>
                          </label>
                        );
                      })}
                    </div>
                  </fieldset>
                );
              })}
            <label className="stock-filter">
              <input
                defaultChecked={query.in_stock === "true"}
                name="in_stock"
                type="checkbox"
                value="true"
              />
              Лише в наявності
            </label>
          </div>
          <button
            aria-expanded={moreFiltersOpen}
            className="filters__more"
            onClick={() => setMoreFiltersOpen((value) => !value)}
            type="button"
          >
            {moreFiltersOpen ? "Менше фільтрів" : "Більше фільтрів"}
          </button>
          <button className="button button--primary button--wide" type="submit">
            Застосувати
          </button>
        </Form>
      </aside>
    </>
  );
}

function FacetOptions({
  activeValues,
  label,
  name,
  optionLabel,
  options,
}: {
  activeValues: Set<string>;
  label: string;
  name: string;
  optionLabel?: (value: string) => string;
  options: ProductList["facets"]["brands"];
}) {
  if (!options.length) return null;
  return (
    <fieldset>
      <legend>{label}</legend>
      <div className="filter-options">
        {options.map((option) => (
          <label key={option.value}>
            <input
              defaultChecked={activeValues.has(option.value)}
              name={name}
              type="checkbox"
              value={option.value}
            />
            <span>{optionLabel?.(option.value) ?? option.value}</span>
            <small>{option.count}</small>
          </label>
        ))}
      </div>
    </fieldset>
  );
}
