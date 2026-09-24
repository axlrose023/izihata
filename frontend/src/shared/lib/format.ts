const moneyFormatter = new Intl.NumberFormat("uk-UA", {
  style: "currency",
  currency: "UAH",
  maximumFractionDigits: 0,
});

const dateFormatter = new Intl.DateTimeFormat("uk-UA", {
  dateStyle: "medium",
  timeStyle: "short",
});

export function formatMoney(value: string | number): string {
  const amount = Number(value);
  return Number.isFinite(amount) ? moneyFormatter.format(amount) : "—";
}

export function formatDate(value: string): string {
  return dateFormatter.format(new Date(value));
}

// Українські числівники: 1 товар · 2 товари · 5 товарів, з винятком на 11-14.
function pluralizeUk(
  count: number,
  forms: [one: string, few: string, many: string],
): string {
  const mod10 = count % 10;
  const mod100 = count % 100;
  if (mod10 === 1 && mod100 !== 11) return `${count} ${forms[0]}`;
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) {
    return `${count} ${forms[1]}`;
  }
  return `${count} ${forms[2]}`;
}

export function pluralizeProducts(count: number): string {
  return pluralizeUk(count, ["товар", "товари", "товарів"]);
}

export function pluralizePositions(count: number): string {
  return pluralizeUk(count, ["позиція", "позиції", "позицій"]);
}

export function pluralizeSubcategories(count: number): string {
  return pluralizeUk(count, ["підкатегорія", "підкатегорії", "підкатегорій"]);
}

export function pluralizeReviews(count: number): string {
  return pluralizeUk(count, ["відгук", "відгуки", "відгуків"]);
}

export function discountPercent(
  price: string | number,
  oldPrice: string | number | null | undefined,
): number | null {
  if (oldPrice === null || oldPrice === undefined) return null;
  const current = Number(price);
  const previous = Number(oldPrice);
  if (!Number.isFinite(current) || !Number.isFinite(previous)) return null;
  if (previous <= current || previous <= 0) return null;
  return Math.round(((previous - current) / previous) * 100);
}

const saleUnitLabels = {
  piece: "шт",
  meter: "м",
  coil: "бухта",
} as const;

export function saleUnitLabel(unit: keyof typeof saleUnitLabels): string {
  return saleUnitLabels[unit] ?? "шт";
}
