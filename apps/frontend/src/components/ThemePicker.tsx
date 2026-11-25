import * as DropdownMenu from '@radix-ui/react-dropdown-menu';
import { Check, ChevronDown } from 'lucide-react';
import { useTheme } from '@/theme/ThemeProvider';
import { seasonOf } from '@/theme/resolveTheme';
import { THEMES, tokens, type ThemeName } from '@/theme/tokens';

const itemClass =
  'relative flex cursor-pointer select-none items-center gap-3 py-2 pl-8 pr-3 text-[14px] font-semibold text-ink outline-none data-[highlighted]:bg-light';

/** Theme menu: trigger shows the active theme's kanji; content has the auto toggle and the six themes. */
export function ThemePicker() {
  const { pref, theme, setPref } = useTheme();
  const auto = pref === 'auto';
  return (
    <DropdownMenu.Root>
      <DropdownMenu.Trigger className="btn btn-secondary btn-sm" aria-label={`Giao diện: ${tokens[theme].label}`}>
        <span lang="ja" className="jp text-[15px]">
          {tokens[theme].kanji}
        </span>
        <span className="hidden md:inline">Giao diện</span>
        <ChevronDown aria-hidden="true" size={14} />
      </DropdownMenu.Trigger>
      <DropdownMenu.Portal>
        <DropdownMenu.Content align="end" sideOffset={6} className="win z-50 min-w-[220px] p-1">
          <DropdownMenu.CheckboxItem
            checked={auto}
            onSelect={(e) => e.preventDefault()}
            onCheckedChange={(c) => setPref(c ? 'auto' : seasonOf(new Date()))}
            className={itemClass}
          >
            <DropdownMenu.ItemIndicator className="absolute left-2 flex">
              <Check aria-hidden="true" size={16} />
            </DropdownMenu.ItemIndicator>
            Tự động theo mùa
          </DropdownMenu.CheckboxItem>
          <DropdownMenu.Separator className="my-1 h-[2px] bg-ink" />
          <DropdownMenu.RadioGroup value={auto ? '' : theme} onValueChange={(v) => setPref(v as ThemeName)}>
            {THEMES.map((name) => (
              <DropdownMenu.RadioItem key={name} value={name} className={itemClass}>
                <DropdownMenu.ItemIndicator className="absolute left-2 flex">
                  <Check aria-hidden="true" size={16} />
                </DropdownMenu.ItemIndicator>
                <span lang="ja" aria-hidden="true" className="jp w-5 text-center">
                  {tokens[name].kanji}
                </span>
                <span>{tokens[name].label}</span>
                {auto && theme === name && <span className="ml-auto text-[12px] font-normal text-muted">đang dùng</span>}
              </DropdownMenu.RadioItem>
            ))}
          </DropdownMenu.RadioGroup>
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  );
}
