import { X } from "lucide-react";
import { Link, useSearchParams } from "react-router-dom";

import { saleUnitLabel } from "@/shared/lib/format";
import type { SaleUnit } from "@/shared/types/api";
import { labels as statusLabels } from "@/shared/lib/status-labels";

interface Chip {
  key: string;
  value: string;
  label: string;
}

/** Кожен активний фільтр окремою плашкою з хрестиком, як на артборді Catalog. */
export function ActiveFilters({ resetHref }: { resetHref: string }) {
  const [searchParams, setSearchParams] = useSearchParams();

  const chips: Chip[] = [];
  const push = (key: string, value: string, label: string) =>
    chips.push({ key, value, label });

  for (const value of searchParams.getAll("brand")) push("brand", value, value);
  for (const value of searchParams.getAll("availability")) {
    push("availability", value, statusLabels[value] ?? value);
  }
  for (const value of searchParams.getAll("sale_unit")) {
    push("sale_unit", value, saleUnitLabel(value as SaleUnit));
  }
  for (const value of searchParams.getAll("spec")) {
    const at = value.indexOf(":");
    push(
      "spec",
      value,
      at > 0 ? `${value.slice(0, at)}: ${value.slice(at + 1)}` : value,
    );
  }
  const min = searchParams.get("min_price");
  const max = searchParams.get("max_price");
  if (min) push("min_price", min, `від ${min} ₴`);
  if (max) push("max_price", max, `до ${max} ₴`);
  if (searchParams.get("in_stock") === "true") {
    push("in_stock", "true", "Тільки в наявності");
  }
  if (searchParams.get("subcategory")) {
    push("subcategory", searchParams.get("subcategory")!, "Підкатегорія");
  }

  if (!chips.length) return null;

  const drop = (chip: Chip) => {
    const next = new URLSearchParams(searchParams);
    const rest = next.getAll(chip.key).filter((item) => item !== chip.value);
    next.delete(chip.key);
    for (const item of rest) next.append(chip.key, item);
    next.delete("page");
    setSearchParams(next);
  };

  return (
    <div aria-label="Активні фільтри" className="active-filters" role="group">
      <span className="active-filters__caption">Активні</span>
      {chips.map((chip) => (
        <button
          aria-label={`Прибрати фільтр: ${chip.label}`}
          key={`${chip.key}:${chip.value}`}
          onClick={() => drop(chip)}
          type="button"
        >
          {chip.label}
          <X aria-hidden="true" size={13} />
        </button>
      ))}
      <Link className="active-filters__reset" to={resetHref}>
        Скинути все
      </Link>
    </div>
  );
}
