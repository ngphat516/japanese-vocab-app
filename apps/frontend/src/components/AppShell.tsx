import { BookOpen, Repeat, Search, User } from 'lucide-react';
import { useMemo, type ReactNode } from 'react';
import { NavLink, Outlet, useLocation } from 'react-router-dom';
import { clsx } from 'clsx';
import { useAuth } from '@/auth/AuthProvider';
import { seeded } from '@/lib/random';
import { useTheme } from '@/theme/ThemeProvider';
import { AccountMenu } from './AccountMenu';
import { Logo } from './Logo';
import { PixelImage, themeAsset } from './PixelImage';
import { ThemePicker } from './ThemePicker';

const NAV = [
  { to: '/', label: 'Tra từ', end: true },
  { to: '/notebook', label: 'Sổ từ' },
  { to: '/import', label: 'Import' },
];

function Header() {
  return (
    <header className="mx-auto flex max-w-[1240px] flex-wrap items-center gap-x-6 gap-y-3 px-4 py-[18px] md:px-6">
      <NavLink to="/" className="border-2 border-ink bg-card px-3 py-[6px] text-ink no-underline shadow-block-sm hover:text-ink">
        <Logo />
      </NavLink>
      <nav aria-label="Điều hướng chính" className="hidden flex-grow flex-wrap gap-[6px] text-[14px] font-semibold md:flex">
        {NAV.map((n) => (
          <NavLink
            key={n.to}
            to={n.to}
            end={n.end}
            className={({ isActive }) =>
              clsx('px-3 py-1 uppercase no-underline', isActive ? 'bg-ink text-card hover:text-card' : 'text-ink')
            }
          >
            {n.label}
          </NavLink>
        ))}
        <span aria-disabled="true" title="Sắp có" className="cursor-not-allowed px-3 py-1 uppercase text-muted">
          Ôn tập · Sắp có
        </span>
      </nav>
      <div className="flex flex-grow flex-wrap items-center justify-end gap-3 md:flex-grow-0">
        <ThemePicker />
        <div className="hidden md:block">
          <AccountMenu />
        </div>
      </div>
    </header>
  );
}

function Particles({ theme, count = 20 }: { theme: string; count?: number }) {
  const items = useMemo(() => {
    const rand = seeded(20260417);
    return Array.from({ length: count }, (_, i) => ({
      key: i,
      left: rand() * 98,
      top: rand() * 130,
      file: `particle-${1 + Math.floor(rand() * 4)}.svg`,
    }));
  }, [count]);
  return (
    <div aria-hidden="true" className="pointer-events-none absolute inset-0 opacity-[.35]">
      {items.map((p) => (
        <PixelImage key={p.key} src={themeAsset(theme, p.file)} className="absolute" style={{ left: `${p.left}%`, top: p.top }} />
      ))}
    </div>
  );
}

function Footer() {
  const { theme, t } = useTheme();
  const strip = themeAsset(theme, 'strip.svg');
  return (
    <footer className="mt-12 flex flex-grow flex-col">
      <div
        aria-hidden="true"
        className="pixel mx-auto w-full max-w-[1240px] px-4 md:px-6"
        style={{ backgroundImage: `url(${strip})`, backgroundRepeat: 'repeat-x', backgroundPosition: 'left bottom', backgroundOrigin: 'content-box', backgroundClip: 'content-box' }}
      >
        {/* invisible copy gives the strip row its natural height */}
        <PixelImage src={strip} className="invisible block" />
      </div>
      <div className="h-1 bg-ink" />
      <div className="relative flex flex-grow flex-col overflow-hidden bg-light">
        <Particles theme={theme} />
        <div className="relative mx-auto box-border flex w-full max-w-[1240px] flex-wrap items-center gap-x-12 gap-y-6 px-4 py-7 text-[13px] text-muted md:px-6">
          <div className="flex-[1_1_260px]">
            <div className="text-[15px] text-ink">
              <Logo size={15} />
            </div>
            <div className="mt-1">Tra một từ, đọc mọi giáo trình.</div>
          </div>
          <nav aria-label="Liên kết chân trang" className="flex flex-wrap gap-5">
            {['Giới thiệu', 'Nguồn dữ liệu', 'Góp ý'].map((l) => (
              <a key={l} href="#" className="text-muted hover:text-acc">
                {l}
              </a>
            ))}
            <a href="https://github.com/ngphat516/japanese-vocab-app" className="text-muted hover:text-acc" target="_blank" rel="noreferrer">
              GitHub
            </a>
          </nav>
          <div className="flex items-center gap-2">
            <span lang="ja" className="font-serif text-[16px] text-ink">
              {t.footer.ja}
            </span>
            <span>· {t.footer.vi}</span>
          </div>
        </div>
        <div className="relative mt-auto">
          <PixelImage
            src={themeAsset(theme, 'landscape.svg')}
            className="block h-[240px] w-full object-cover"
            style={{ objectPosition: 'bottom' }}
          />
        </div>
      </div>
    </footer>
  );
}

function MobileNav() {
  const { user } = useAuth();
  const loc = useLocation();
  const item = (active: boolean) =>
    clsx(
      'flex flex-col items-center justify-center gap-1 text-[12px] no-underline',
      active ? 'bg-ink font-semibold text-card hover:text-card' : 'text-ink',
    );
  return (
    <nav
      aria-label="Điều hướng dưới"
      className="fixed inset-x-0 bottom-0 z-40 grid h-[68px] grid-cols-4 border-t-2 border-ink bg-card md:hidden"
    >
      <NavLink to="/" end className={({ isActive }) => item(isActive)}>
        <Search aria-hidden="true" size={22} /> Tra từ
      </NavLink>
      <NavLink to="/notebook" className={({ isActive }) => item(isActive)}>
        <BookOpen aria-hidden="true" size={22} /> Sổ từ
      </NavLink>
      <span aria-disabled="true" title="Sắp có" className={clsx(item(false), 'cursor-not-allowed text-muted')}>
        <Repeat aria-hidden="true" size={22} /> Ôn tập
      </span>
      <NavLink
        to={user ? '/account' : `/login?next=${encodeURIComponent(loc.pathname + loc.search)}`}
        className={({ isActive }) => item(isActive || loc.pathname === '/login')}
      >
        <User aria-hidden="true" size={22} /> Tài khoản
      </NavLink>
    </nav>
  );
}

export function AppShell({ children }: { children?: ReactNode }) {
  return (
    <div className="relative flex min-h-screen flex-col overflow-x-hidden pb-[68px] md:pb-0">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-50 focus:bg-card focus:p-2">
        Bỏ qua tới nội dung
      </a>
      <Header />
      <div id="main" className="flex-shrink-0">
        {children ?? <Outlet />}
      </div>
      <Footer />
      <MobileNav />
    </div>
  );
}
