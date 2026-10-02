interface AdminPaginationProps {
  page: number;
  totalPages: number;
  hasPrev: boolean;
  hasNext: boolean;
  onPageChange: (page: number) => void;
}

export function AdminPagination({
  page,
  totalPages,
  hasPrev,
  hasNext,
  onPageChange,
}: AdminPaginationProps) {
  if (totalPages <= 1) return null;
  return (
    <nav aria-label="Сторінки списку" className="pagination">
      <button
        disabled={!hasPrev}
        onClick={() => onPageChange(page - 1)}
        type="button"
      >
        ← Назад
      </button>
      <span>
        {page} / {totalPages}
      </span>
      <button
        disabled={!hasNext}
        onClick={() => onPageChange(page + 1)}
        type="button"
      >
        Далі →
      </button>
    </nav>
  );
}
