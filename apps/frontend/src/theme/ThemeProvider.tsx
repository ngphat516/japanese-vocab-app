import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { resolveTheme } from './resolveTheme';
import { isThemeName, tokens, type ThemeName, type ThemePref, type ThemeTokens } from './tokens';

export const THEME_STORAGE_KEY = 'kotonoha.theme';

interface ThemeContextValue {
  pref: ThemePref;
  theme: ThemeName;
  t: ThemeTokens;
  setPref: (pref: ThemePref) => void;
}

const ThemeContext = createContext<ThemeContextValue | null>(null);

export function readStoredPref(): ThemePref {
  try {
    const v = localStorage.getItem(THEME_STORAGE_KEY);
    return v === 'auto' || isThemeName(v) ? v : 'auto';
  } catch {
    return 'auto';
  }
}

export function ThemeProvider({ children, initial }: { children: ReactNode; initial?: ThemePref }) {
  const [pref, setPrefState] = useState<ThemePref>(() => initial ?? readStoredPref());
  const theme = resolveTheme(pref, new Date());

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  const setPref = useCallback((next: ThemePref) => {
    setPrefState(next);
    try {
      localStorage.setItem(THEME_STORAGE_KEY, next);
    } catch {
      /* storage unavailable: keep in memory only */
    }
  }, []);

  const value = useMemo(() => ({ pref, theme, t: tokens[theme], setPref }), [pref, theme, setPref]);
  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error('useTheme must be used inside ThemeProvider');
  return ctx;
}
