import { useQuery } from "@tanstack/react-query";
import { facetsQuery } from "@/modules/catalog/api/facet-queries";
import { CatalogSpecFilters } from "./catalog-spec-filters";
import { ErrorNotice } from "@/shared/ui/error-notice";
import type { QueryValue } from "@/shared/api/query";
import { Filter, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import {
  decodeSpecFilter,
  encodeSpecFilter,
} from "@/modules/catalog/lib/spec-filter";
import { useBodyScrollLock } from "@/shared/lib/use-body-scroll-lock";
import { useCloseOnEscape } from "@/shared/lib/use-close-on-escape";
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
  params: Record<string, QueryValue | QueryValue[]>;
  query: CatalogFilterQuery;
  total: number;
}

export function CatalogFilters({
  action,
  categories,
  activeCategory,
  categoryIsRouteParam,
  params,
  query,
  total,
}: CatalogFiltersProps) {
  const [searchParams, setSearchParams] = useSearchParams();
  const [isOpen, setIsOpen] = useState(false);
  const [moreFiltersOpen, setMoreFiltersOpen] = useState(query.spec.length > 0);
  const facetsResult = useQuery(facetsQuery(params));
  const facets = facetsResult.data ?? {
    brands: [],
    specs: {},
    availability: [],
    sale_units: [],
    price: { minimum: null, maximum: null },
  };
  useBodyScrollLock(isOpen);
  const activeBrands = new Set(query.brand);
  const activeSpecs = new Set(
    query.spec.map((raw) => {
      const pair = decodeSpecFilter(raw);
      return pair ? encodeSpecFilter(...pair) : raw;
    }),
  );
  const activeAvailability = new Set(query.availability);
  const activeSaleUnits = new Set(query.sale_unit);
  const activeCount =
    activeBrands.size +
    activeSpecs.size +
    activeAvailability.size +
    activeSaleUnits.size +
    (query.min_price || query.max_price ? 1 : 0);

  const update = (mutate: (params: URLSearchParams) => void) => {
    const next = new URLSearchParams(searchParams);
    mutate(next);
    next.delete("page");
    setSearchParams(next, { replace: true, preventScrollReset: true });
  };
  const setValues = (values: Record<string, string>) =>
    update((params) => {
      for (const [name, value] of Object.entries(values)) {
        if (value) params.set(name, value);
        else params.delete(name);
      }
    });
  const setSingle = (name: string, value: string) =>
    setValues({ [name]: value });
  const toggleMulti = (name: string, value: string, checked: boolean) =>
    update((params) => {
      const kept = params.getAll(name).filter((item) => {
        const pair = name === "spec" ? decodeSpecFilter(item) : null;
        return (pair ? encodeSpecFilter(...pair) : item) !== value;
      });
      params.delete(name);
      for (const item of kept) params.append(name, item);
      if (checked) params.append(name, value);
    });

  useCloseOnEscape(isOpen, () => setIsOpen(false));

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
          {activeCount ? <b className="filters__count">{activeCount}</b> : null}
          <Link preventScrollReset to={action}>
            Скинути
          </Link>
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
          {facetsResult.isPending ? (
            <p role="status">Завантажуємо фільтри…</p>
          ) : null}
          {facetsResult.isError ? (
            <ErrorNotice
              error={facetsResult.error}
              fallback="Не вдалося завантажити фільтри."
              onRetry={() => void facetsResult.refetch()}
            />
          ) : null}
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
          <PriceFilter
            facets={facets}
            key={`${query.min_price ?? ""}:${query.max_price ?? ""}`}
            onChange={setValues}
            query={query}
          />
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
          {moreFiltersOpen ? (
            <div className="filters__secondary" data-open>
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
              <CatalogSpecFilters
                params={params}
                activeSpecs={activeSpecs}
                activeBrands={activeBrands}
                onToggle={toggleMulti}
              />
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
          ) : null}
          <button
            aria-expanded={moreFiltersOpen}
            className="filters__more"
            onClick={() => setMoreFiltersOpen((value) => !value)}
            type="button"
          >
            {moreFiltersOpen ? "Менше фільтрів" : "Більше фільтрів"}
          </button>
        </div>
        <div className="filters__footer">
          <Link
            className="filters__footer-reset"
            preventScrollReset
            to={action}
          >
            Скинути
          </Link>
          <button
            className="filters__done"
            onClick={() => setIsOpen(false)}
            type="button"
          >
            Показати {total}
          </button>
        </div>
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
  onChange: (values: Record<string, string>) => void;
  query: CatalogFilterQuery;
}) {
  const [range, setRange] = useState({
    min: query.min_price ?? "",
    max: query.max_price ?? "",
  });
  const debounced = useDebouncedValue(range, 500);
  const userChangedRange = useRef(false);
  // Межі приходять із фасетів; без них повзунок не має шкали й не малюється.
  const lo = Number(facets.price.minimum);
  const hi = Number(facets.price.maximum);
  const bounds =
    Number.isFinite(lo) && Number.isFinite(hi) && hi > lo
      ? { min: Math.floor(lo), max: Math.ceil(hi) }
      : null;
  const minValue = range.min === "" ? (bounds?.min ?? 0) : Number(range.min);
  const maxValue = range.max === "" ? (bounds?.max ?? 0) : Number(range.max);

  useEffect(() => {
    if (
      !userChangedRange.current ||
      debounced.min !== range.min ||
      debounced.max !== range.max
    ) {
      return;
    }
    const queryMin = query.min_price ?? "";
    const queryMax = query.max_price ?? "";
    if (debounced.min === queryMin && debounced.max === queryMax) {
      userChangedRange.current = false;
      return;
    }
    onChange({ min_price: debounced.min, max_price: debounced.max });
    // The input state is remounted from the URL once the route changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debounced, query.min_price, query.max_price, range]);

  const changeRange = (update: (value: typeof range) => typeof range) => {
    userChangedRange.current = true;
    setRange(update);
  };

  return (
    <fieldset>
      <legend>Ціна, ₴</legend>
      <div className="price-filter">
        <input
          aria-label="Мінімальна ціна"
          inputMode="decimal"
          min="0"
          onChange={(event) =>
            changeRange((value) => ({ ...value, min: event.target.value }))
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
            changeRange((value) => ({ ...value, max: event.target.value }))
          }
          placeholder={facets.price.maximum ?? "до"}
          type="number"
          value={range.max}
        />
      </div>
      {bounds ? (
        <div className="price-slider">
          <input
            aria-label="Мінімальна ціна, повзунок"
            max={bounds.max}
            min={bounds.min}
            onChange={(event) =>
              changeRange((value) => ({
                ...value,
                min: String(Math.min(Number(event.target.value), maxValue)),
              }))
            }
            type="range"
            value={minValue}
          />
          <input
            aria-label="Максимальна ціна, повзунок"
            max={bounds.max}
            min={bounds.min}
            onChange={(event) =>
              changeRange((value) => ({
                ...value,
                max: String(Math.max(Number(event.target.value), minValue)),
              }))
            }
            type="range"
            value={maxValue}
          />
          <div className="price-slider__bounds">
            <span>{bounds.min}</span>
            <span>{bounds.max}</span>
          </div>
        </div>
      ) : null}
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
  const [search, setSearch] = useState("");
  if (!options.length) return null;
  // Брендів десятки, тож довгий список отримує власний пошук (артборд Catalog).
  const searchable = options.length > 8;
  const matches = searchable
    ? options.filter((option) =>
        option.value
          .toLocaleLowerCase("uk")
          .includes(search.toLocaleLowerCase("uk")),
      )
    : options;
  const shown = searchable
    ? search
      ? matches.slice(0, 100)
      : [
          ...options.filter((option) => activeValues.has(option.value)),
          ...options.slice(0, 8),
        ].filter(
          (option, index, all) =>
            all.findIndex((item) => item.value === option.value) === index,
        )
    : options;
  return (
    <fieldset>
      <legend>{label}</legend>
      {searchable ? (
        <input
          aria-label={`Пошук: ${label.toLocaleLowerCase("uk")}`}
          className="facet-search"
          onChange={(event) => setSearch(event.target.value)}
          placeholder={`Пошук: ${label.toLocaleLowerCase("uk")}`}
          type="search"
          value={search}
        />
      ) : null}
      {searchable ? (
        <small className="facet-search__hint">
          {search
            ? `Знайдено ${matches.length}; показано ${shown.length}`
            : `Показано ${shown.length} з ${options.length}. Уточніть пошук.`}
        </small>
      ) : null}
      <div className="filter-options">
        {shown.map((option) => (
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
        {searchable && search && !shown.length ? (
          <p className="filter-options__empty">Нічого не знайдено</p>
        ) : null}
      </div>
    </fieldset>
  );
}
