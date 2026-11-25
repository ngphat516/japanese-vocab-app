import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { ThemePicker } from '@/components/ThemePicker';
import { seasonOf } from './resolveTheme';
import { THEME_STORAGE_KEY, ThemeProvider } from './ThemeProvider';
import { tokens } from './tokens';

describe('ThemePicker', () => {
  it('auto mode highlights the current season; clicking a theme turns auto off', async () => {
    render(
      <ThemeProvider initial="auto">
        <ThemePicker />
      </ThemeProvider>,
    );
    const season = seasonOf(new Date());
    expect(screen.getByRole('checkbox', { name: 'Tự động theo mùa' })).toBeChecked();
    expect(screen.getByRole('button', { name: tokens[season].label })).toHaveAttribute('aria-pressed', 'true');
    expect(document.documentElement.dataset.theme).toBe(season);

    await userEvent.click(screen.getByRole('button', { name: 'Tối' }));
    expect(screen.getByRole('checkbox', { name: 'Tự động theo mùa' })).not.toBeChecked();
    expect(document.documentElement.dataset.theme).toBe('night');
    expect(localStorage.getItem(THEME_STORAGE_KEY)).toBe('night');
  });
});
