import * as DropdownMenu from '@radix-ui/react-dropdown-menu';
import { ChevronDown, LogIn, LogOut, User } from 'lucide-react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '@/auth/AuthProvider';

export function AccountMenu() {
  const { user, loading, logout } = useAuth();
  const loc = useLocation();
  const nav = useNavigate();
  if (loading) return <span className="text-[13px] text-muted">…</span>;
  if (!user) {
    const onAuthPage = loc.pathname === '/login' || loc.pathname === '/register';
    const next = onAuthPage ? '' : `?next=${encodeURIComponent(loc.pathname + loc.search)}`;
    return (
      <Link to={`/login${next}`} className="btn btn-secondary btn-sm no-underline">
        <LogIn aria-hidden="true" size={16} /> Đăng nhập
      </Link>
    );
  }
  return (
    <DropdownMenu.Root>
      <DropdownMenu.Trigger className="btn btn-secondary btn-sm">
        <User aria-hidden="true" size={16} />
        <span className="max-w-[140px] truncate">{user.display_name || user.email}</span>
        <ChevronDown aria-hidden="true" size={14} />
      </DropdownMenu.Trigger>
      <DropdownMenu.Portal>
        <DropdownMenu.Content align="end" sideOffset={6} className="win z-50 min-w-[200px] p-1">
          <div className="px-3 py-2 text-[12px] text-muted">{user.email}</div>
          <DropdownMenu.Item
            onSelect={async () => {
              await logout();
              nav('/');
            }}
            className="flex cursor-pointer items-center gap-2 px-3 py-2 text-[14px] font-semibold outline-none data-[highlighted]:bg-light"
          >
            <LogOut aria-hidden="true" size={16} /> Đăng xuất
          </DropdownMenu.Item>
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  );
}
