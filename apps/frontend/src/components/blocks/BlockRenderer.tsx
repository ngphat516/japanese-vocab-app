import { Check, X } from 'lucide-react';
import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import type { Block, RelatedItem } from '@/api/types';
import { Ruby } from '../ruby/Ruby';

const CIRCLED_1_20 = 0x2460;
const CIRCLED_21_35 = 0x3251;
const CIRCLED_36_50 = 0x32b1;

/** ① ② … ㊿, then (51) (52) … */
export function circled(n: number): string {
  if (n >= 1 && n <= 20) return String.fromCodePoint(CIRCLED_1_20 + n - 1);
  if (n >= 21 && n <= 35) return String.fromCodePoint(CIRCLED_21_35 + n - 21);
  if (n >= 36 && n <= 50) return String.fromCodePoint(CIRCLED_36_50 + n - 36);
  return `(${n})`;
}

const RELATION_LABEL = { synonym: 'Đồng nghĩa', antonym: 'Trái nghĩa', related: 'Liên quan' } as const;

function Label({ children }: { children: ReactNode }) {
  return <span className="mr-2 font-ui text-[12px] font-bold uppercase tracking-[0.04em] text-muted">{children}</span>;
}

function Related({ item }: { item: RelatedItem }) {
  if (item.word_id)
    return (
      <Link to={`/?w=${item.word_id}`} className="text-ink underline decoration-2 underline-offset-4 hover:text-acc-text">
        <Ruby text={item.text} />
      </Link>
    );
  return <Ruby text={item.text} />;
}

function isBlock(value: unknown): value is Block {
  return typeof value === 'object' && value !== null && typeof (value as { type?: unknown }).type === 'string';
}

function RawBlockView({ data }: { data: unknown }) {
  return (
    <details className="border-2 border-dashed border-light p-2 text-[13px]">
      <summary className="cursor-pointer font-semibold text-muted">Dữ liệu gốc (JSON)</summary>
      <pre className="m-0 mt-2 overflow-x-auto whitespace-pre-wrap break-all text-[12px] text-ink">
        {JSON.stringify(data, null, 2)}
      </pre>
    </details>
  );
}

interface Props {
  blocks: readonly unknown[] | null | undefined;
  /** Number examples starting from this value (default 1). */
  startNumber?: number;
}

/** Renders entry content blocks: meaning, example, usage, collocation, relations, note, raw. */
export function BlockRenderer({ blocks, startNumber = 1 }: Props) {
  if (!blocks?.length) return null;
  let exampleNo = startNumber - 1;
  return (
    <div className="flex flex-col gap-[14px]" data-testid="blocks">
      {blocks.map((b, i) => {
        if (!isBlock(b)) return <RawBlockView key={i} data={b} />;
        switch (b.type) {
          case 'meaning':
            return (
              <div key={i} data-block="meaning">
                {b.vi && <div className="text-[16px] font-semibold text-ink">{b.vi}</div>}
                {b.en && <div lang="en" className="text-muted">{b.en}</div>}
              </div>
            );
          case 'example': {
            exampleNo += 1;
            return (
              <div key={i} data-block="example">
                <div className="jp text-[18px] leading-[2.1] text-ink">
                  <span aria-hidden="true">{circled(exampleNo)} </span>
                  <Ruby text={b.ja} />
                </div>
                {b.vi && <div className="text-muted">→ {b.vi}</div>}
              </div>
            );
          }
          case 'usage':
            return (
              <div key={i} data-block="usage" className="flex flex-col gap-2">
                {b.context && (
                  <div className="jp text-muted">
                    <Ruby text={b.context} />
                  </div>
                )}
                <ul className="m-0 flex list-none flex-wrap gap-2 p-0 jp">
                  {b.variants.map((v, j) =>
                    v.correct ? (
                      <li key={j} className="flex items-center gap-1 border-2 border-ok bg-card px-3 py-1 text-ink">
                        <Check aria-label="Đúng" size={14} strokeWidth={3} className="text-ok" />
                        <Ruby text={v.ja} />
                      </li>
                    ) : (
                      <li key={j} className="flex items-center gap-1 border-2 border-light bg-light px-3 py-1 text-muted">
                        <X aria-label="Sai" size={14} strokeWidth={3} />
                        <s>
                          <Ruby text={v.ja} />
                        </s>
                      </li>
                    ),
                  )}
                </ul>
                {b.vi && <div className="text-muted">{b.vi}</div>}
              </div>
            );
          case 'collocation':
            return (
              <div key={i} data-block="collocation" className="border-t-2 border-dashed border-light pt-3 jp text-[16px]">
                <Label>
                  Kết hợp <span lang="ja">連</span>
                </Label>
                {b.items.map((it, j) => (
                  <span key={j}>
                    {j > 0 && <span className="text-muted"> · </span>}
                    <Ruby text={it} />
                  </span>
                ))}
                {b.vi && <div className="font-ui text-[14px] text-muted">{b.vi}</div>}
              </div>
            );
          case 'synonym':
          case 'antonym':
          case 'related':
            return (
              <div key={i} data-block={b.type} className="jp text-[16px]">
                <Label>{RELATION_LABEL[b.type]}</Label>
                {b.items.map((it, j) => (
                  <span key={j}>
                    {j > 0 && <span className="text-muted"> · </span>}
                    <Related item={it} />
                  </span>
                ))}
              </div>
            );
          case 'note':
            return (
              <div key={i} data-block="note" className="border-l-4 border-acc bg-card pl-3 text-ink">
                <Label>Ghi chú</Label>
                <Ruby text={b.text} />
              </div>
            );
          case 'raw':
            return <RawBlockView key={i} data={b.data} />;
          default:
            return <RawBlockView key={i} data={b} />;
        }
      })}
    </div>
  );
}

/** Number of example blocks, for continuing numbering across sections. */
export const countExamples = (blocks: readonly unknown[] | null | undefined) =>
  (blocks ?? []).filter((b) => isBlock(b) && b.type === 'example').length;
