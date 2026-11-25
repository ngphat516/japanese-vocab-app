import * as DropdownMenu from '@radix-ui/react-dropdown-menu';
import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ChevronDown, Download, LayoutGrid, Search, Table2, Trash2 } from 'lucide-react';
import { useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { clsx } from 'clsx';
import { downloadResponse, saved, textbooks, type SavedFilter } from '@/api/endpoints';
import type { SavedItem } from '@/api/types';
import { JlptBadge, jlptColors, jlptKey, jlptLabel } from '@/components/JlptBadge';
import { Pager } from '@/components/Pager';
import { ErrorNote, Loading } from '@/components/Status';
import { Window } from '@/components/Window';
import { useLocalBool } from '@/hooks/useLocalBool';
import { useTheme } from '@/theme/ThemeProvider';

const LEVELS = ['N1', 'N2', 'N3', 'N4', 'N5', 'none'] as const;
type Level = (typeof LEVELS)[number];
const PAGE_SIZE = 24;

const FORMATS = [
  { id: 'anki', label: 'Anki (.apkg)', hint: 'Có furigana, tag theo cấp' },
  { id: 'csv', label: 'CSV', hint: 'Mở bằng Excel / Sheets' },
  { id: 'markdown', label: 'Markdown', hint: 'Dán vào ghi chú' },
] as const;

function StatTiles({ level, onLevel }: { level: Level | undefined; onLevel: (l: Level | undefined) => void }) {
  const { t } = useTheme();
  const stats = useQuery({ queryKey: ['saved-stats'], queryFn: saved.stats });
  return (
    <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
      {LEVELS.map((l) => {
        const { bg, fg } = jlptColors(l, t.dark);
        const active = level === l;
        return (
          <button
            key={l}
            type="button"
            aria-pressed={active}
            onClick={() => onLevel(active ? undefined : l)}
            className="flex flex-col items-start gap-1 px-4 py-[14px] text-left"
            style={{
              background: bg,
              border: `2px solid ${fg}`,
              boxShadow: active ? `4px 4px 0 ${fg}` : 'none',
              transform: active ? 'translate(-2px,-2px)' : undefined,
            }}
          >
            <span className="font-bold" style={{ color: fg }}>
              {jlptLabel(l)}
              {active ? ' · đang lọc' : ''}
            </span>
            <span className="text-[26px] font-bold leading-none" style={{ color: fg }}>
              {stats.data ? (stats.data[l] ?? 0) : '–'}
            </span>
          </button>
        );
      })}
    </div>
  );
}

function ExportMenu({ filter }: { filter: SavedFilter }) {
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const run = async (format: (typeof FORMATS)[number]['id']) => {
    setBusy(true);
    setError(null);
    try {
      const res = await saved.export(format, filter);
      await downloadResponse(res, `notebook.${format === 'anki' ? 'apkg' : format === 'markdown' ? 'md' : 'csv'}`);
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="flex flex-col items-end gap-2">
      <DropdownMenu.Root>
        <DropdownMenu.Trigger className="btn btn-primary" disabled={busy}>
          <Download aria-hidden="true" size={16} /> {busy ? 'Đang xuất…' : 'Xuất'} <ChevronDown aria-hidden="true" size={14} />
        </DropdownMenu.Trigger>
        <DropdownMenu.Portal>
          <DropdownMenu.Content align="end" sideOffset={8} className="win z-50 w-[240px] p-1">
            {FORMATS.map((f) => (
              <DropdownMenu.Item
                key={f.id}
                onSelect={() => void run(f.id)}
                className="cursor-pointer px-3 py-[10px] text-[14px] font-semibold outline-none data-[highlighted]:bg-light"
              >
                {f.label}
                <div className="text-[12px] font-normal text-muted">{f.hint}</div>
              </DropdownMenu.Item>
            ))}
          </DropdownMenu.Content>
        </DropdownMenu.Portal>
      </DropdownMenu.Root>
      {error ? <ErrorNote error={error} /> : null}
    </div>
  );
}

function useRemove() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => saved.remove(id),
    onSuccess: () => {
      for (const key of ['saved', 'saved-stats', 'word', 'search']) void qc.invalidateQueries({ queryKey: [key] });
    },
  });
}

function sourceLabel(it: SavedItem) {
  const s = it.sources[0];
  return s ? `${s.textbook} · ${s.lesson}` : null;
}

function Card({ it, onRemove }: { it: SavedItem; onRemove: () => void }) {
  const w = it.word;
  const src = sourceLabel(it);
  return (
    <article className="win flex flex-col gap-[6px] p-[18px]">
      <div className="flex items-center justify-between gap-2">
        <span lang="ja" className="jp text-[13px] text-muted">{w.kana}</span>
        <JlptBadge level={w.jlpt_level} />
      </div>
      <Link to={`/?w=${w.id}`} lang="ja" className="font-serif text-[30px] font-bold leading-tight no-underline">
        {w.kanji || w.kana}
      </Link>
      {w.hanviet && <div className="font-bold uppercase tracking-[0.04em] text-acc">《{w.hanviet.toUpperCase()}》</div>}
      {it.note && <div className="text-ink">{it.note}</div>}
      <div className="mt-[6px] flex flex-wrap items-center gap-[6px]">
        {src && <span className="border-2 border-light bg-light px-2 py-[2px] text-[12px] text-ink">{src}</span>}
        {it.tags.map((t) => (
          <span key={t} className="border-2 border-ink px-2 py-[2px] text-[12px] text-ink">
            #{t}
          </span>
        ))}
        <button type="button" onClick={onRemove} aria-label={`Bỏ lưu ${w.kanji || w.kana}`} className="ml-auto p-1 text-muted hover:text-ink">
          <Trash2 aria-hidden="true" size={16} />
        </button>
      </div>
    </article>
  );
}

function Table({ items, onRemove }: { items: SavedItem[]; onRemove: (id: number) => void }) {
  return (
    <div className="win mt-5 overflow-x-auto">
      <table className="w-full border-collapse text-left">
        <thead className="bg-light">
          <tr className="border-b-2 border-ink text-[12px] uppercase tracking-[0.06em]">
            <th className="px-3 py-2">Từ</th>
            <th className="px-3 py-2">Đọc</th>
            <th className="px-3 py-2">Hán Việt</th>
            <th className="px-3 py-2">Cấp</th>
            <th className="px-3 py-2">Giáo trình</th>
            <th className="px-3 py-2">Tag</th>
            <th className="px-3 py-2"><span className="sr-only">Thao tác</span></th>
          </tr>
        </thead>
        <tbody>
          {items.map((it) => (
            <tr key={it.id} className="border-t-2 border-dashed border-light">
              <td className="px-3 py-2">
                <Link to={`/?w=${it.word.id}`} lang="ja" className="font-serif text-[18px] font-bold no-underline">
                  {it.word.kanji || it.word.kana}
                </Link>
              </td>
              <td lang="ja" className="jp px-3 py-2 text-muted">{it.word.kana}</td>
              <td className="px-3 py-2 uppercase text-acc">{it.word.hanviet}</td>
              <td className="px-3 py-2"><JlptBadge level={it.word.jlpt_level} /></td>
              <td className="px-3 py-2 text-[13px]">{sourceLabel(it) ?? '—'}</td>
              <td className="px-3 py-2 text-[13px]">{it.tags.map((t) => `#${t}`).join(' ') || '—'}</td>
              <td className="px-3 py-2 text-right">
                <button type="button" onClick={() => onRemove(it.id)} aria-label={`Bỏ lưu ${it.word.kanji || it.word.kana}`} className="p-1 text-muted hover:text-ink">
                  <Trash2 aria-hidden="true" size={16} />
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

const selectClass = 'h-10 border-2 border-ink bg-card px-3 text-[14px] text-ink';

export default function NotebookPage() {
  const [params, setParams] = useSearchParams();
  const level = (LEVELS as readonly string[]).includes(params.get('jlpt') ?? '') ? (params.get('jlpt') as Level) : undefined;
  const tag = params.get('tag') ?? undefined;
  const textbookId = Number(params.get('textbook')) || undefined;
  const page = Math.max(1, Number(params.get('page')) || 1);
  const [text, setText] = useState('');
  const [tableView, setTableView] = useLocalBool('kotonoha.notebook.table', false);
  const remove = useRemove();

  const update = (patch: Record<string, string | undefined>) => {
    const next = new URLSearchParams(params);
    for (const [k, v] of Object.entries(patch)) {
      if (v) next.set(k, v);
      else next.delete(k);
    }
    if (!('page' in patch)) next.delete('page');
    setParams(next, { replace: true });
  };

  const filter: SavedFilter = { jlpt: level, tag, textbook_id: textbookId };
  // "Ngoài JLPT" has no server filter: fetch a large page and filter locally (docs/DECISIONS.md).
  const localLevel = level === 'none';
  const list = useQuery({
    queryKey: ['saved', 'list', filter, localLevel ? 1 : page],
    queryFn: () => saved.list({ ...filter, page: localLevel ? 1 : page, size: localLevel ? 100 : PAGE_SIZE }),
    placeholderData: keepPreviousData,
  });
  // Tag options: no tags endpoint, so collect from the first 100 saved words.
  const tagSource = useQuery({ queryKey: ['saved', 'tags'], queryFn: () => saved.list({ page: 1, size: 100 }), staleTime: 60_000 });
  const books = useQuery({ queryKey: ['textbooks'], queryFn: textbooks, staleTime: 5 * 60_000 });
  const tags = useMemo(
    () => [...new Set((tagSource.data?.items ?? []).flatMap((i) => i.tags))].sort((a, b) => a.localeCompare(b, 'vi')),
    [tagSource.data],
  );

  const items = useMemo(() => {
    let rows = list.data?.items ?? [];
    if (localLevel) rows = rows.filter((r) => jlptKey(r.word.jlpt_level) === 'none');
    const needle = text.trim().toLowerCase();
    if (needle)
      rows = rows.filter((r) =>
        [r.word.kanji, r.word.kana, r.word.romaji, r.word.hanviet, r.note, ...r.tags].some((v) => v?.toLowerCase().includes(needle)),
      );
    return rows;
  }, [list.data, localLevel, text]);

  const total = list.data?.total ?? 0;

  return (
    <main className="mx-auto max-w-[1240px] px-4 pt-6 md:px-6">
      <div className="flex flex-wrap items-end gap-4">
        <div className="flex-grow">
          <h1 className="m-0 text-[28px] font-extrabold uppercase">Sổ từ</h1>
          <div className="mt-1 text-muted">{total} từ{level || tag || textbookId ? ' khớp bộ lọc' : ' đã lưu'} · bấm vào một cấp để lọc</div>
        </div>
        <ExportMenu filter={{ jlpt: level, tag }} />
      </div>

      <StatTiles level={level} onLevel={(l) => update({ jlpt: l })} />

      <div className="mt-5 flex flex-wrap items-center gap-[10px]">
        <label className="flex h-10 flex-[1_1_260px] items-center gap-2 border-2 border-ink bg-card px-3 focus-within:outline focus-within:outline-[3px] focus-within:outline-offset-2 focus-within:outline-acc">
          <Search aria-hidden="true" size={16} />
          <input
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Tìm trong sổ từ (trang hiện tại)"
            aria-label="Tìm trong sổ từ"
            className="min-w-0 flex-grow border-0 bg-transparent text-[14px] text-ink outline-none placeholder:text-muted"
          />
        </label>
        <select aria-label="Lọc theo tag" className={selectClass} value={tag ?? ''} onChange={(e) => update({ tag: e.target.value || undefined })}>
          <option value="">Tag: Tất cả</option>
          {tags.map((t) => (
            <option key={t} value={t}>
              #{t}
            </option>
          ))}
        </select>
        <select
          aria-label="Lọc theo giáo trình"
          className={clsx(selectClass, 'max-w-[260px]')}
          value={textbookId ?? ''}
          onChange={(e) => update({ textbook: e.target.value || undefined })}
        >
          <option value="">Giáo trình: Tất cả</option>
          {books.data?.items.map((b) => (
            <option key={b.id} value={b.id}>
              {b.name}
            </option>
          ))}
        </select>
        <div role="group" aria-label="Kiểu hiển thị" className="flex border-2 border-ink">
          <button type="button" aria-pressed={!tableView} onClick={() => setTableView(false)} className={clsx('flex h-9 items-center gap-1 px-3 text-[14px] font-semibold', !tableView ? 'bg-ink text-card' : 'bg-card text-ink')}>
            <LayoutGrid aria-hidden="true" size={15} /> Thẻ
          </button>
          <button type="button" aria-pressed={tableView} onClick={() => setTableView(true)} className={clsx('flex h-9 items-center gap-1 border-l-2 border-ink px-3 text-[14px] font-semibold', tableView ? 'bg-ink text-card' : 'bg-card text-ink')}>
            <Table2 aria-hidden="true" size={15} /> Bảng
          </button>
        </div>
      </div>

      {remove.isError && <div className="mt-4"><ErrorNote error={remove.error} /></div>}

      {list.isPending ? (
        <Loading />
      ) : list.isError ? (
        <div className="mt-5"><ErrorNote error={list.error} /></div>
      ) : !items.length ? (
        <Window title="Trống" className="mt-5">
          <p className="m-0 p-5 text-muted">
            {total || text ? 'Không có từ nào khớp bộ lọc.' : 'Chưa lưu từ nào. Tra một từ và bấm ♥ Lưu để thêm vào sổ.'}
          </p>
        </Window>
      ) : tableView ? (
        <Table items={items} onRemove={(id) => remove.mutate(id)} />
      ) : (
        <div className="mt-5 grid gap-[18px] [grid-template-columns:repeat(auto-fill,minmax(240px,1fr))]">
          {items.map((it) => (
            <Card key={it.id} it={it} onRemove={() => remove.mutate(it.id)} />
          ))}
        </div>
      )}

      {!localLevel && list.data && (
        <div className="mt-5">
          <Pager page={page} size={PAGE_SIZE} total={list.data.total} onPage={(p) => update({ page: String(p) })} />
        </div>
      )}
    </main>
  );
}

