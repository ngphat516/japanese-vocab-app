import { Link } from 'react-router-dom';
import { clsx } from 'clsx';
import type { SearchResult } from '@/api/types';
import { JlptBadge } from '@/components/JlptBadge';
import { Pager } from '@/components/Pager';
import { ErrorNote, Loading } from '@/components/Status';
import { Window } from '@/components/Window';

interface Props {
  data: SearchResult | undefined;
  isPending: boolean;
  error: unknown;
  selectedId: number | undefined;
  hrefFor: (wordId: number) => string;
  page: number;
  onPage: (p: number) => void;
  className?: string;
}

export function ResultsWindow({ data, isPending, error, selectedId, hrefFor, page, onPage, className }: Props) {
  const total = data?.total ?? 0;
  return (
    <Window
      title={`Kết quả (${data ? `${total}${data.total_capped ? '+' : ''}` : '…'})`}
      labelId="results-title"
      className={className}
    >
      {isPending ? (
        <Loading text="Đang tìm…" />
      ) : error ? (
        <div className="p-4"><ErrorNote error={error} /></div>
      ) : !data?.items.length ? (
        <p className="m-0 p-5 text-muted">Không tìm thấy từ nào. Thử kana, romaji hoặc nghĩa tiếng Việt.</p>
      ) : (
        <>
          <ul className="m-0 list-none p-0">
            {data.items.map((it, i) => {
              const active = it.word.id === selectedId;
              const summary = it.entries[0]?.summary;
              return (
                <li key={it.word.id} className={clsx(i > 0 && 'border-t-2 border-dashed border-light')}>
                  <Link
                    to={hrefFor(it.word.id)}
                    replace
                    aria-current={active ? 'true' : undefined}
                    className={clsx(
                      'flex items-center gap-[10px] border-l-[6px] px-[14px] py-3 text-ink no-underline hover:bg-light hover:text-ink',
                      active ? 'border-acc bg-light' : 'border-transparent',
                    )}
                  >
                    <div className="min-w-0 flex-grow">
                      <div lang="ja" className="jp text-[17px] font-medium">{it.word.kanji || it.word.kana}</div>
                      <div className="truncate text-[12px] text-muted">
                        <span lang="ja" className="jp">{it.word.kana}</span>
                        {summary ? ` · ${summary}` : it.word.hanviet ? ` · ${it.word.hanviet}` : ''}
                      </div>
                    </div>
                    <JlptBadge level={it.word.jlpt_level} />
                  </Link>
                </li>
              );
            })}
          </ul>
          <Pager page={page} size={data.size} total={data.total} onPage={onPage} />
        </>
      )}
    </Window>
  );
}
