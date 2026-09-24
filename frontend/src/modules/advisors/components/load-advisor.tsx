import { AlertCircle, LoaderCircle, Plus } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import {
  calculateBreaker,
  calculateCable,
} from "@/modules/advisors/api/advisor-api";
import { ProductVisual } from "@/modules/catalog/components/product-visual";
import { useCartStore } from "@/modules/cart/store";
import { formatMoney } from "@/shared/lib/format";
import type {
  BreakerResult,
  CableSizeResult,
  Product,
} from "@/shared/types/api";

type Calculation = {
  cable: CableSizeResult;
  breaker: BreakerResult;
};

const presets = [
  { label: "розетки", value: 2 },
  { label: "бойлер", value: 3.5 },
  { label: "варильна", value: 5 },
  { label: "ввід квартири", value: 9 },
  { label: "ввід будинку", value: 15 },
];

function bundleItems(result: Calculation | null): Product[] {
  if (!result) return [];
  return [...result.cable.products, ...result.breaker.products].filter(
    (product, index, products) =>
      products.findIndex((candidate) => candidate.id === product.id) === index,
  );
}

export function LoadAdvisor() {
  const [power, setPower] = useState(3.5);
  const [length, setLength] = useState(20);
  const [phase, setPhase] = useState<"single" | "three">("single");
  const [result, setResult] = useState<Calculation | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(false);
  const add = useCartStore((state) => state.add);

  const voltage = phase === "single" ? 230 : 400;
  const current = useMemo(
    () =>
      phase === "single"
        ? (power * 1000) / (voltage * 0.95)
        : (power * 1000) / (Math.sqrt(3) * voltage * 0.95),
    [phase, power, voltage],
  );

  useEffect(() => {
    let currentRequest = true;
    setIsLoading(true);
    setError(false);
    void Promise.all([
      calculateCable({
        current_a: current.toFixed(1),
        length_m: String(length),
        conductor_material: "copper",
      }),
      calculateBreaker({
        current_a: current.toFixed(1),
        load_type: "resistive",
      }),
    ])
      .then(([cable, breaker]) => {
        if (currentRequest) setResult({ cable, breaker });
      })
      .catch(() => {
        if (currentRequest) setError(true);
      })
      .finally(() => {
        if (currentRequest) setIsLoading(false);
      });
    return () => {
      currentRequest = false;
    };
  }, [current, length]);

  const section = Number(result?.cable.recommended_cross_section_mm2 ?? 0);
  const voltageDrop = section
    ? ((2 * length * current * 0.0175) / section / voltage) * 100
    : null;
  const products = bundleItems(result);

  const addBundle = () => {
    products.forEach((product) => {
      const quantity = product.sale_unit === "meter" ? length : 1;
      add(product, quantity);
    });
  };

  return (
    <div className="load-advisor">
      <header className="load-advisor__intro">
        <span className="eyebrow">Кабель і автомат за навантаженням</span>
        <h1>Який переріз і номінал вам потрібні</h1>
        <p>
          Вкажіть потужність лінії та відстань до щита — порахуємо струм,
          підберемо номінал автомата й переріз мідного кабелю з перевіркою на
          падіння напруги, а тоді покажемо позиції з каталогу.
        </p>
      </header>

      <section className="load-advisor__workspace">
        <div className="load-advisor__controls">
          <label>
            <span>Потужність лінії</span>
            <strong>{String(power).replace(".", ",")} кВт</strong>
            <input
              aria-label="Потужність лінії"
              max="20"
              min="0.5"
              onChange={(event) => setPower(Number(event.target.value))}
              step="0.5"
              type="range"
              value={power}
            />
            <small>
              <span>0,5 кВт</span>
              <span>20 кВт</span>
            </small>
          </label>
          <div
            className="load-advisor__presets"
            aria-label="Типове навантаження"
          >
            {presets.map((preset) => (
              <button
                className={power === preset.value ? "is-active" : undefined}
                key={preset.label}
                onClick={() => setPower(preset.value)}
                type="button"
              >
                {preset.label}
              </button>
            ))}
          </div>
          <label>
            <span>Довжина лінії до щита</span>
            <strong>{length} м</strong>
            <input
              aria-label="Довжина лінії до щита"
              max="120"
              min="3"
              onChange={(event) => setLength(Number(event.target.value))}
              type="range"
              value={length}
            />
            <small>
              <span>3 м</span>
              <span>120 м</span>
            </small>
          </label>
          <div className="load-advisor__phase">
            <span>Мережа</span>
            <div>
              <button
                aria-pressed={phase === "single"}
                className={phase === "single" ? "is-active" : undefined}
                onClick={() => setPhase("single")}
                type="button"
              >
                Однофазна · 230 В
              </button>
              <button
                aria-pressed={phase === "three"}
                className={phase === "three" ? "is-active" : undefined}
                onClick={() => setPhase("three")}
                type="button"
              >
                Трифазна · 400 В
              </button>
            </div>
          </div>
        </div>

        <div className="load-advisor__result" aria-live="polite">
          <div className="load-advisor__result-card">
            <span className="eyebrow">Розрахунок</span>
            <div className="load-advisor__metrics">
              <div>
                <span>Робочий струм</span>
                <strong>{current.toFixed(1).replace(".", ",")} А</strong>
              </div>
              <div>
                <span>Номінал автомата</span>
                <strong>
                  {result?.breaker.recommended_nominal_a ?? "—"} А
                </strong>
              </div>
              <div>
                <span>Переріз мідь</span>
                <strong>
                  {result?.cable.recommended_cross_section_mm2 ?? "—"} мм²
                </strong>
              </div>
            </div>
            <div className="load-advisor__checks">
              <span>
                Падіння напруги на довжині
                <b
                  className={
                    voltageDrop && voltageDrop > 3 ? "is-warning" : undefined
                  }
                >
                  {voltageDrop
                    ? `${voltageDrop.toFixed(1).replace(".", ",")} %`
                    : "—"}
                </b>
              </span>
              <span>
                Допустимий струм перерізу{" "}
                <b>
                  {result?.cable.current_a
                    ? `${result.cable.current_a} А`
                    : "—"}
                </b>
              </span>
            </div>
            {isLoading ? (
              <span className="load-advisor__loading">
                <LoaderCircle className="spin" size={16} /> Оновлюємо розрахунок
              </span>
            ) : null}
            {error ? (
              <span className="load-advisor__loading is-error">
                Не вдалося оновити підбір
              </span>
            ) : null}
          </div>
          <p className="load-advisor__notice">
            <AlertCircle size={17} /> Попередній розрахунок за спрощеною
            методикою: мідь, cos φ 0,95, допустиме падіння 3 %. Остаточний вибір
            апарата й кабелю — за ПУЕ та проєктом.
          </p>
        </div>
      </section>

      <section className="load-advisor__picks">
        <header>
          <div>
            <h2>Підібрані позиції з каталогу</h2>
            <span>
              {products.length
                ? `${products.length} позиції для комплекту`
                : "Підбираємо позиції"}
            </span>
          </div>
          <small>кошторис на {length} м</small>
        </header>
        <div className="load-advisor__pick-list">
          {products.map((product) => (
            <article key={product.id}>
              <span className="load-advisor__pick-visual">
                <ProductVisual iconSize={24} product={product} />
              </span>
              <div>
                <span className="eyebrow">
                  {product.sale_unit === "meter" ? "Кабель" : "Захист"}
                </span>
                <Link to={`/products/${product.slug}`}>{product.name}</Link>
                <small>
                  {product.sku} · {product.brand}
                </small>
              </div>
              <div>
                <small>
                  {product.sale_unit === "meter" ? `${length} м × ` : "1 шт × "}
                  {formatMoney(product.price)}
                </small>
                <strong>
                  {formatMoney(
                    Number(product.price) *
                      (product.sale_unit === "meter" ? length : 1),
                  )}
                </strong>
              </div>
            </article>
          ))}
          {!isLoading && !products.length ? (
            <p className="load-advisor__no-match">
              Частини комплекту немає в доступному каталозі. Залиште заявку —
              менеджер підбере сумісну заміну.
            </p>
          ) : null}
          <footer>
            <div>
              <span>Разом за комплект</span>
              <small>Ціну й наявність підтвердить сервер.</small>
            </div>
            <div>
              <strong>
                {products.length
                  ? formatMoney(
                      products.reduce(
                        (sum, product) =>
                          sum +
                          Number(product.price) *
                            (product.sale_unit === "meter" ? length : 1),
                        0,
                      ),
                    )
                  : "—"}
              </strong>
              <button
                className="button button--primary"
                disabled={!products.length}
                onClick={addBundle}
                type="button"
              >
                <Plus size={17} /> Додати комплект у кошик
              </button>
            </div>
          </footer>
        </div>
      </section>
    </div>
  );
}
