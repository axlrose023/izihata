import { useInfiniteQuery } from "@tanstack/react-query";
import { useState } from "react";

import { specFacetsQuery } from "@/modules/catalog/api/facet-queries";
import {
  decodeSpecFilter,
  encodeSpecFilter,
} from "@/modules/catalog/lib/spec-filter";
import type { QueryValue } from "@/shared/api/query";
import { useDebouncedValue } from "@/shared/lib/use-debounced-value";
import { ErrorNotice } from "@/shared/ui/error-notice";

type FilterParams = Record<string, QueryValue | QueryValue[]>;
type Toggle = (name: string, value: string, checked: boolean) => void;

const materialFilterKey = "Матеріал";
const ipFilterKey = "Ступінь захисту IP";
const groupedAttributeKeys = new Set([
  "Матеріал виготовлення",
  "Ступінь захисту, IP",
  "Захисне виконання ІР",
]);
const groupedFilterCategories = new Set(["lowvoltage", "panels"]);

export function CatalogSpecFilters({
  params,
  activeSpecs,
  activeBrands,
  onToggle,
}: {
  params: FilterParams;
  activeSpecs: Set<string>;
  activeBrands: Set<string>;
  onToggle: Toggle;
}) {
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebouncedValue(search, 300);
  const result = useInfiniteQuery(
    specFacetsQuery(params, undefined, debouncedSearch),
  );
  const keys = new Map(
    result.data?.pages
      .flatMap((page) => page.items)
      .map((item) => [item.value, item.count]),
  );
  const category = typeof params.category === "string" ? params.category : "";
  const showGroupedFilters = groupedFilterCategories.has(category);
  if (showGroupedFilters) {
    keys.set(materialFilterKey, 0);
    keys.set(ipFilterKey, 0);
  }
  const selected = new Map<string, string[]>();
  for (const raw of activeSpecs) {
    const pair = decodeSpecFilter(raw);
    if (!pair) continue;
    selected.set(pair[0], [...(selected.get(pair[0]) ?? []), pair[1]]);
    if (!keys.has(pair[0])) keys.set(pair[0], 0);
  }
  return (
    <>
      <input
        aria-label="Пошук характеристики"
        className="facet-search"
        placeholder="Знайти характеристику"
        type="search"
        value={search}
        onChange={(event) => setSearch(event.target.value)}
      />
      {result.isPending ? (
        <p role="status">Завантажуємо характеристики…</p>
      ) : null}
      {result.isError ? (
        <ErrorNotice
          error={result.error}
          fallback="Не вдалося завантажити характеристики."
          onRetry={() => void result.refetch()}
        />
      ) : null}
      {[...keys]
        .filter(
          ([key]) =>
            !showGroupedFilters ||
            !groupedAttributeKeys.has(key) ||
            selected.has(key),
        )
        .filter(
          ([key]) =>
            key.toLocaleLowerCase("uk") !== "серія" ||
            activeBrands.size > 0 ||
            selected.has(key),
        )
        .map(([key, count]) => (
          <SpecFacet
            key={key}
            label={key}
            optionCount={count}
            selected={selected.get(key) ?? []}
            params={params}
            onToggle={onToggle}
          />
        ))}
      {result.hasNextPage ? (
        <button
          className="filters__more"
          type="button"
          disabled={result.isFetchingNextPage}
          onClick={() => void result.fetchNextPage()}
        >
          {result.isFetchingNextPage ? "Завантажуємо…" : "Ще характеристики"}
        </button>
      ) : null}
    </>
  );
}

function SpecFacet({
  label,
  optionCount,
  selected,
  params,
  onToggle,
}: {
  label: string;
  optionCount: number;
  selected: string[];
  params: FilterParams;
  onToggle: Toggle;
}) {
  const [open, setOpen] = useState(selected.length > 0);
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebouncedValue(search, 300);
  const result = useInfiniteQuery({
    ...specFacetsQuery(params, label, debouncedSearch),
    enabled: open,
  });
  const options = new Map(
    result.data?.pages
      .flatMap((page) => page.items)
      .map((item) => [item.value, item.count]),
  );
  for (const value of selected) if (!options.has(value)) options.set(value, 0);
  return (
    <details
      className="filter-spec"
      open={open}
      onToggle={(event) => setOpen(event.currentTarget.open)}
    >
      <summary>
        {label} {optionCount ? <small>({optionCount})</small> : null}
      </summary>
      {open ? (
        <fieldset>
          <legend className="visually-hidden">{label}</legend>
          {label.toLocaleLowerCase("uk") === "серія" ? (
            <p className="filter-series-note">
              Вибір серії покаже всі сумісні елементи цього дизайну.
            </p>
          ) : null}
          {optionCount > 8 || search ? (
            <input
              aria-label={`Пошук: ${label.toLocaleLowerCase("uk")}`}
              className="facet-search"
              type="search"
              placeholder={`Пошук: ${label.toLocaleLowerCase("uk")}`}
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
          ) : null}
          {result.isPending ? (
            <p role="status">Завантажуємо значення…</p>
          ) : null}
          {result.isError ? (
            <ErrorNotice
              error={result.error}
              fallback="Не вдалося завантажити значення."
              onRetry={() => void result.refetch()}
            />
          ) : null}
          <div className="filter-options">
            {[...options].map(([value, count]) => (
              <label key={value}>
                <input
                  type="checkbox"
                  checked={selected.includes(value)}
                  onChange={(event) =>
                    onToggle(
                      "spec",
                      encodeSpecFilter(label, value),
                      event.target.checked,
                    )
                  }
                />
                <span>{value}</span>
                <small>{count}</small>
              </label>
            ))}
            {!result.isPending && !result.isError && !options.size ? (
              <p className="filter-options__empty">Нічого не знайдено</p>
            ) : null}
          </div>
          {result.hasNextPage ? (
            <button
              className="filters__more"
              type="button"
              disabled={result.isFetchingNextPage}
              onClick={() => void result.fetchNextPage()}
            >
              {result.isFetchingNextPage ? "Завантажуємо…" : "Ще значення"}
            </button>
          ) : null}
        </fieldset>
      ) : null}
    </details>
  );
}
