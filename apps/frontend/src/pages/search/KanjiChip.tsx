import * as Popover from '@radix-ui/react-popover';
import { useQuery } from '@tanstack/react-query';
import { X } from 'lucide-react';
import { Link } from 'react-router-dom';
import { kanji } from '@/api/endpoints';
import type { KanjiPart } from '@/api/types';
import { JlptBadge } from '@/components/JlptBadge';
import { ErrorNote, Loading } from '@/components/Status';

function KanjiPanel({ char }: { char: string }) {
  const q = useQuery({ queryKey: ['kanji', char], queryFn: () => kanji(char), staleTime: 10 * 60_000 });
  if (q.isPending) return <Loading />;
  if (q.isError) return <div className="p-3"><ErrorNote error={q.error} /></div>;
  const k = q.data;
  return (
    <div className="flex flex-col gap-3 p-4">
      <div className="flex items-start gap-4">
        <span lang="ja" className="font-serif text-[48px] font-bold leading-none">{k.char}</span>
        <div className="flex flex-col gap-1">
          <span className="font-bold uppercase tracking-[0.04em] text-acc">
            {k.hanviet.length ? `《${k.hanviet.join(' · ').toUpperCase()}》` : '《—》'}
          </span>
          {k.meaning && <span className="text-ink">{k.meaning}</span>}
          <span className="flex flex-wrap items-center gap-2 text-[12px] text-muted">
            {k.strokes ? <span>{k.strokes} nét</span> : null}
            {k.jlpt_level ? <JlptBadge level={k.jlpt_level} /> : null}
          </span>
        </div>
      </div>
      {k.words.items.length > 0 && (
        <div>
          <div className="eyebrow mb-1">Từ có chữ này ({k.words.total})</div>
          <ul className="m-0 flex list-none flex-col p-0">
            {k.words.items.map((w) => (
              <li key={w.id}>
                <Popover.Close asChild>
                  <Link to={`/?w=${w.id}`} className="flex items-baseline gap-2 py-1 no-underline hover:bg-light">
                    <span lang="ja" className="jp text-[16px]">{w.kanji || w.kana}</span>
                    <span className="jp text-[12px] text-muted">{w.kana}</span>
                    {w.hanviet && <span className="text-[12px] text-muted">{w.hanviet}</span>}
                  </Link>
                </Popover.Close>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

/** Chip for one kanji of the head word; opens a popover with GET /kanji/{char}. */
export function KanjiChip({ part }: { part: KanjiPart }) {
  return (
    <Popover.Root>
      <Popover.Trigger className="chip-btn" aria-label={`Chữ ${part.char} – ${part.hanviet || 'không rõ Hán Việt'}`}>
        <span lang="ja" className="jp">{part.char}</span> {part.hanviet.toUpperCase()}
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Content sideOffset={8} align="start" collisionPadding={12} className="win z-50 w-[320px] max-w-[calc(100vw-24px)]">
          <div className="flex items-center border-b-2 border-ink bg-light px-[10px] py-[6px]">
            <span className="flex-grow text-[13px] font-bold uppercase tracking-[0.06em]">Chữ Hán</span>
            <Popover.Close aria-label="Đóng" className="flex h-6 w-6 items-center justify-center border-2 border-ink bg-card">
              <X aria-hidden="true" size={14} />
            </Popover.Close>
          </div>
          <KanjiPanel char={part.char} />
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  );
}
