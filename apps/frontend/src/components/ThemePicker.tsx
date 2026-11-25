import { clsx } from 'clsx';
import { useTheme } from '@/theme/ThemeProvider';
import { seasonOf } from '@/theme/resolveTheme';
import { THEMES, tokens } from '@/theme/tokens';

export function ThemePicker({ compact = false }: { compact?: boolean }) {
  const { pref, theme, setPref } = useTheme();
  const auto = pref === 'auto';
  return (
    <div role="group" aria-label="Giao diện" className="flex flex-wrap items-center gap-[6px]">
      {!compact && <span className="mr-[2px] text-[13px] font-semibold text-ink">Giao diện</span>}
      {THEMES.map((name) => {
        const selected = theme === name;
        return (
          <button
            key={name}
            type="button"
            aria-label={tokens[name].label}
            aria-pressed={selected}
            title={tokens[name].label}
            onClick={() => setPref(name)}
            className={clsx(
              'jp flex h-9 min-w-[40px] items-center justify-center border-2 border-ink px-[10px] text-[14px] font-semibold',
              selected ? 'bg-ink text-card' : 'bg-transparent text-ink hover:bg-light',
            )}
          >
            {tokens[name].kanji}
          </button>
        );
      })}
      <label className="ml-1 flex cursor-pointer items-center gap-[6px] text-[13px] font-semibold">
        <input
          type="checkbox"
          checked={auto}
          onChange={(e) => setPref(e.target.checked ? 'auto' : seasonOf(new Date()))}
          className="h-4 w-4 accent-[var(--ink)]"
        />
        Tự động theo mùa
      </label>
    </div>
  );
}
