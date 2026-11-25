export const API_URL: string =
  (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, '') ??
  'http://localhost:8000/api/v1';

const REFRESH_KEY = 'kotonoha.refresh';

// Access token lives only in memory; refresh token in localStorage.
let accessToken: string | null = null;
type Listener = () => void;
const listeners = new Set<Listener>();

export const tokenStore = {
  get access() {
    return accessToken;
  },
  get refresh(): string | null {
    try {
      return localStorage.getItem(REFRESH_KEY);
    } catch {
      return null;
    }
  },
  set(access: string, refresh: string) {
    accessToken = access;
    try {
      localStorage.setItem(REFRESH_KEY, refresh);
    } catch {
      /* ignore */
    }
    listeners.forEach((l) => l());
  },
  clear() {
    accessToken = null;
    try {
      localStorage.removeItem(REFRESH_KEY);
    } catch {
      /* ignore */
    }
    listeners.forEach((l) => l());
  },
  subscribe(l: Listener) {
    listeners.add(l);
    return () => listeners.delete(l);
  },
};

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public details: unknown = {},
  ) {
    super(message);
  }
}

type QueryValue = string | number | boolean | null | undefined | (string | number)[];
export interface RequestOptions {
  method?: string;
  query?: Record<string, QueryValue>;
  json?: unknown;
  form?: FormData;
  raw?: boolean; // return the Response (downloads)
  auth?: boolean; // default true
  signal?: AbortSignal;
}

export function buildUrl(path: string, query?: Record<string, QueryValue>): string {
  const url = new URL(API_URL + path);
  for (const [k, v] of Object.entries(query ?? {})) {
    if (v === undefined || v === null || v === '') continue;
    if (Array.isArray(v)) v.forEach((x) => url.searchParams.append(k, String(x)));
    else url.searchParams.set(k, String(v));
  }
  return url.toString();
}

let refreshing: Promise<boolean> | null = null;

/** Calls /auth/refresh once (concurrent callers share the same promise). */
export function refreshTokens(): Promise<boolean> {
  const refresh = tokenStore.refresh;
  if (!refresh) return Promise.resolve(false);
  refreshing ??= fetch(API_URL + '/auth/refresh', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: refresh }),
  })
    .then(async (res) => {
      if (!res.ok) {
        tokenStore.clear();
        return false;
      }
      const data = (await res.json()) as { access_token: string; refresh_token: string };
      tokenStore.set(data.access_token, data.refresh_token);
      return true;
    })
    .catch(() => false)
    .finally(() => {
      refreshing = null;
    });
  return refreshing;
}

async function toError(res: Response): Promise<ApiError> {
  let body: unknown = null;
  try {
    body = await res.json();
  } catch {
    /* not json */
  }
  const err = (body as { error?: { code?: string; message?: string; details?: unknown } } | null)?.error;
  return new ApiError(res.status, err?.code ?? 'HTTP_' + res.status, err?.message ?? res.statusText, err?.details);
}

export async function api<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const { method = 'GET', query, json, form, raw, auth = true, signal } = opts;
  const send = () => {
    const headers: Record<string, string> = {};
    if (json !== undefined) headers['Content-Type'] = 'application/json';
    if (auth && accessToken) headers.Authorization = `Bearer ${accessToken}`;
    return fetch(buildUrl(path, query), {
      method,
      headers,
      body: form ?? (json !== undefined ? JSON.stringify(json) : undefined),
      signal,
    });
  };
  let res = await send();
  // On 401: refresh once, then retry once.
  if (res.status === 401 && auth && tokenStore.refresh) {
    if (await refreshTokens()) res = await send();
  }
  if (!res.ok) throw await toError(res);
  if (raw) return res as unknown as T;
  if (res.status === 204) return undefined as T;
  const text = await res.text();
  return (text ? JSON.parse(text) : undefined) as T;
}
