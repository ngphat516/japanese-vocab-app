import { api } from './client';
import type {
  CollectionPage,
  ExamplesResult,
  HistoryPage,
  ImportAdapter,
  ImportJob,
  ImportRow,
  JlptLevel,
  KanjiDetail,
  MatchStatus,
  Paged,
  Profile,
  SavedItem,
  SavedPage,
  SavedStats,
  SearchResult,
  TextbookOut,
  Tokens,
  WordDetail,
} from './types';

export const auth = {
  login: (email: string, password: string) =>
    api<Tokens>('/auth/login', { method: 'POST', json: { email, password }, auth: false }),
  register: (email: string, password: string, display_name: string) =>
    api<Profile>('/auth/register', { method: 'POST', json: { email, password, display_name }, auth: false }),
  logout: (refresh_token: string) =>
    api<unknown>('/auth/logout', { method: 'POST', json: { refresh_token }, auth: false }),
  me: () => api<Profile>('/me'),
};

export const search = (q: string, page = 1, size = 20, signal?: AbortSignal) =>
  api<SearchResult>('/search', { query: { q, page, size }, signal });

export const word = (id: number) => api<WordDetail>(`/words/${id}`);
export const wordExamples = (id: number, page = 1, size = 20) =>
  api<ExamplesResult>(`/words/${id}/examples`, { query: { page, size } });
export const kanji = (char: string) => api<KanjiDetail>(`/kanji/${encodeURIComponent(char)}`, { query: { size: 8 } });

export const history = (page = 1, size = 10) => api<HistoryPage>('/history', { query: { page, size } });

export interface SavedFilter {
  jlpt?: JlptLevel | 'none';
  tag?: string;
  textbook_id?: number;
  collection_id?: number;
}

export const saved = {
  list: (f: SavedFilter & { page?: number; size?: number }) =>
    api<SavedPage>('/saved-words', {
      // "none" (Ngoài JLPT) has no server-side filter; the caller filters locally.
      query: { ...f, jlpt: f.jlpt === 'none' ? undefined : f.jlpt },
    }),
  stats: () => api<SavedStats>('/saved-words/stats'),
  save: (word_id: number) => api<SavedItem>('/saved-words', { method: 'POST', json: { word_id } }),
  remove: (saved_id: number) => api<unknown>(`/saved-words/${saved_id}`, { method: 'DELETE' }),
  export: (format: 'anki' | 'csv' | 'markdown', f: Omit<SavedFilter, 'textbook_id'>) =>
    api<Response>('/saved-words/export', {
      raw: true,
      query: { format, collection_id: f.collection_id, tag: f.tag, jlpt: f.jlpt === 'none' ? undefined : f.jlpt },
    }),
};

export const collections = () => api<CollectionPage>('/collections', { query: { size: 100 } });
export const textbooks = () => api<Paged<TextbookOut>>('/textbooks', { query: { size: 100 } });

export const imports = {
  adapters: () => api<ImportAdapter[]>('/imports/adapters'),
  template: () => api<Response>('/imports/template', { raw: true }),
  upload: (form: FormData) => api<ImportJob>('/imports', { method: 'POST', form }),
  job: (id: number) => api<ImportJob>(`/imports/${id}`),
  rows: (id: number, match_status?: MatchStatus, page = 1, size = 20) =>
    api<Paged<ImportRow>>(`/imports/${id}/rows`, { query: { match_status, page, size } }),
  review: (id: number, rowId: number, body: { chosen_word_id: number } | { skipped: true }) =>
    api<ImportRow>(`/imports/${id}/rows/${rowId}`, { method: 'PATCH', json: body }),
  commit: (id: number) => api<ImportJob & Record<string, unknown>>(`/imports/${id}/commit`, { method: 'POST' }),
};

/** Triggers a browser download for a fetch Response. */
export async function downloadResponse(res: Response, fallbackName: string) {
  const blob = await res.blob();
  const cd = res.headers.get('Content-Disposition') ?? '';
  const star = /filename\*=UTF-8''([^;]+)/i.exec(cd)?.[1];
  const plain = /filename="?([^";]+)"?/i.exec(cd)?.[1];
  const name = star ? decodeURIComponent(star) : (plain ?? fallbackName);
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = name;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
