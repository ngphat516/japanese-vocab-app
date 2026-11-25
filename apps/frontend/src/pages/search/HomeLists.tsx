import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { history, saved } from '@/api/endpoints';
import type { WordSummary } from '@/api/types';
import { useAuth } from '@/auth/AuthProvider';
import { JlptBadge } from '@/components/JlptBadge';
import { LoginPrompt } from '@/components/LoginPrompt';
import { ErrorNote, Loading } from '@/components/Status';
import { Window } from '@/components/Window';

function WordRow({ w, meta }: { w: WordSummary; meta?: string }) {
  return (
    <Link to={`/?w=${w.id}`} className="flex items-center gap-3 px-[14px] py-3 text-ink no-underline hover:bg-light hover:text-ink">
      <div className="min-w-0 flex-grow">
        <div lang="ja" className="jp text-[17px] font-medium">{w.kanji || w.kana}</div>
        <div className="truncate text-[12px] text-muted">
          <span lang="ja" className="jp">{w.kana}</span>
          {w.hanviet ? ` · ${w.hanviet}` : ''}
          {meta ? ` · ${meta}` : ''}
        </div>
      </div>
      <JlptBadge level={w.jlpt_level} />
    </Link>
  );
}

const fmt = new Intl.DateTimeFormat('vi-VN', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });

/** Shown when there is no query: search history and recently saved words. */
export function HomeLists() {
  const { user } = useAuth();
  const h = useQuery({ queryKey: ['history'], queryFn: () => history(1, 10), enabled: Boolean(user) });
  const s = useQuery({ queryKey: ['saved', 'recent'], queryFn: () => saved.list({ page: 1, size: 6 }), enabled: Boolean(user) });

  if (!user)
    return (
      <main className="mx-auto max-w-[1240px] px-4 pt-8 md:px-6">
        <Window title="Bắt đầu">
          <LoginPrompt text="Đăng nhập để tra từ trong mọi giáo trình, xem lịch sử tra và lưu từ vào sổ." />
        </Window>
      </main>
    );

  return (
    <main className="mx-auto flex max-w-[1240px] flex-wrap items-start gap-7 px-4 pt-8 md:px-6">
      <Window title="Lịch sử tra" className="flex-[1_1_420px]">
        {h.isPending ? (
          <Loading />
        ) : h.isError ? (
          <div className="p-4"><ErrorNote error={h.error} /></div>
        ) : !h.data.items.length ? (
          <p className="m-0 p-5 text-muted">Chưa có lịch sử. Gõ một từ vào ô tìm kiếm để bắt đầu.</p>
        ) : (
          <ul className="m-0 list-none p-0">
            {h.data.items.map((it, i) => (
              <li key={it.id} className={i ? 'border-t-2 border-dashed border-light' : ''}>
                <WordRow w={it.word} meta={fmt.format(new Date(it.searched_at))} />
              </li>
            ))}
          </ul>
        )}
      </Window>
      <Window title="Mới lưu" className="flex-[1_1_320px]">
        {s.isPending ? (
          <Loading />
        ) : s.isError ? (
          <div className="p-4"><ErrorNote error={s.error} /></div>
        ) : !s.data.items.length ? (
          <p className="m-0 p-5 text-muted">Sổ từ đang trống. Bấm ♥ Lưu ở trang chi tiết để thêm.</p>
        ) : (
          <>
            <ul className="m-0 list-none p-0">
              {s.data.items.map((it, i) => (
                <li key={it.id} className={i ? 'border-t-2 border-dashed border-light' : ''}>
                  <WordRow w={it.word} meta={it.sources[0]?.textbook} />
                </li>
              ))}
            </ul>
            <div className="border-t-2 border-ink px-[14px] py-2 text-right">
              <Link to="/notebook" className="text-[13px] font-bold uppercase">Mở sổ từ →</Link>
            </div>
          </>
        )}
      </Window>
    </main>
  );
}
