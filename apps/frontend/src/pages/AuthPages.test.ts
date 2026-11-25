import { describe, expect, it } from 'vitest';
import { loginSchema, registerSchema, safeNext } from './AuthPages';

describe('auth forms', () => {
  it('validates login input', () => {
    expect(loginSchema.safeParse({ email: 'a@b.co', password: 'x' }).success).toBe(true);
    expect(loginSchema.safeParse({ email: 'nope', password: '' }).success).toBe(false);
  });

  it('validates register input incl. password confirmation', () => {
    const ok = { display_name: 'K', email: 'a@b.co', password: '12345678', confirm: '12345678' };
    expect(registerSchema.safeParse(ok).success).toBe(true);
    expect(registerSchema.safeParse({ ...ok, password: 'short', confirm: 'short' }).success).toBe(false);
    const mismatch = registerSchema.safeParse({ ...ok, confirm: 'different' });
    expect(mismatch.success).toBe(false);
    expect(mismatch.error?.issues[0]?.path).toEqual(['confirm']);
  });

  it('only redirects to in-app paths', () => {
    expect(safeNext('/notebook?x=1')).toBe('/notebook?x=1');
    expect(safeNext('https://evil.example')).toBe('/');
    expect(safeNext('//evil.example')).toBe('/');
    expect(safeNext(null)).toBe('/');
  });
});
