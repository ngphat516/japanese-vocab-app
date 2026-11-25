import type { ReactNode } from 'react';
import { clsx } from 'clsx';

interface WindowProps {
  title: ReactNode;
  children: ReactNode;
  className?: string;
  bodyClassName?: string;
  actions?: ReactNode;
  as?: 'section' | 'div' | 'aside';
  labelId?: string;
}

/** Window frame: 2px ink border, block shadow, title bar with three decorative squares. */
export function Window({ title, children, className, bodyClassName, actions, as: Tag = 'section', labelId }: WindowProps) {
  return (
    <Tag className={clsx('win min-w-0', className)} aria-labelledby={labelId}>
      <div className="flex items-center gap-2 border-b-2 border-ink bg-light px-[10px] py-[6px]">
        <h2 id={labelId} className="m-0 flex-grow text-[13px] font-bold uppercase tracking-[0.06em] text-ink">
          {title}
        </h2>
        {actions}
        <span aria-hidden="true" className="flex gap-2">
          {[0, 1, 2].map((i) => (
            <span key={i} className="block h-[14px] w-[14px] border-2 border-ink bg-card" />
          ))}
        </span>
      </div>
      <div className={bodyClassName}>{children}</div>
    </Tag>
  );
}
