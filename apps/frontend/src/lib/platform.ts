export function isMac(nav: Pick<Navigator, 'platform' | 'userAgent'> = navigator): boolean {
  return /Mac|iPhone|iPad|iPod/i.test(nav.platform || nav.userAgent);
}
export const shortcutLabel = () => (isMac() ? '⌘K' : 'Ctrl K');
