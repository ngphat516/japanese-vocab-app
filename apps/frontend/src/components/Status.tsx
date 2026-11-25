import { ApiError } from '@/api/client';

export function Loading({ text = 'Đang tải…' }: { text?: string }) {
  return (
    <p role="status" className="m-0 p-5 text-muted">
      {text}
    </p>
  );
}

export function ErrorNote({ error }: { error: unknown }) {
  const msg =
    error instanceof ApiError
      ? error.message
      : error instanceof TypeError
        ? 'Không kết nối được máy chủ. Kiểm tra backend đang chạy.'
        : 'Đã có lỗi xảy ra.';
  return (
    <p role="alert" className="m-0 border-l-4 border-[var(--jlpt-n1-fg)] bg-card p-4 text-ink">
      {msg}
    </p>
  );
}
