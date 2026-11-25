import { useTheme } from '@/theme/ThemeProvider';
import { jlptPalettes, type JlptKey } from '@/theme/tokens';

export function jlptKey(level: string | null | undefined): JlptKey {
  const v = (level ?? '').toUpperCase();
  return v === 'N1' || v === 'N2' || v === 'N3' || v === 'N4' || v === 'N5' ? v : 'none';
}

export function jlptColors(level: string | null | undefined, dark: boolean) {
  const [bg, fg] = jlptPalettes[dark ? 'dark' : 'light'][jlptKey(level)];
  return { bg, fg };
}

export const jlptLabel = (level: string | null | undefined) => {
  const k = jlptKey(level);
  return k === 'none' ? 'Ngoài JLPT' : k;
};

/** JLPT badge: always labelled, 2px border in text colour, square corners. Palette follows tokens[theme].dark. */
export function JlptBadge({ level, className }: { level: string | null | undefined; className?: string }) {
  const { t } = useTheme();
  const { bg, fg } = jlptColors(level, t.dark);
  return (
    <span
      data-testid="jlpt-badge"
      className={className}
      style={{
        display: 'inline-block',
        fontFamily: "'Be Vietnam Pro', sans-serif",
        fontSize: 12,
        fontWeight: 700,
        lineHeight: 1,
        padding: '4px 8px',
        background: bg,
        color: fg,
        border: `2px solid ${fg}`,
        borderRadius: 0,
        whiteSpace: 'nowrap',
      }}
    >
      {jlptLabel(level)}
    </span>
  );
}
