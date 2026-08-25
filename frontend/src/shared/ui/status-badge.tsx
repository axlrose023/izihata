const labels: Record<string, string> = {
  in_stock_today: "Відправимо сьогодні",
  in_stock: "В наявності",
  preorder: "Під замовлення",
  out_of_stock: "Немає в наявності",
  approved: "Підтверджено",
  rejected: "Відхилено",
  published: "Опубліковано",
  in_review: "На розгляді",
  quoted: "Кошторис надіслано",
  new: "Новий",
  confirmed: "Підтверджено",
  processing: "В роботі",
  shipped: "Відправлено",
  delivered: "Доставлено",
  cancelled: "Скасовано",
  closed: "Закрито",
  contacted: "Зв’язались",
  pending: "Очікує",
  not_required: "Не потрібна",
  paid: "Сплачено",
  failed: "Помилка",
  refunded: "Повернено",
};

export function StatusBadge({ status }: { status: string }) {
  return (
    <span className="status-badge" data-status={status}>
      {labels[status] ?? status}
    </span>
  );
}
