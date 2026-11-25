import { Link } from 'react-router-dom';
import { Window } from '@/components/Window';

export function NotFoundPage() {
  return (
    <main className="mx-auto max-w-[640px] px-4 pt-10">
      <Window title="404" bodyClassName="p-6 flex flex-col gap-4">
        <p className="m-0 text-[16px]">Không tìm thấy trang này.</p>
        <Link to="/" className="btn btn-primary self-start no-underline">Về trang Tra từ</Link>
      </Window>
    </main>
  );
}
