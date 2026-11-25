import { LogIn } from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';

export function LoginPrompt({ text = 'Đăng nhập để tra từ và lưu vào sổ.' }: { text?: string }) {
  const loc = useLocation();
  return (
    <div className="flex flex-col items-start gap-3 p-6">
      <p className="m-0 text-[15px]">{text}</p>
      <Link to={`/login?next=${encodeURIComponent(loc.pathname + loc.search)}`} className="btn btn-primary no-underline">
        <LogIn aria-hidden="true" size={16} /> Đăng nhập
      </Link>
    </div>
  );
}
