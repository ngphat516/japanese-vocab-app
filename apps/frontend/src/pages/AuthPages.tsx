import { useState, type FormEvent, type ReactNode } from 'react';
import { Link, Navigate, useNavigate, useSearchParams } from 'react-router-dom';
import { z } from 'zod';
import { ApiError } from '@/api/client';
import { useAuth } from '@/auth/AuthProvider';
import { PixelImage, themeAsset } from '@/components/PixelImage';
import { Window } from '@/components/Window';
import { useTheme } from '@/theme/ThemeProvider';

export const loginSchema = z.object({
  email: z.string().trim().email('Email không hợp lệ'),
  password: z.string().min(1, 'Nhập mật khẩu'),
});

export const registerSchema = z
  .object({
    display_name: z.string().trim().max(100, 'Tối đa 100 ký tự'),
    email: z.string().trim().email('Email không hợp lệ'),
    password: z.string().min(8, 'Mật khẩu tối thiểu 8 ký tự').max(128, 'Tối đa 128 ký tự'),
    confirm: z.string(),
  })
  .refine((v) => v.password === v.confirm, { path: ['confirm'], message: 'Mật khẩu nhập lại không khớp' });

type Errors = Record<string, string | undefined>;

/** Only allow in-app redirects. */
export function safeNext(next: string | null): string {
  return next && next.startsWith('/') && !next.startsWith('//') ? next : '/';
}

function Field({
  name,
  label,
  type = 'text',
  error,
  autoComplete,
}: {
  name: string;
  label: string;
  type?: string;
  error?: string;
  autoComplete?: string;
}) {
  const id = `f-${name}`;
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="label">
        {label}
      </label>
      <input
        id={id}
        name={name}
        type={type}
        autoComplete={autoComplete}
        aria-invalid={Boolean(error)}
        aria-describedby={error ? `${id}-err` : undefined}
        className="field"
      />
      {error && (
        <span id={`${id}-err`} className="text-[13px] font-semibold text-[var(--jlpt-n1-fg)]">
          {error}
        </span>
      )}
    </div>
  );
}

function AuthCard({ title, children }: { title: string; children: ReactNode }) {
  const { theme } = useTheme();
  return (
    <main className="mx-auto flex max-w-[480px] flex-col px-4 pt-6">
      <Window title={title}>
        <div className="relative h-[120px] overflow-hidden border-b-2 border-ink bg-scene">
          <PixelImage src={themeAsset(theme, 'hero.svg')} className="absolute inset-0 h-full w-full object-cover" style={{ objectPosition: 'bottom' }} />
        </div>
        <div className="flex flex-col gap-4 p-6">{children}</div>
      </Window>
    </main>
  );
}

function formErrors(issues: z.core.$ZodIssue[]): Errors {
  const out: Errors = {};
  for (const i of issues) {
    const k = String(i.path[0] ?? 'form');
    out[k] ??= i.message;
  }
  return out;
}

function apiMessage(err: unknown, fallback: string): string {
  if (err instanceof ApiError) {
    if (err.status === 401) return 'Sai email hoặc mật khẩu.';
    if (err.status === 429) return 'Thử quá nhiều lần, vui lòng đợi một lát.';
    return err.message || fallback;
  }
  return 'Không kết nối được máy chủ.';
}

export function LoginPage() {
  const { user, login } = useAuth();
  const [params] = useSearchParams();
  const nav = useNavigate();
  const next = safeNext(params.get('next'));
  const [errors, setErrors] = useState<Errors>({});
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to={next} replace />;

  const onSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const parsed = loginSchema.safeParse(Object.fromEntries(new FormData(e.currentTarget)));
    if (!parsed.success) return setErrors(formErrors(parsed.error.issues));
    setErrors({});
    setBusy(true);
    try {
      await login(parsed.data.email, parsed.data.password);
      nav(next, { replace: true });
    } catch (err) {
      setErrors({ form: apiMessage(err, 'Đăng nhập thất bại.') });
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthCard title="Đăng nhập">
      <form noValidate onSubmit={onSubmit} className="flex flex-col gap-4">
        <Field name="email" label="Email" type="email" autoComplete="email" error={errors.email} />
        <Field name="password" label="Mật khẩu" type="password" autoComplete="current-password" error={errors.password} />
        {errors.form && (
          <p role="alert" className="m-0 border-l-4 border-[var(--jlpt-n1-fg)] pl-3 font-semibold">
            {errors.form}
          </p>
        )}
        <button type="submit" className="btn btn-primary" disabled={busy}>
          {busy ? 'Đang đăng nhập…' : 'Đăng nhập'}
        </button>
      </form>
      <p className="m-0 text-muted">
        Chưa có tài khoản?{' '}
        <Link to={`/register${params.get('next') ? `?next=${encodeURIComponent(next)}` : ''}`} className="font-bold text-ink">
          Đăng ký
        </Link>
      </p>
    </AuthCard>
  );
}

export function RegisterPage() {
  const { user, register } = useAuth();
  const [params] = useSearchParams();
  const nav = useNavigate();
  const next = safeNext(params.get('next'));
  const [errors, setErrors] = useState<Errors>({});
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to={next} replace />;

  const onSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const parsed = registerSchema.safeParse(Object.fromEntries(new FormData(e.currentTarget)));
    if (!parsed.success) return setErrors(formErrors(parsed.error.issues));
    setErrors({});
    setBusy(true);
    try {
      await register(parsed.data.email, parsed.data.password, parsed.data.display_name);
      nav(next, { replace: true });
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) setErrors({ email: 'Email này đã được đăng ký.' });
      else setErrors({ form: apiMessage(err, 'Đăng ký thất bại.') });
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthCard title="Đăng ký">
      <form noValidate onSubmit={onSubmit} className="flex flex-col gap-4">
        <Field name="display_name" label="Tên hiển thị" autoComplete="nickname" error={errors.display_name} />
        <Field name="email" label="Email" type="email" autoComplete="email" error={errors.email} />
        <Field name="password" label="Mật khẩu" type="password" autoComplete="new-password" error={errors.password} />
        <Field name="confirm" label="Nhập lại mật khẩu" type="password" autoComplete="new-password" error={errors.confirm} />
        {errors.form && (
          <p role="alert" className="m-0 border-l-4 border-[var(--jlpt-n1-fg)] pl-3 font-semibold">
            {errors.form}
          </p>
        )}
        <button type="submit" className="btn btn-primary" disabled={busy}>
          {busy ? 'Đang tạo tài khoản…' : 'Tạo tài khoản'}
        </button>
      </form>
      <p className="m-0 text-muted">
        Đã có tài khoản?{' '}
        <Link to={`/login${params.get('next') ? `?next=${encodeURIComponent(next)}` : ''}`} className="font-bold text-ink">
          Đăng nhập
        </Link>
      </p>
    </AuthCard>
  );
}
