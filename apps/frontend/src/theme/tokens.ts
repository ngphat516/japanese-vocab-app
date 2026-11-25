import raw from '@design/tokens.json';

export const THEMES = ['day', 'night', 'spring', 'summer', 'autumn', 'winter'] as const;
export type ThemeName = (typeof THEMES)[number];
export type ThemePref = ThemeName | 'auto';
export type JlptKey = 'N1' | 'N2' | 'N3' | 'N4' | 'N5' | 'none';

export interface ThemeTokens {
  bg: string;
  card: string;
  ink: string;
  acc: string;
  light: string;
  mid: string;
  muted: string;
  sceneBg: string;
  ok: string;
  dark: boolean;
  label: string;
  kanji: string;
  chip: string;
  tagline: string;
  word: { label: string; title: string; kanji: string; kana: string; hanviet: string; vi: string };
  footer: { ja: string; vi: string };
}

type Palette = Record<JlptKey, readonly [string, string]>;

const data = raw as unknown as Record<ThemeName, ThemeTokens> & {
  _jlpt: { light: Palette; dark: Palette };
};

export const tokens: Record<ThemeName, ThemeTokens> = Object.fromEntries(
  THEMES.map((t) => [t, data[t]]),
) as Record<ThemeName, ThemeTokens>;

export const jlptPalettes = data._jlpt;

export function isThemeName(value: unknown): value is ThemeName {
  return typeof value === 'string' && (THEMES as readonly string[]).includes(value);
}
