import { Filter, X } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { useDebouncedValue } from "@/shared/lib/use-debounced-value";
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
  total: number;
}

export function CatalogFilters({
  action,
  categories,
  activeCategory,
  categoryIsRouteParam,
  facets,
  query,
  total,
}: CatalogFiltersProps) {
  const [searchParams, setSearchParams] = useSearchParams();
  const [isOpen, setIsOpen] = useState(false);
  const [moreFiltersOpen, setMoreFiltersOpen] = useState(false);
  const activeBrands = new Set(query.brand);
  const activeSpecs = new Set(query.spec);
  const activeAvailability = new Set(query.availability);
  const activeSaleUnits = new Set(query.sale_unit);

  const update = (mutate: (params: URLSearchParams) => void) => {
    const next = new URLSearchParams(searchParams);
    mutate(next);
    next.delete("page");
    setSearchParams(next, { replace: true });
  };
  const setSingle = (name: string, value: string) =>
    update((params) => {
      if (value) params.set(name, value);
      else params.delete(name);
    });
  const toggleMulti = (name: string, value: string, checked: boolean) =>
    update((params) => {
      const kept = params.getAll(name).filter((item) => item !== value);
      params.delete(name);
      for (const item of kept) params.append(name, item);
      if (checked) params.append(name, value);
    });

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
        <div className="filters__body">
          <fieldset>
            <legend>Категорія</legend>
            <select
              aria-label="Категорія"
              disabled={categoryIsRouteParam}
              onChange={(event) => setSingle("category", event.target.value)}
              value={activeCategory?.slug ?? ""}
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
                onChange={(event) =>
                  setSingle("subcategory", event.target.value)
                }
                value={query.subcategory ?? ""}
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
          <PriceFilter facets={facets} onChange={setSingle} query={query} />
          <FacetOptions
            activeValues={activeBrands}
            label="Бренд"
            name="brand"
            onToggle={toggleMulti}
            options={facets.brands}
          />
          <FacetOptions
            activeValues={activeAvailability}
            label="Наявність"
            name="availability"
            onToggle={toggleMulti}
            optionLabel={(value) =>
              availabilityLabels[value as StockStatus] ?? value
            }
            options={facets.availability}
          />
          <div
            className="filters__secondary"
            data-open={moreFiltersOpen || undefined}
          >
            <FacetOptions
              activeValues={activeSaleUnits}
              label="Одиниця продажу"
              name="sale_unit"
              onToggle={toggleMulti}
              optionLabel={(value) =>
                saleUnitLabels[value as SaleUnit] ?? value
              }
              options={facets.sale_units}
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
                              checked={activeSpecs.has(value)}
                              onChange={(event) =>
                                toggleMulti("spec", value, event.target.checked)
                              }
                              type="checkbox"
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
                checked={query.in_stock === "true"}
                onChange={(event) =>
                  setSingle("in_stock", event.target.checked ? "true" : "")
                }
                type="checkbox"
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
        </div>
        <button
          className="filters__done"
          onClick={() => setIsOpen(false)}
          type="button"
        >
          Показати {total}
        </button>
      </aside>
    </>
  );
}

function PriceFilter({
  facets,
  onChange,
  query,
}: {
  facets: ProductList["facets"];
  onChange: (name: string, value: string) => void;
  query: CatalogFilterQuery;
}) {
  const [range, setRange] = useState({
    min: query.min_price ?? "",
    max: query.max_price ?? "",
  });
  const debounced = useDebouncedValue(range, 500);

  useEffect(() => {
    if (debounced.min !== (query.min_price ?? "")) {
      onChange("min_price", debounced.min);
    }
    if (debounced.max !== (query.max_price ?? "")) {
      onChange("max_price", debounced.max);
    }
    // Only the settled input drives the URL; query values are the source of truth.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debounced]);

  return (
    <fieldset>
      <legend>Ціна, ₴</legend>
      <div className="price-filter">
        <input
          aria-label="Мінімальна ціна"
          inputMode="decimal"
          min="0"
          onChange={(event) =>
            setRange((value) => ({ ...value, min: event.target.value }))
          }
          placeholder={facets.price.minimum ?? "від"}
          type="number"
          value={range.min}
        />
        <input
          aria-label="Максимальна ціна"
          inputMode="decimal"
          min="0"
          onChange={(event) =>
            setRange((value) => ({ ...value, max: event.target.value }))
          }
          placeholder={facets.price.maximum ?? "до"}
          type="number"
          value={range.max}
        />
      </div>
    </fieldset>
  );
}

function FacetOptions({
  activeValues,
  label,
  name,
  onToggle,
  optionLabel,
  options,
}: {
  activeValues: Set<string>;
  label: string;
  name: string;
  onToggle: (name: string, value: string, checked: boolean) => void;
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
              checked={activeValues.has(option.value)}
              onChange={(event) =>
                onToggle(name, option.value, event.target.checked)
              }
              type="checkbox"
            />
            <span>{optionLabel?.(option.value) ?? option.value}</span>
            <small>{option.count}</small>
          </label>
        ))}
      </div>
    </fieldset>
  );
}
