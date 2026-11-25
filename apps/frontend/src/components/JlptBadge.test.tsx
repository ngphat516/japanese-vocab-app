import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { ThemeProvider } from '@/theme/ThemeProvider';
import { jlptPalettes, type ThemePref } from '@/theme/tokens';
import { JlptBadge, jlptColors, jlptLabel } from './JlptBadge';

const renderIn = (theme: ThemePref, level: string | null) =>
  render(
    <ThemeProvider initial={theme}>
      <JlptBadge level={level} />
    </ThemeProvider>,
  );

// jsdom normalises hex to rgb()
const rgb = (hex: string) => {
  const n = parseInt(hex.slice(1), 16);
  return `rgb(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255})`;
};

describe('JlptBadge', () => {
  it('always shows the level text', () => {
    renderIn('day', 'N3');
    expect(screen.getByTestId('jlpt-badge')).toHaveTextContent('N3');
  });

  it('labels missing / unknown levels as "Ngoài JLPT"', () => {
    expect(jlptLabel(null)).toBe('Ngoài JLPT');
    expect(jlptLabel('N9')).toBe('Ngoài JLPT');
    renderIn('day', null);
    expect(screen.getByTestId('jlpt-badge')).toHaveTextContent('Ngoài JLPT');
  });

  it('uses the light palette on light themes', () => {
    renderIn('spring', 'N1');
    const el = screen.getByTestId('jlpt-badge');
    const [bg, fg] = jlptPalettes.light.N1;
    expect(el.style.background).toBe(rgb(bg));
    expect(el.style.color).toBe(rgb(fg));
    expect(el.style.border).toBe(`2px solid ${rgb(fg)}`);
    expect(el.style.borderRadius).toMatch(/^0(px)?$/);
  });

  it('switches to the dark palette on the night theme', () => {
    renderIn('night', 'N1');
    const el = screen.getByTestId('jlpt-badge');
    const [bg, fg] = jlptPalettes.dark.N1;
    expect(el.style.background).toBe(rgb(bg));
    expect(el.style.color).toBe(rgb(fg));
    expect(jlptPalettes.dark.N1).not.toEqual(jlptPalettes.light.N1);
  });

  it('jlptColors picks palette by dark flag', () => {
    expect(jlptColors('n5', false)).toEqual({ bg: jlptPalettes.light.N5[0], fg: jlptPalettes.light.N5[1] });
    expect(jlptColors('N5', true)).toEqual({ bg: jlptPalettes.dark.N5[0], fg: jlptPalettes.dark.N5[1] });
  });
});
