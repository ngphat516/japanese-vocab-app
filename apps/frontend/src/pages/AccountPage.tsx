import { LogOut } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/auth/AuthProvider';
import { ThemePicker } from '@/components/ThemePicker';
import { Window } from '@/components/Window';

/** Mobile "Tài khoản" tab: profile, theme, logout. */
export function AccountPage() {
  const { user, logout } = useAuth();
  const nav = useNavigate();
  return (
    <main className="mx-auto max-w-[640px] px-4 pt-6">
      <Window title="Tài khoản" bodyClassName="p-6 flex flex-col gap-5">
        <div>
          <div className="text-[18px] font-bold">{user?.display_name || 'Bạn'}</div>
          <div className="text-muted">{user?.email}</div>
        </div>
        <ThemePicker />
        <button
          type="button"
          className="btn btn-secondary self-start"
          onClick={async () => {
            await logout();
            nav('/');
          }}
        >
          <LogOut aria-hidden="true" size={16} /> Đăng xuất
        </button>
      </Window>
    </main>
  );
}
