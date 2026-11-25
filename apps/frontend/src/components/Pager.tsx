import { ChevronLeft, ChevronRight } from 'lucide-react';

export function Pager({ page, size, total, onPage }: { page: number; size: number; total: number; onPage: (p: number) => void }) {
  const pages = Math.max(1, Math.ceil(total / size));
  if (pages <= 1) return null;
  return (
    <nav aria-label="Phân trang" className="flex items-center justify-between gap-2 border-t-2 border-ink px-3 py-2 text-[13px]">
      <button type="button" className="btn btn-secondary btn-sm" disabled={page <= 1} onClick={() => onPage(page - 1)}>
        <ChevronLeft aria-hidden="true" size={16} /> Trước
      </button>
      <span className="text-muted">
        Trang {page}/{pages}
      </span>
      <button type="button" className="btn btn-secondary btn-sm" disabled={page >= pages} onClick={() => onPage(page + 1)}>
        Sau <ChevronRight aria-hidden="true" size={16} />
      </button>
    </nav>
  );
}
