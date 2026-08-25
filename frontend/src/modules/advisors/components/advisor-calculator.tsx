import { useMutation } from "@tanstack/react-query";
import { useState } from "react";

import { ProductCard } from "@/modules/catalog/components/product-card";
import { getUserErrorMessage } from "@/shared/api/errors";
import type { AdvisorProductResult } from "@/shared/types/api";

export interface CalculatorField {
  name: string;
  label: string;
  type?: "number" | "select";
  min?: number;
  options?: Array<{ value: string; label: string }>;
  required?: boolean;
  initialValue: string;
}

export function AdvisorCalculator<TResult extends AdvisorProductResult>({
  title,
  description,
  fields,
  calculate,
  renderMetrics,
}: {
  title: string;
  description: string;
  fields: CalculatorField[];
  calculate: (values: Record<string, string>) => Promise<TResult>;
  renderMetrics: (result: TResult) => Array<{ label: string; value: string }>;
}) {
  const [values, setValues] = useState<Record<string, string>>(() =>
    Object.fromEntries(fields.map((field) => [field.name, field.initialValue])),
  );
  const mutation = useMutation({ mutationFn: calculate });

  const submit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    mutation.mutate(values);
  };

  return (
    <section className="advisor-calculator">
      <div>
        <span className="eyebrow">Експрес-підбір</span>
        <h2>{title}</h2>
        <p>{description}</p>
      </div>
      <form className="advisor-calculator__form" onSubmit={submit}>
        {fields.map((field) => (
          <label className="field" key={field.name}>
            <span>{field.label}</span>
            {field.type === "select" ? (
              <select
                onChange={(event) =>
                  setValues((current) => ({
                    ...current,
                    [field.name]: event.target.value,
                  }))
                }
                value={values[field.name]}
              >
                {field.options?.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            ) : (
              <input
                inputMode="decimal"
                min={field.min}
                onChange={(event) =>
                  setValues((current) => ({
                    ...current,
                    [field.name]: event.target.value,
                  }))
                }
                required={field.required ?? true}
                step="any"
                type="number"
                value={values[field.name]}
              />
            )}
          </label>
        ))}
        {mutation.isError ? (
          <p className="form-error" role="alert">
            {getUserErrorMessage(
              mutation.error,
              "Не вдалося виконати розрахунок",
            )}
          </p>
        ) : null}
        <button
          className="button button--primary"
          disabled={mutation.isPending}
          type="submit"
        >
          {mutation.isPending ? "Розраховуємо…" : "Розрахувати"}
        </button>
      </form>
      {mutation.data ? (
        <div className="advisor-calculator__result">
          <div className="advisor-calculator__metrics">
            {renderMetrics(mutation.data).map((metric) => (
              <div key={metric.label}>
                <span>{metric.label}</span>
                <strong>{metric.value}</strong>
              </div>
            ))}
          </div>
          <p>{mutation.data.reference_notice}</p>
          {mutation.data.products.length ? (
            <div className="product-grid advisor-calculator__products">
              {mutation.data.products.map((product) => (
                <ProductCard key={product.id} product={product} />
              ))}
            </div>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
