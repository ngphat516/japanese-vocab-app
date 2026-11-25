import type { ImgHTMLAttributes } from 'react';
import { clsx } from 'clsx';

/** Decorative pixel art: always pixelated and hidden from assistive tech. */
export function PixelImage({ className, ...rest }: Omit<ImgHTMLAttributes<HTMLImageElement>, 'alt'>) {
  return <img alt="" aria-hidden="true" draggable={false} {...rest} className={clsx('pixel', className)} />;
}

export const themeAsset = (theme: string, file: string) => `/themes/${theme}/${file}`;
