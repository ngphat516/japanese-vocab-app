import { Search } from 'lucide-react';
import { forwardRef, useEffect, useImperativeHandle, useRef } from 'react';
import { isMac } from '@/lib/platform';

interface SearchBoxProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit?: () => void;
  autoFocus?: boolean;
  /** Bind ⌘K / Ctrl K to focus this box. */
  hotkey?: boolean;
}

export const SearchBox = forwardRef<HTMLInputElement, SearchBoxProps>(function SearchBox(
  { value, onChange, onSubmit, autoFocus, hotkey = true },
  ref,
) {
  const inner = useRef<HTMLInputElement>(null);
  useImperativeHandle(ref, () => inner.current as HTMLInputElement);
  const mac = isMac();

  useEffect(() => {
    if (!hotkey) return;
    const onKey = (e: KeyboardEvent) => {
      if ((mac ? e.metaKey : e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        inner.current?.focus();
        inner.current?.select();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [hotkey, mac]);

  return (
    <form
      role="search"
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit?.();
      }}
      className="w-full max-w-[560px]"
    >
      <label className="flex h-14 items-center gap-3 border-[3px] border-ink bg-card px-4 shadow-search focus-within:outline focus-within:outline-[3px] focus-within:outline-offset-2 focus-within:outline-acc">
        <Search aria-hidden="true" size={22} strokeWidth={2.5} className="shrink-0 text-ink" />
        <span className="sr-only">Tìm từ</span>
        <input
          ref={inner}
          type="search"
          value={value}
          autoFocus={autoFocus}
          onChange={(e) => onChange(e.target.value)}
          placeholder="漢字 / kana / romaji / tiếng Việt"
          className="jp min-w-0 flex-grow border-0 bg-transparent text-[20px] text-ink outline-none placeholder:text-muted [&::-webkit-search-cancel-button]:hidden"
          autoComplete="off"
          spellCheck={false}
        />
        {hotkey && (
          <kbd className="hidden shrink-0 border-2 border-ink px-[6px] py-[1px] font-ui text-[12px] sm:inline">
            {mac ? '⌘K' : 'Ctrl K'}
          </kbd>
        )}
      </label>
    </form>
  );
});
