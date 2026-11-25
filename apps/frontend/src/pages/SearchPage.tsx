import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { useCallback, useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { clsx } from 'clsx';
import { search } from '@/api/endpoints';
import { useAuth } from '@/auth/AuthProvider';
import { Hero } from '@/components/Hero';
import { LoginPrompt } from '@/components/LoginPrompt';
import { SearchBox } from '@/components/SearchBox';
import { Window } from '@/components/Window';
import { useDebounced } from '@/hooks/useDebounced';
import { HomeLists } from './search/HomeLists';
import { ResultsWindow } from './search/ResultsWindow';
import { WordDetailWindow } from './search/WordDetailWindow';
import { WordOfSeason } from './search/WordOfSeason';

const PAGE_SIZE = 20;

export function SearchPage() {
  const { user } = useAuth();
  const [params, setParams] = useSearchParams();
  const q = params.get('q') ?? '';
  const w = Number(params.get('w')) || undefined;
  const page = Math.max(1, Number(params.get('page')) || 1);

  // Input is local; the URL follows it after a 250ms debounce.
  const [input, setInput] = useState(q);
  const debounced = useDebounced(input, 250);
  const lastPushed = useRef(q);

  useEffect(() => {
    // URL changed from outside (back/forward, links): sync the input.
    if (q !== lastPushed.current) {
      lastPushed.current = q;
      setInput(q);
    }
  }, [q]);

  const pushQuery = useCallback(
    (value: string) => {
      const next = value.trim();
      if (next === lastPushed.current.trim()) return;
      lastPushed.current = next;
      setParams(next ? { q: next } : {}, { replace: true });
    },
    [setParams],
  );

  useEffect(() => pushQuery(debounced), [debounced, pushQuery]);

  const results = useQuery({
    queryKey: ['search', q, page],
    queryFn: ({ signal }) => search(q, page, PAGE_SIZE, signal),
    enabled: Boolean(q) && Boolean(user),
    placeholderData: keepPreviousData,
  });

  const items = results.data?.items ?? [];
  const selectedId = w ?? items[0]?.word.id;
  const selectedItem = items.find((it) => it.word.id === selectedId);

  const hrefFor = useCallback(
    (id: number) => {
      const p = new URLSearchParams();
      if (q) p.set('q', q);
      if (page > 1) p.set('page', String(page));
      p.set('w', String(id));
      return `/?${p.toString()}`;
    },
    [q, page],
  );

  const setPage = (p: number) => {
    const next = new URLSearchParams(params);
    next.set('page', String(p));
    next.delete('w');
    setParams(next, { replace: true });
  };

  const back = () => {
    const next = new URLSearchParams(params);
    next.delete('w');
    setParams(next, { replace: true });
  };

  let body;
  if (!q && !w) body = <HomeLists />;
  else if (!user)
    body = (
      <main className="mx-auto max-w-[1240px] px-4 pt-8 md:px-6">
        <Window title="Kết quả">
          <LoginPrompt />
        </Window>
      </main>
    );
  else
    body = (
      <main className="mx-auto flex max-w-[1240px] flex-wrap items-start gap-7 px-4 pt-8 md:px-6">
        {q && (
          <ResultsWindow
            className={clsx('flex-[1_1_280px]', w && 'hidden md:block')}
            data={results.data}
            isPending={results.isPending}
            error={results.error}
            selectedId={selectedId}
            hrefFor={hrefFor}
            page={page}
            onPage={setPage}
          />
        )}
        {selectedId !== undefined && (
          <WordDetailWindow
            className={clsx('flex-[999_1_560px]', q && !w && 'hidden md:block')}
            wordId={selectedId}
            examplesCount={selectedItem?.appears_in_examples?.count}
            onBack={q ? back : undefined}
          />
        )}
      </main>
    );

  return (
    <>
      <Hero search={<SearchBox value={input} onChange={setInput} onSubmit={() => pushQuery(input)} />} />
      <WordOfSeason />
      {body}
    </>
  );
}
