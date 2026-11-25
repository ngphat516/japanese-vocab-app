import type { ThemeName, ThemePref } from './tokens';

/** Season for a date: 3–5 spring, 6–8 summer, 9–11 autumn, 12–2 winter. */
export function seasonOf(date: Date): ThemeName {
  const m = date.getMonth() + 1;
  if (m >= 3 && m <= 5) return 'spring';
  if (m >= 6 && m <= 8) return 'summer';
  if (m >= 9 && m <= 11) return 'autumn';
  return 'winter';
}

/** Pure: resolves a stored preference to a concrete theme. */
export function resolveTheme(pref: ThemePref, date: Date): ThemeName {
  return pref === 'auto' ? seasonOf(date) : pref;
}
