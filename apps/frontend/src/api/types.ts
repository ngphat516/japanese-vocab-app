import type { components } from './schema';

type S = components['schemas'];
export type WordSummary = S['WordSummary'];
export type KanjiPart = S['KanjiPart'];
export type SearchResult = S['SearchResult'];
export type SearchItem = S['SearchItem'];
export type EntryResult = S['EntryResult'];
export type WordDetail = S['WordDetail'];
export type ExamplesResult = S['ExamplesResult'];
export type ExampleItem = S['ExampleItem'];
export type HistoryPage = S['HistoryPage'];
export type HistoryItem = S['HistoryItem'];
export type SavedPage = S['SavedPage'];
export type SavedItem = S['SavedItem'];
export type Source = S['Source'];
export type Profile = S['Profile'];
export type Tokens = S['Tokens'];
export type TextbookOut = S['TextbookOut'];
export type CollectionPage = S['CollectionPage'];

// Content blocks (EntryResult.content is typed as unknown[] in OpenAPI;
// the block schemas below are exported as components).
export type MeaningBlock = S['Meaning'] & { type: 'meaning' };
export type ExampleBlock = S['Example'] & { type: 'example' };
export type UsageBlock = S['Usage'] & { type: 'usage' };
export type CollocationBlock = S['Collocation'] & { type: 'collocation' };
export type RelationBlock = S['Relation'];
export type NoteBlock = S['Note'] & { type: 'note' };
export type RawBlock = S['Raw'] & { type: 'raw' };
export type Block =
  | MeaningBlock
  | ExampleBlock
  | UsageBlock
  | CollocationBlock
  | RelationBlock
  | NoteBlock
  | RawBlock;

// Endpoints whose response is untyped in OpenAPI (see docs/DECISIONS.md).
export interface Paged<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
}

export interface KanjiDetail {
  char: string;
  meaning: string | null;
  strokes: number | null;
  hanviet: string[];
  hanviet_source: string | null;
  jlpt_level: string | null;
  words: Paged<WordSummary>;
}

export interface ImportAdapter {
  name: string;
  formats: string[];
}

export type ImportStatus = string; // pending | parsing | review | commit_pending | committing | committed | failed
export interface ImportJob {
  id: number;
  user_id: number;
  textbook_id: number;
  adapter: string;
  file_key: string;
  status: ImportStatus;
  total: number;
  matched: number;
  ambiguous: number;
  failed: number;
  error: string | null;
  created_at: string;
  updated_at: string;
  progress: { processed: number; total: number };
}

export type MatchStatus = 'auto' | 'ambiguous' | 'none' | 'skipped';
export interface ImportRow {
  id: number;
  job_id: number;
  row_no: number;
  raw: Record<string, unknown>;
  kanji: string;
  kana: string;
  lesson_no: number;
  order_no: number;
  content: unknown[];
  match_status: MatchStatus;
  candidate_word_ids: number[];
  chosen_word_id: number | null;
}

export type JlptLevel = 'N1' | 'N2' | 'N3' | 'N4' | 'N5';
export type SavedStats = Record<JlptLevel | 'none', number>;
export type RelatedItem = S['RelatedItem'];
