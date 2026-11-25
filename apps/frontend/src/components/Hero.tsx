import type { ReactNode } from 'react';
import { useTheme } from '@/theme/ThemeProvider';
import { PixelImage, themeAsset } from './PixelImage';

export function Hero({ search }: { search: ReactNode }) {
  const { theme, t } = useTheme();
  return (
    <div className="mx-auto flex max-w-[1240px] flex-wrap items-stretch gap-8 px-4 pt-2 md:px-6">
      <div className="flex min-w-0 flex-[1_1_520px] flex-col gap-[18px] pt-3">
        <span className="self-start border-2 border-ink bg-light px-[10px] py-[5px] text-[13px] font-bold tracking-[0.04em]">
          {t.chip}
        </span>
        <h1 className="m-0 text-[34px] font-extrabold uppercase leading-[1.12] tracking-[-0.01em] md:text-[50px]">
          Tra một từ,
          <br />
          đọc mọi giáo trình
        </h1>
        <p className="m-0 max-w-[480px] leading-[1.6] text-muted">{t.tagline}</p>
        {search}
      </div>
      <div className="relative h-[160px] flex-[1_1_400px] overflow-hidden border-2 border-ink bg-scene shadow-block md:h-[320px]">
        <PixelImage src={themeAsset(theme, 'hero.svg')} className="absolute inset-0 h-full w-full object-cover" style={{ objectPosition: 'bottom' }} />
      </div>
    </div>
  );
}
