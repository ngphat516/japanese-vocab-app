import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { act, render, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { tokenStore } from '@/api/client';
import { AuthProvider } from './AuthProvider';

const profile = { id: 1, email: 'a@example.com', display_name: 'A', role: 'user' };

function setup() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  qc.setQueryData(['search', '緊張', 1], { items: [] });
  qc.setQueryData(['public', 'x'], 1);
  render(
    <QueryClientProvider client={qc}>
      <AuthProvider>
        <span />
      </AuthProvider>
    </QueryClientProvider>,
  );
  return qc;
}

beforeEach(() => {
  vi.stubGlobal(
    'fetch',
    vi.fn(() => Promise.resolve(new Response(JSON.stringify(profile), { status: 200, headers: { 'Content-Type': 'application/json' } }))),
  );
});

afterEach(() => {
  tokenStore.clear();
  vi.unstubAllGlobals();
});

describe('AuthProvider', () => {
  it('a guest mount keeps the cached queries', async () => {
    const qc = setup();
    await act(async () => {});
    expect(qc.getQueryData(['search', '緊張', 1])).toEqual({ items: [] });
  });

  it('losing the session drops user queries but keeps public ones', async () => {
    tokenStore.set('access', 'refresh');
    const qc = setup();
    await waitFor(() => expect(qc.getQueryData(['me'])).toEqual(profile));
    expect(qc.getQueryData(['search', '緊張', 1])).toBeDefined();

    act(() => tokenStore.clear());
    await waitFor(() => expect(qc.getQueryData(['search', '緊張', 1])).toBeUndefined());
    expect(qc.getQueryData(['me'])).toBeUndefined();
    expect(qc.getQueryData(['public', 'x'])).toBe(1);
  });
});
