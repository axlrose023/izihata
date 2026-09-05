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

export function pluralizeProducts(count: number): string {
  const mod10 = count % 10;
  const mod100 = count % 100;
  if (mod10 === 1 && mod100 !== 11) return `${count} товар`;
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) {
    return `${count} товари`;
  }
  return `${count} товарів`;
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
