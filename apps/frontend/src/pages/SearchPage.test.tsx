import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { AuthProvider } from '@/auth/AuthProvider';
import { ThemeProvider } from '@/theme/ThemeProvider';
import { SearchPage } from './SearchPage';

const word = {
  id: 7,
  kanji: '緊張',
  kana: 'きんちょう',
  romaji: 'kinchou',
  hanviet: 'KHẨN TRƯƠNG',
  hanviet_source: null,
  jlpt_level: 'N3',
  kanji_breakdown: [],
  saved: false,
};

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });

function route(url: string, init?: RequestInit): Response {
  const { pathname } = new URL(url);
  if (pathname.endsWith('/search'))
    return json({
      items: [{ word, entries: [], matched_by: 'exact', appears_in_examples: { count: 0, capped: false } }],
      page: 1,
      size: 20,
      total: 1,
      total_capped: false,
    });
  if (pathname.endsWith('/words/7/examples')) return json({ items: [], total: 0, page: 1, size: 20 });
  if (pathname.endsWith('/words/7')) return json({ word, senses: [{ gloss: 'căng thẳng', lang: 'vie' }], entries: [] });
  return json({ error: { code: 'UNEXPECTED', message: `${init?.method ?? 'GET'} ${pathname}` } }, 500);
}

function LoginProbe() {
  const loc = useLocation();
  return <p data-testid="login">{loc.pathname + loc.search}</p>;
}

function renderAt(path: string) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <ThemeProvider initial="day">
        <AuthProvider>
          <MemoryRouter initialEntries={[path]}>
            <Routes>
              <Route path="/" element={<SearchPage />} />
              <Route path="/login" element={<LoginProbe />} />
            </Routes>
          </MemoryRouter>
        </AuthProvider>
      </ThemeProvider>
    </QueryClientProvider>,
  );
}

let fetchMock: ReturnType<typeof vi.fn>;

beforeEach(() => {
  fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => Promise.resolve(route(String(input), init)));
  vi.stubGlobal('fetch', fetchMock);
});

afterEach(() => vi.unstubAllGlobals());

describe('SearchPage as a guest', () => {
  it('searches without a session and shows results and detail', async () => {
    renderAt('/?q=緊張');
    expect(await screen.findByRole('heading', { level: 3, name: '緊張' })).toBeInTheDocument();
    expect(screen.getByText('《KHẨN TRƯƠNG》')).toBeInTheDocument();
    const calls = fetchMock.mock.calls.map(([u, init]) => [new URL(String(u)), init as RequestInit | undefined] as const);
    const searchCall = calls.find(([u]) => u.pathname.endsWith('/search') && u.searchParams.get('q') === '緊張');
    expect(searchCall).toBeDefined();
    expect(new Headers(searchCall?.[1]?.headers).has('Authorization')).toBe(false);
    expect(screen.queryByText(/Đang tìm/)).toBeNull();
  });

  it('♥ Lưu sends a guest to login with next=<current url> and never calls the API', async () => {
    renderAt('/?q=緊張&w=7');
    await userEvent.click(await screen.findByRole('button', { name: 'Lưu' }));
    expect(screen.getByTestId('login')).toHaveTextContent('/login?next=' + encodeURIComponent('/?q=緊張&w=7'));
    expect(fetchMock.mock.calls.some(([u]) => String(u).includes('/saved-words'))).toBe(false);
  });
});
