import { describe, expect, it } from 'vitest';
import { resolveTheme, seasonOf } from './resolveTheme';

const d = (month: number) => new Date(2026, month - 1, 15);

describe('resolveTheme', () => {
  it.each([
    [3, 'spring'], [4, 'spring'], [5, 'spring'],
    [6, 'summer'], [7, 'summer'], [8, 'summer'],
    [9, 'autumn'], [10, 'autumn'], [11, 'autumn'],
    [12, 'winter'], [1, 'winter'], [2, 'winter'],
  ] as const)('auto in month %i → %s', (month, expected) => {
    expect(resolveTheme('auto', d(month))).toBe(expected);
    expect(seasonOf(d(month))).toBe(expected);
  });

  it('handles month boundaries', () => {
    expect(resolveTheme('auto', new Date(2026, 1, 28, 23, 59))).toBe('winter');
    expect(resolveTheme('auto', new Date(2026, 2, 1, 0, 0))).toBe('spring');
    expect(resolveTheme('auto', new Date(2026, 10, 30))).toBe('autumn');
    expect(resolveTheme('auto', new Date(2026, 11, 1))).toBe('winter');
  });

  it('returns explicit themes unchanged regardless of date', () => {
    for (const t of ['day', 'night', 'spring', 'summer', 'autumn', 'winter'] as const) {
      expect(resolveTheme(t, d(1))).toBe(t);
      expect(resolveTheme(t, d(7))).toBe(t);
    }
  });
});
