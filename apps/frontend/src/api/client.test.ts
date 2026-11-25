import { afterEach, describe, expect, it, vi } from 'vitest';
import { api, ApiError, buildUrl, tokenStore } from './client';

const json = (status: number, body: unknown) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });

afterEach(() => {
  vi.restoreAllMocks();
  tokenStore.clear();
});

describe('api client', () => {
  it('buildUrl skips empty values and repeats arrays', () => {
    const u = new URL(buildUrl('/search', { q: '緊張', page: 1, jlpt: undefined, tag: '', ids: [1, 2] }));
    expect(u.pathname.endsWith('/search')).toBe(true);
    expect(u.searchParams.get('q')).toBe('緊張');
    expect(u.searchParams.has('jlpt')).toBe(false);
    expect(u.searchParams.has('tag')).toBe(false);
    expect(u.searchParams.getAll('ids')).toEqual(['1', '2']);
  });

  it('keeps the refresh token in localStorage and the access token only in memory', () => {
    tokenStore.set('acc', 'ref');
    expect(localStorage.getItem('kotonoha.refresh')).toBe('ref');
    expect(JSON.stringify(localStorage)).not.toContain('acc');
    expect(tokenStore.access).toBe('acc');
  });

  it('on 401 refreshes once and retries with the new token', async () => {
    tokenStore.set('old', 'ref1');
    const fetchMock = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(json(401, { error: { code: 'TOKEN_EXPIRED', message: 'x' } }))
      .mockResolvedValueOnce(json(200, { access_token: 'new', refresh_token: 'ref2' }))
      .mockResolvedValueOnce(json(200, { id: 1 }));
    await expect(api('/me')).resolves.toEqual({ id: 1 });
    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(String(fetchMock.mock.calls[1]![0])).toContain('/auth/refresh');
    const retryHeaders = fetchMock.mock.calls[2]![1]!.headers as Record<string, string>;
    expect(retryHeaders.Authorization).toBe('Bearer new');
    expect(tokenStore.refresh).toBe('ref2');
  });

  it('does not loop: a second 401 after refresh is surfaced as an error', async () => {
    tokenStore.set('old', 'ref1');
    const fetchMock = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(json(401, {}))
      .mockResolvedValueOnce(json(200, { access_token: 'new', refresh_token: 'ref2' }))
      .mockResolvedValueOnce(json(401, { error: { code: 'AUTH_REQUIRED', message: 'Cần đăng nhập' } }));
    await expect(api('/me')).rejects.toMatchObject({ status: 401, code: 'AUTH_REQUIRED' });
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });

  it('clears the session when refresh fails', async () => {
    tokenStore.set('old', 'ref1');
    vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(json(401, {}))
      .mockResolvedValueOnce(json(401, {}));
    await expect(api('/me')).rejects.toBeInstanceOf(ApiError);
    expect(tokenStore.refresh).toBeNull();
    expect(tokenStore.access).toBeNull();
  });
});
