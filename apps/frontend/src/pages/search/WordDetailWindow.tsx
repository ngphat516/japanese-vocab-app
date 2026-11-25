import * as Tabs from '@radix-ui/react-tabs';
import { useInfiniteQuery, useQuery } from '@tanstack/react-query';
import { ArrowLeft, Heart } from 'lucide-react';
import { useState } from 'react';
import { clsx } from 'clsx';
import { word, wordExamples } from '@/api/endpoints';
import type { EntryResult, ExampleItem, WordDetail } from '@/api/types';
import { useAuth } from '@/auth/AuthProvider';
import { BlockRenderer, circled } from '@/components/blocks/BlockRenderer';
import { JlptBadge } from '@/components/JlptBadge';
import { Ruby } from '@/components/ruby/Ruby';
import { ErrorNote, Loading } from '@/components/Status';
import { Window } from '@/components/Window';
import { useLocalBool } from '@/hooks/useLocalBool';
import { useSaveToggle } from '@/hooks/useSaveToggle';
import { KanjiChip } from './KanjiChip';

interface MeaningLike {
  type?: string;
  vi?: string | null;
  en?: string | null;
}

/** Headline meaning: first Vietnamese meaning block, else JMdict sense, else entry summary. */
export function headlineMeaning(d: WordDetail): string {
  for (const e of d.entries) {
    for (const b of (e.content ?? []) as MeaningLike[]) if (b?.type === 'meaning' && b.vi) return b.vi;
  }
  const senses = d.senses as { lang?: string; gloss?: string }[];
  const vi = senses.filter((s) => s.lang === 'vi' || s.lang === 'vie').map((s) => s.gloss);
  if (vi.length) return vi.slice(0, 3).join('; ');
  const en = senses.filter((s) => s.gloss).map((s) => s.gloss);
  if (en.length) return en.slice(0, 3).join('; ');
  return d.entries[0]?.summary ?? '';
}

const EXAMPLES_TAB = '__examples';

function EntryPanel({ entry }: { entry: EntryResult }) {
  return (
    <div className="flex flex-col gap-3">
      <div className="text-[12px] uppercase text-muted">
        #{entry.order_no} · {entry.lesson}
      </div>
      {entry.content?.length ? <BlockRenderer blocks={entry.content} /> : <p className="m-0 text-muted">{entry.summary}</p>}
    </div>
  );
}

function ExampleSource({ item }: { item: ExampleItem }) {
  return (
    <div className="text-[12px] text-muted">
      {item.textbook} · {item.lesson} #{item.order_no} ·{' '}
      <span lang="ja" className="jp">{item.source_word.kanji || item.source_word.kana}</span>
    </div>
  );
}

function ExamplesPanel({ wordId }: { wordId: number }) {
  const q = useInfiniteQuery({
    queryKey: ['word', wordId, 'examples'],
    queryFn: ({ pageParam }) => wordExamples(wordId, pageParam, 20),
    initialPageParam: 1,
    getNextPageParam: (last) => (last.page * last.size < last.total ? last.page + 1 : undefined),
  });
  if (q.isPending) return <Loading />;
  if (q.isError) return <ErrorNote error={q.error} />;
  const items = q.data.pages.flatMap((p) => p.items);
  if (!items.length) return <p className="m-0 text-muted">Chưa có ví dụ từ giáo trình khác.</p>;
  let n = 0;
  return (
    <div className="flex flex-col gap-4">
      {items.map((it) => (
        <div key={it.entry_id} className="flex flex-col gap-1 border-b-2 border-dashed border-light pb-3">
          {it.sentences.map((s, j) => {
            n += 1;
            return (
              <div key={j}>
                <div className="jp text-[18px] leading-[2.1]">
                  <span aria-hidden="true">{circled(n)} </span>
                  <Ruby text={s.ja} />
                </div>
                {s.vi && <div className="text-muted">→ {s.vi}</div>}
              </div>
            );
          })}
          <ExampleSource item={it} />
        </div>
      ))}
      {q.hasNextPage && (
        <button type="button" className="btn btn-secondary btn-sm self-start" disabled={q.isFetchingNextPage} onClick={() => q.fetchNextPage()}>
          {q.isFetchingNextPage ? 'Đang tải…' : 'Xem thêm ví dụ'}
        </button>
      )}
    </div>
  );
}

const tabClass = (dashed = false) =>
  clsx(
    'border-2 border-ink bg-card px-[14px] py-1 text-[13px] font-bold uppercase text-ink',
    'data-[state=active]:bg-ink data-[state=active]:text-card',
    dashed && 'border-dashed',
  );

export function WordDetailView({ data, examplesCount }: { data: WordDetail; examplesCount?: number }) {
  const { user } = useAuth();
  const w = data.word;
  const toggle = useSaveToggle();
  const [furigana, setFurigana] = useLocalBool('kotonoha.furigana', true);
  const ex = useQuery({
    queryKey: ['word', w.id, 'examples-count'],
    queryFn: () => wordExamples(w.id, 1, 1),
    enabled: examplesCount === undefined,
  });
  const count = examplesCount ?? ex.data?.total ?? 0;
  const firstTab = data.entries.length ? `e0` : EXAMPLES_TAB;
  const [tab, setTab] = useState(firstTab);
  const activeTab = tab === EXAMPLES_TAB || Number(tab.slice(1)) < data.entries.length ? tab : firstTab;
  const meaning = headlineMeaning(data);
  const saved = Boolean(w.saved);

  return (
    <div className={clsx('flex flex-col gap-[18px] px-5 py-6 md:px-7', !furigana && 'hide-furigana')}>
      <div className="flex flex-wrap items-start gap-4">
        <div className="min-w-0 flex-grow">
          <div lang="ja" className="jp text-muted">
            {w.kana} · <span lang="en" className="font-ui">{w.romaji}</span>
          </div>
          <div className="flex flex-wrap items-center gap-[14px]">
            <h3 lang="ja" className="m-0 break-all font-serif text-[40px] font-bold leading-[1.2] md:text-[52px]">
              {w.kanji || w.kana}
            </h3>
            <JlptBadge level={w.jlpt_level} />
          </div>
          {w.hanviet && <div className="font-bold uppercase tracking-[0.04em] text-acc">《{w.hanviet.toUpperCase()}》</div>}
        </div>
        {user && (
          <button
            type="button"
            className={clsx('btn', saved ? 'btn-secondary' : 'btn-primary')}
            aria-pressed={saved}
            disabled={toggle.isPending}
            onClick={() => toggle.mutate({ wordId: w.id, save: !saved })}
          >
            <Heart aria-hidden="true" size={16} fill={saved ? 'currentColor' : 'none'} />
            {saved ? 'Đã lưu' : 'Lưu'}
          </button>
        )}
      </div>
      {toggle.isError && <ErrorNote error={toggle.error} />}

      <div className="flex flex-wrap items-center gap-[10px]">
        {meaning && <span className="text-[16px] font-semibold">{meaning}</span>}
        {w.kanji_breakdown.map((p, i) => (
          <KanjiChip key={`${p.char}-${i}`} part={p} />
        ))}
      </div>

      <Tabs.Root value={activeTab} onValueChange={setTab} className="flex flex-col gap-4">
        <div className="flex flex-wrap items-center gap-2">
          <Tabs.List aria-label="Giáo trình" className="flex flex-grow flex-wrap gap-[6px]">
            {data.entries.map((e, i) => (
              <Tabs.Trigger key={i} value={`e${i}`} className={tabClass()}>
                {e.textbook}
              </Tabs.Trigger>
            ))}
            <Tabs.Trigger value={EXAMPLES_TAB} className={tabClass(true)}>
              +{count} ví dụ
            </Tabs.Trigger>
          </Tabs.List>
          <label className="flex cursor-pointer items-center gap-2 text-[13px] font-semibold">
            <input type="checkbox" checked={furigana} onChange={(e) => setFurigana(e.target.checked)} className="h-4 w-4 accent-[var(--ink)]" />
            Furigana
          </label>
        </div>
        {data.entries.map((e, i) => (
          <Tabs.Content key={i} value={`e${i}`} className="outline-none">
            <EntryPanel entry={e} />
          </Tabs.Content>
        ))}
        <Tabs.Content value={EXAMPLES_TAB} className="outline-none">
          {activeTab === EXAMPLES_TAB && <ExamplesPanel wordId={w.id} />}
        </Tabs.Content>
      </Tabs.Root>
    </div>
  );
}

export function WordDetailWindow({
  wordId,
  examplesCount,
  onBack,
  className,
}: {
  wordId: number;
  examplesCount?: number;
  onBack?: () => void;
  className?: string;
}) {
  const q = useQuery({ queryKey: ['word', wordId], queryFn: () => word(wordId) });
  return (
    <Window
      title="Chi tiết từ"
      labelId="detail-title"
      className={className}
      actions={
        onBack && (
          <button type="button" onClick={onBack} className="flex items-center gap-1 text-[12px] font-bold md:hidden" aria-label="Quay lại kết quả">
            <ArrowLeft aria-hidden="true" size={16} /> Kết quả
          </button>
        )
      }
    >
      {q.isPending ? <Loading /> : q.isError ? <div className="p-4"><ErrorNote error={q.error} /></div> : <WordDetailView key={wordId} data={q.data} examplesCount={examplesCount} />}
    </Window>
  );
}
