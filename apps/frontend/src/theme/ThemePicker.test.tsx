import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { ThemePicker } from '@/components/ThemePicker';
import { seasonOf } from './resolveTheme';
import { THEME_STORAGE_KEY, ThemeProvider } from './ThemeProvider';
import { tokens } from './tokens';

describe('ThemePicker', () => {
  it('auto mode marks the current season as in use; picking a theme turns auto off', async () => {
    render(
      <ThemeProvider initial="auto">
        <ThemePicker />
      </ThemeProvider>,
    );
    const season = seasonOf(new Date());
    expect(document.documentElement.dataset.theme).toBe(season);

    await userEvent.click(screen.getByRole('button', { name: /Giao diện/ }));
    expect(screen.getByRole('menuitemcheckbox', { name: 'Tự động theo mùa' })).toHaveAttribute('aria-checked', 'true');
    const current = screen.getByRole('menuitemradio', { name: new RegExp(tokens[season].label) });
    expect(current).toHaveTextContent('đang dùng');
    expect(screen.getAllByRole('menuitemradio')).toHaveLength(6);

    await userEvent.click(screen.getByRole('menuitemradio', { name: 'Tối' }));
    expect(document.documentElement.dataset.theme).toBe('night');
    expect(localStorage.getItem(THEME_STORAGE_KEY)).toBe('night');

    await userEvent.click(screen.getByRole('button', { name: /Giao diện/ }));
    expect(screen.getByRole('menuitemcheckbox', { name: 'Tự động theo mùa' })).toHaveAttribute('aria-checked', 'false');
    expect(screen.getByRole('menuitemradio', { name: 'Tối' })).toHaveAttribute('aria-checked', 'true');
    expect(screen.queryByText('đang dùng')).toBeNull();
  });

  it('turning auto back on follows the season', async () => {
    render(
      <ThemeProvider initial="night">
        <ThemePicker />
      </ThemeProvider>,
    );
    await userEvent.click(screen.getByRole('button', { name: /Giao diện/ }));
    await userEvent.click(screen.getByRole('menuitemcheckbox', { name: 'Tự động theo mùa' }));
    expect(document.documentElement.dataset.theme).toBe(seasonOf(new Date()));
    expect(screen.getByRole('menuitemcheckbox', { name: 'Tự động theo mùa' })).toHaveAttribute('aria-checked', 'true');
  });
});
