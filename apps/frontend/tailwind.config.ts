import type { Config } from 'tailwindcss';

const v = (name: string) => `var(--${name})`;

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    borderRadius: { none: '0' },
    extend: {
      colors: {
        bg: v('bg'),
        card: v('card'),
        ink: v('ink'),
        acc: v('acc'),
        light: v('light'),
        mid: v('mid'),
        muted: v('muted'),
        scene: v('scene-bg'),
        ok: v('ok'),
      },
      fontFamily: {
        ui: ['"Be Vietnam Pro"', '"Noto Sans JP"', 'sans-serif'],
        jp: ['"Noto Sans JP"', 'sans-serif'],
        serif: ['"Noto Serif JP"', 'serif'],
      },
      boxShadow: {
        block: '6px 6px 0 var(--mid)',
        'block-sm': '4px 4px 0 var(--mid)',
        search: '6px 6px 0 var(--acc)',
      },
    },
  },
  plugins: [],
} satisfies Config;
