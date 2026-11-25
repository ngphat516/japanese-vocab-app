import { lazy, Suspense } from 'react';
import { Route, Routes } from 'react-router-dom';
import { RequireAuth } from '@/auth/RequireAuth';
import { AppShell } from '@/components/AppShell';
import { SearchPage } from '@/pages/SearchPage';
import { LoginPage, RegisterPage } from '@/pages/AuthPages';
import { AccountPage } from '@/pages/AccountPage';
import { NotFoundPage } from '@/pages/NotFoundPage';

const NotebookPage = lazy(() => import('@/pages/NotebookPage'));
const ImportPage = lazy(() => import('@/pages/ImportPage'));

const loading = <p className="mx-auto max-w-[1240px] px-6 py-10 text-muted">Đang tải…</p>;

export function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<SearchPage />} />
        <Route path="login" element={<LoginPage />} />
        <Route path="register" element={<RegisterPage />} />
        <Route path="account" element={<RequireAuth><AccountPage /></RequireAuth>} />
        <Route
          path="notebook"
          element={<RequireAuth><Suspense fallback={loading}><NotebookPage /></Suspense></RequireAuth>}
        />
        <Route
          path="import"
          element={<RequireAuth><Suspense fallback={loading}><ImportPage /></Suspense></RequireAuth>}
        />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
