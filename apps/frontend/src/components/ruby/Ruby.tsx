import { Fragment, useMemo, type ReactNode } from 'react';
import { parseRuby, type RubyNode } from './parse';

function renderNodes(nodes: RubyNode[]): ReactNode {
  return nodes.map((n, i) => {
    if (n.kind === 'text') return <Fragment key={i}>{n.text}</Fragment>;
    if (n.kind === 'ruby')
      return (
        <ruby key={i}>
          {n.base}
          <rt>{n.reading}</rt>
        </ruby>
      );
    return (
      <u key={i} className="target">
        {renderNodes(n.children)}
      </u>
    );
  });
}

/** Renders `漢字[よみ]` as ruby and `{{…}}` as an accent underline. */
export function Ruby({ text, className }: { text: string; className?: string }) {
  const nodes = useMemo(() => parseRuby(text), [text]);
  return (
    <span lang="ja" className={className}>
      {renderNodes(nodes)}
    </span>
  );
}
