import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { AlertTriangle, Check, Minus, Plus } from "lucide-react";
import { useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { createBoardRequest } from "@/modules/custom-boards/api/custom-board-api";
import { getUserErrorMessage } from "@/shared/api/errors";
import { formatMoney } from "@/shared/lib/format";
import { Modal } from "@/shared/ui/modal";

type Box = {
  sku: string;
  capacity: number;
  name: string;
  price: number;
  meta: string;
};

type Part = {
  sku: string;
  modules: number;
  name: string;
  brand: string;
  price: number;
  tone: string;
};

const boxes: Box[] = [
  {
    sku: "AX-10035",
    capacity: 12,
    name: "Щит модульний накладний 12 модулів",
    price: 620,
    meta: "AX-10035 · IEK · накладний · IP30",
  },
  {
    sku: "AX-10062",
    capacity: 36,
    name: "Щит мультимедійний вбудований 36 модулів",
    price: 4750,
    meta: "AX-10062 · Legrand · вбудований",
  },
];

const parts: Part[] = [
  {
    sku: "AX-10004",
    modules: 1,
    name: "Автоматичний вимикач MCN 1P B6",
    brand: "Hager",
    price: 198,
    tone: "#3a4453",
  },
  {
    sku: "AX-10002",
    modules: 1,
    name: "Автоматичний вимикач RESI9 1P C10",
    brand: "Schneider Electric",
    price: 224,
    tone: "#3a4453",
  },
  {
    sku: "AX-10001",
    modules: 1,
    name: "Автоматичний вимикач ВА47 1P C16",
    brand: "IEK",
    price: 96,
    tone: "#3a4453",
  },
  {
    sku: "AX-10003",
    modules: 2,
    name: "Автоматичний вимикач S200 2P C25",
    brand: "ABB",
    price: 412,
    tone: "#4d5766",
  },
  {
    sku: "AX-10005",
    modules: 3,
    name: "Автоматичний вимикач e.mcb 3P C32",
    brand: "E.Next",
    price: 356,
    tone: "#4d5766",
  },
  {
    sku: "AX-10010",
    modules: 2,
    name: "ПЗВ ВД1-63 2P 16А 10мА",
    brand: "IEK",
    price: 398,
    tone: "#157347",
  },
  {
    sku: "AX-10006",
    modules: 2,
    name: "ПЗВ (УЗО) RESI9 2P 25А 30мА",
    brand: "Schneider Electric",
    price: 612,
    tone: "#157347",
  },
  {
    sku: "AX-10008",
    modules: 2,
    name: "ПЗВ NFC 2P 40А 30мА",
    brand: "Legrand",
    price: 745,
    tone: "#157347",
  },
  {
    sku: "AX-10007",
    modules: 2,
    name: "Дифавтомат DS201 1P+N C16 30мА",
    brand: "ABB",
    price: 1180,
    tone: "#1f6f8b",
  },
  {
    sku: "AX-10009",
    modules: 2,
    name: "Дифавтомат e.dif.pro 1P+N C25",
    brand: "E.Next",
    price: 690,
    tone: "#1f6f8b",
  },
  {
    sku: "AX-10056",
    modules: 4,
    name: "Обмежувач перенапруги 3P+N тип 2",
    brand: "Schneider Electric",
    price: 3260,
    tone: "#9a5b00",
  },
];

const contactSchema = z.object({
  customer_name: z.string().trim().min(2, "Вкажіть ім’я").max(120),
  phone: z
    .string()
    .trim()
    .regex(/^\+?[0-9 ()-]{8,24}$/, "Вкажіть коректний телефон"),
  email: z.union([
    z.literal(""),
    z.string().trim().email("Вкажіть коректний email"),
  ]),
  details: z.string().trim().max(4000).optional(),
});

type ContactValues = z.infer<typeof contactSchema>;

function plural(value: number, one: string, few: string, many: string) {
  const last = value % 10;
  const hundred = value % 100;
  if (last === 1 && hundred !== 11) return one;
  if (last >= 2 && last <= 4 && (hundred < 10 || hundred >= 20)) return few;
  return many;
}

export function CustomBoardForm() {
  const [boxSku, setBoxSku] = useState(boxes[0].sku);
  const [quantities, setQuantities] = useState<Record<string, number>>({
    "AX-10001": 4,
    "AX-10006": 1,
  });
  const [contactOpen, setContactOpen] = useState(false);
  const [sent, setSent] = useState(false);
  const selectedBox = boxes.find((box) => box.sku === boxSku) ?? boxes[0];
  const chosen = parts
    .filter((part) => (quantities[part.sku] ?? 0) > 0)
    .map((part) => ({ part, quantity: quantities[part.sku] }));
  const used = chosen.reduce(
    (sum, item) => sum + item.part.modules * item.quantity,
    0,
  );
  const total =
    selectedBox.price +
    chosen.reduce((sum, item) => sum + item.part.price * item.quantity, 0);
  const over = used > selectedBox.capacity;
  const rails = useMemo(() => {
    const sequence = chosen.flatMap(({ part, quantity }) =>
      Array.from({ length: quantity }, () => part),
    );
    const rows: Part[][] = [];
    let row: Part[] = [];
    let rowWidth = 0;
    sequence.forEach((part) => {
      if (rowWidth + part.modules > 12) {
        rows.push(row);
        row = [];
        rowWidth = 0;
      }
      row.push(part);
      rowWidth += part.modules;
    });
    if (row.length) rows.push(row);
    return rows;
  }, [chosen]);
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ContactValues>({
    resolver: zodResolver(contactSchema),
    defaultValues: { phone: "+380" },
  });
  const requestMutation = useMutation({
    mutationFn: createBoardRequest,
    onSuccess: () => {
      setContactOpen(false);
      setSent(true);
    },
  });

  const changeQuantity = (sku: string, delta: number) => {
    setQuantities((current) => {
      const next = Math.max(0, (current[sku] ?? 0) + delta);
      if (!next) {
        const { [sku]: _, ...rest } = current;
        return rest;
      }
      return { ...current, [sku]: next };
    });
    setSent(false);
  };
  const submitContacts = handleSubmit((contact) => {
    requestMutation.mutate({
      application: "apartment",
      groups_count: used,
      ip_class: selectedBox.meta.includes("IP30") ? "IP30" : "IP20",
      automation_brand: chosen.map(({ part }) => part.brand).join(", "),
      budget: String(total),
      customer_name: contact.customer_name,
      phone: contact.phone,
      email: contact.email || undefined,
      details: [
        contact.details,
        `Конструктор: ${selectedBox.name}; ${chosen.map(({ part, quantity }) => `${part.sku} × ${quantity}`).join(", ")}.`,
      ]
        .filter(Boolean)
        .join(" "),
    });
  });

  return (
    <section className="board-builder" aria-label="Конструктор щита">
      <div className="board-builder__left">
        <section className="board-builder__section">
          <header className="board-builder__step-heading">
            <span>1</span>
            <h1>Корпус щита</h1>
          </header>
          <div className="board-builder__boxes">
            {boxes.map((box) => {
              const selected = box.sku === selectedBox.sku;
              return (
                <button
                  aria-pressed={selected}
                  className={selected ? "is-selected" : undefined}
                  key={box.sku}
                  onClick={() => {
                    setBoxSku(box.sku);
                    setSent(false);
                  }}
                  type="button"
                >
                  <span className="board-builder__radio" />
                  <span>
                    <strong>{box.name}</strong>
                    <small>{box.meta}</small>
                  </span>
                  <b>{formatMoney(box.price)}</b>
                </button>
              );
            })}
          </div>
        </section>
        <section className="board-builder__section board-builder__parts">
          <header className="board-builder__step-heading">
            <span>2</span>
            <h2>Наповнення</h2>
            <small>
              {used} з {selectedBox.capacity}{" "}
              {plural(selectedBox.capacity, "модуля", "модулів", "модулів")}
            </small>
          </header>
          <p>
            Ширина апарата в модулях порахована за кількістю полюсів: 1P — один
            модуль, 2P і 1P+N — два, 3P — три, 3P+N — чотири.
          </p>
          <div className="board-builder__part-list">
            {parts.map((part) => {
              const quantity = quantities[part.sku] ?? 0;
              return (
                <article
                  className={quantity ? "is-selected" : undefined}
                  key={part.sku}
                >
                  <span
                    className="board-builder__device"
                    data-modules={part.modules}
                  >
                    <i style={{ backgroundColor: part.tone }} />
                  </span>
                  <div>
                    <span className="eyebrow">
                      {part.brand} · {part.modules} мод.
                    </span>
                    <strong>{part.name}</strong>
                    <small>
                      {part.sku} · {formatMoney(part.price)}
                    </small>
                  </div>
                  <div className="board-builder__quantity">
                    <button
                      aria-label={`Зменшити кількість: ${part.name}`}
                      disabled={!quantity}
                      onClick={() => changeQuantity(part.sku, -1)}
                      type="button"
                    >
                      <Minus size={15} />
                    </button>
                    <output>{quantity}</output>
                    <button
                      aria-label={`Збільшити кількість: ${part.name}`}
                      onClick={() => changeQuantity(part.sku, 1)}
                      type="button"
                    >
                      <Plus size={15} />
                    </button>
                  </div>
                </article>
              );
            })}
          </div>
        </section>
      </div>
      <aside className="board-builder__right">
        <section className="board-builder__schematic">
          <header>
            <span className="eyebrow">Схема складання</span>
            <small>{selectedBox.name}</small>
            <b className={over ? "is-over" : undefined}>
              {used} з {selectedBox.capacity}{" "}
              {plural(selectedBox.capacity, "модуля", "модулів", "модулів")}
            </b>
          </header>
          <div className="board-builder__rails">
            {rails.length ? (
              rails.map((rail, index) => {
                const width = rail.reduce((sum, part) => sum + part.modules, 0);
                const extra = index >= Math.ceil(selectedBox.capacity / 12);
                return (
                  <div
                    className={extra ? "is-over" : undefined}
                    key={`${rail.map((part) => part.sku).join("-")}-${index}`}
                  >
                    {extra ? <em>НЕ ВМІЩАЄТЬСЯ</em> : null}
                    {rail.map((part, partIndex) => (
                      <span
                        key={`${part.sku}-${partIndex}`}
                        style={{
                          width: `${part.modules * 26}px`,
                          backgroundColor: part.tone,
                        }}
                      >
                        {part.modules > 1 ? `${part.modules}P` : ""}
                      </span>
                    ))}
                    {Array.from({ length: 12 - width }).map((_, emptyIndex) => (
                      <i key={emptyIndex} />
                    ))}
                  </div>
                );
              })
            ) : (
              <p>Додайте апарати зліва — вони стануть на рейку</p>
            )}
          </div>
          <footer>
            <span>
              <i
                style={{
                  width: `${Math.min(100, (used / selectedBox.capacity) * 100)}%`,
                }}
              />
            </span>
            <small>
              <span>
                {used} з {selectedBox.capacity}{" "}
                {plural(selectedBox.capacity, "модуля", "модулів", "модулів")}
              </span>
              <span>
                {over
                  ? `перевищення на ${used - selectedBox.capacity}`
                  : `вільно ${selectedBox.capacity - used}`}
              </span>
            </small>
          </footer>
          {over ? (
            <p className="board-builder__overload">
              <AlertTriangle size={15} /> Апарати не вміщаються: потрібно {used}{" "}
              модулів, у корпусі {selectedBox.capacity}. Оберіть більший корпус
              або приберіть позицію.
            </p>
          ) : null}
        </section>
        <section className="board-builder__estimate">
          <header>
            <h2>Кошторис</h2>
            <small>
              {chosen.length}{" "}
              {plural(chosen.length, "позиція", "позиції", "позицій")}
            </small>
          </header>
          <div>
            <p>
              <span>{selectedBox.name}</span>
              <b>{formatMoney(selectedBox.price)}</b>
            </p>
            {chosen.map(({ part, quantity }) => (
              <p key={part.sku}>
                <span>
                  {part.name} × {quantity}
                </span>
                <b>{formatMoney(part.price * quantity)}</b>
              </p>
            ))}
            <p>
              <span>Складання і перевірка</span>
              <b>[вартість робіт]</b>
            </p>
            <p className="board-builder__estimate-total">
              <strong>Комплектуючі</strong>
              <strong>{formatMoney(total)}</strong>
            </p>
          </div>
        </section>
        {sent ? (
          <section className="board-builder__sent" role="status">
            <span>
              <Check size={21} />
            </span>
            <div>
              <h2>Заявку надіслано</h2>
              <p>
                Схема на {used} {plural(used, "модуль", "модулі", "модулів")} у
                корпусі «{selectedBox.name}» на {formatMoney(total)} пішла
                менеджеру. Відповімо протягом робочого дня.
              </p>
              <button
                className="button button--outline"
                onClick={() => {
                  setQuantities({});
                  setSent(false);
                }}
                type="button"
              >
                Зібрати ще один щит
              </button>
            </div>
          </section>
        ) : (
          <section className="board-builder__send">
            <button
              className="button button--primary"
              disabled={over || !chosen.length}
              onClick={() => setContactOpen(true)}
              type="button"
            >
              Надіслати заявку на складання
            </button>
            <p>
              Менеджер перевірить схему, узгодить вартість робіт і термін
              складання
            </p>
          </section>
        )}
      </aside>
      <Modal
        onClose={() => setContactOpen(false)}
        open={contactOpen}
        title="Контакти для заявки"
      >
        <form
          className="board-builder__contact form-stack"
          onSubmit={submitContacts}
        >
          <p>
            Надішлемо менеджеру вашу схему і дамо відповідь протягом робочого
            дня.
          </p>
          <label className="field">
            <span>Ім’я</span>
            <input autoComplete="name" {...register("customer_name")} />
            {errors.customer_name ? (
              <small>{errors.customer_name.message}</small>
            ) : null}
          </label>
          <label className="field">
            <span>Телефон</span>
            <input autoComplete="tel" inputMode="tel" {...register("phone")} />
            {errors.phone ? <small>{errors.phone.message}</small> : null}
          </label>
          <label className="field">
            <span>Email (необов’язково)</span>
            <input autoComplete="email" type="email" {...register("email")} />
            {errors.email ? <small>{errors.email.message}</small> : null}
          </label>
          <label className="field">
            <span>Коментар (необов’язково)</span>
            <textarea rows={3} {...register("details")} />
          </label>
          {requestMutation.isError ? (
            <p className="form-error" role="alert">
              {getUserErrorMessage(
                requestMutation.error,
                "Не вдалося надіслати заявку",
              )}
            </p>
          ) : null}
          <button
            className="button button--primary"
            disabled={requestMutation.isPending}
            type="submit"
          >
            {requestMutation.isPending ? "Надсилаємо…" : "Надіслати заявку"}
          </button>
        </form>
      </Modal>
    </section>
  );
}
