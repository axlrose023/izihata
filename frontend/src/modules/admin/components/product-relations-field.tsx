import { useQuery } from "@tanstack/react-query";
import { Plus, Search, Trash2 } from "lucide-react";
import { useState } from "react";

import { apiClient } from "@/shared/api/client";
import { buildQuery } from "@/shared/api/query";
import { useDebouncedValue } from "@/shared/lib/use-debounced-value";
import type {
  AdminProductRelation,
  ProductList,
  ProductRelationKind,
} from "@/shared/types/api";

type RelationDraft = Omit<AdminProductRelation, "position">;

const kinds: Array<{ value: ProductRelationKind; label: string }> = [
  { value: "bought_together", label: "З цим купують" },
  { value: "related", label: "Схожі товари" },
  { value: "alternative", label: "Аналоги" },
];

export function ProductRelationsField({
  productId,
  value,
  onChange,
}: {
  productId: string | null;
  value: RelationDraft[];
  onChange: (next: RelationDraft[]) => void;
}) {
  const [kind, setKind] = useState<ProductRelationKind>("bought_together");
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebouncedValue(search.trim(), 350);
  const results = useQuery({
    queryKey: ["admin", "relation-search", debouncedSearch],
    enabled: debouncedSearch.length >= 2,
    queryFn: () =>
      apiClient<ProductList>(
        `/catalog/products${buildQuery({ search: debouncedSearch, page_size: 8 })}`,
      ),
  });

  const add = (item: { id: string; name: string; sku: string }) => {
    onChange([
      ...value,
      { product_id: item.id, kind, name: item.name, sku: item.sku },
    ]);
    setSearch("");
  };
  const remove = (index: number) =>
    onChange(value.filter((_, position) => position !== index));

  return (
    <fieldset className="product-relations">
      <div className="product-relations__header">
        <div>
          <legend>Супутні товари</legend>
          <small>
            «З цим купують» показується в картці товару і в кошику. До 30
            зв’язків.
          </small>
        </div>
      </div>

      <div className="product-relations__picker">
        <div className="product-relations__kinds" role="group">
          {kinds.map((item) => (
            <button
              aria-pressed={kind === item.value}
              key={item.value}
              onClick={() => setKind(item.value)}
              type="button"
            >
              {item.label}
            </button>
          ))}
        </div>
        <label className="field">
          <span>Знайти товар за назвою або SKU</span>
          <span className="product-relations__search">
            <Search size={16} />
            <input
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Мінімум 2 символи"
              value={search}
            />
          </span>
        </label>
        {debouncedSearch.length >= 2 ? (
          <div className="product-relations__results">
            {results.isPending ? <p>Шукаємо…</p> : null}
            {results.isError ? <p>Не вдалося виконати пошук.</p> : null}
            {results.data?.items.length === 0 ? (
              <p>Нічого не знайдено.</p>
            ) : null}
            {results.data?.items.map((item) => {
              const isSelf = item.id === productId;
              const alreadyAdded = value.some(
                (relation) =>
                  relation.product_id === item.id && relation.kind === kind,
              );
              return (
                <div key={item.id}>
                  <span>
                    <strong>{item.name}</strong>
                    <small>{item.sku}</small>
                  </span>
                  <button
                    disabled={isSelf || alreadyAdded}
                    onClick={() => add(item)}
                    title={
                      isSelf
                        ? "Не можна пов’язати товар сам із собою"
                        : alreadyAdded
                          ? "Вже додано в цю групу"
                          : undefined
                    }
                    type="button"
                  >
                    <Plus size={15} /> Додати
                  </button>
                </div>
              );
            })}
          </div>
        ) : null}
      </div>

      {kinds.map((group) => {
        const items = value
          .map((relation, index) => ({ relation, index }))
          .filter(({ relation }) => relation.kind === group.value);
        if (!items.length) return null;
        return (
          <div className="product-relations__group" key={group.value}>
            <strong>{group.label}</strong>
            <ul>
              {items.map(({ relation, index }) => (
                <li key={`${relation.kind}-${relation.product_id}`}>
                  <span>
                    {relation.name}
                    <small>{relation.sku}</small>
                  </span>
                  <button
                    aria-label={`Прибрати ${relation.name} з групи «${group.label}»`}
                    onClick={() => remove(index)}
                    type="button"
                  >
                    <Trash2 size={16} />
                  </button>
                </li>
              ))}
            </ul>
          </div>
        );
      })}
    </fieldset>
  );
}
