import { useQuery } from '@tanstack/react-query';
import { Heart } from 'lucide-react';
import { Link } from 'react-router-dom';
import { search } from '@/api/endpoints';
import { useAuth } from '@/auth/AuthProvider';
import { useSaveToggle } from '@/hooks/useSaveToggle';
import { useTheme } from '@/theme/ThemeProvider';

/** "Từ của mùa / hôm nay" strip. The save button only shows when the word is found by search. */
export function WordOfSeason() {
  const { t } = useTheme();
  const { user } = useAuth();
  const w = t.word;
  const found = useQuery({
    queryKey: ['season-word', w.kanji],
    queryFn: () => search(w.kanji, 1, 5),
    enabled: Boolean(user),
    select: (r) => r.items.find((it) => it.word.kanji === w.kanji || it.word.kana === w.kana)?.word,
    staleTime: 5 * 60_000,
  });
  const toggle = useSaveToggle();
  const match = found.data;

  return (
    <div className="mx-4 mt-8 md:mx-auto md:max-w-[1192px]">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2 border-2 border-ink bg-light px-[18px] py-[10px] text-[14px] font-semibold">
        <span lang="ja" className="jp bg-ink px-2 py-[2px] text-card">{w.label}</span>
        <span className="uppercase">{w.title}:</span>
        {match ? (
          <Link to={`/?w=${match.id}`} lang="ja" className="font-serif text-[20px] no-underline">
            {w.kanji}
          </Link>
        ) : (
          <span lang="ja" className="font-serif text-[20px]">{w.kanji}</span>
        )}
        <span lang="ja" className="jp text-[14px] font-normal text-muted">{w.kana}</span>
        <span>
          《{w.hanviet}》 {w.vi}
        </span>
        {match && (
          <button
            type="button"
            className="ml-auto flex items-center gap-2 border-0 bg-transparent p-0 font-semibold uppercase text-ink hover:text-acc-text"
            disabled={toggle.isPending || Boolean(match.saved)}
            onClick={() => toggle.mutate({ wordId: match.id, save: true })}
          >
            <Heart aria-hidden="true" size={16} fill={match.saved ? 'currentColor' : 'none'} />
            {match.saved ? 'Đã lưu' : 'Lưu vào sổ →'}
          </button>
        )}
      </div>
    </div>
  );
}
