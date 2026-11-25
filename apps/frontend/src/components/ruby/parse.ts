// Parser for the backend furigana markup:
//   漢字[よみ]   → <ruby>漢字<rt>よみ</rt></ruby>
//   {{…}}       → target-word underline, may nest and contain ruby
// Strings without markup are returned as a single text node.

export type RubyNode =
  | { kind: 'text'; text: string }
  | { kind: 'ruby'; base: string; reading: string }
  | { kind: 'target'; children: RubyNode[] };

const HAN = '\\u4E00-\\u9FFF\\u3400-\\u4DBF\\uF900-\\uFAFF\\u{20000}-\\u{323AF}々〆ヶ';
const KANA = 'ぁ-ヿ';
const READING = /^\[([ぁ-ゖァ-ヺー\s]+)\]/u;
const TRAILING_BASE = new RegExp(`[${HAN}${KANA}]+$`, 'u');
const HAS_HAN = new RegExp(`[${HAN}]`, 'u');
const LEADING_KANA = new RegExp(`^[${KANA}]+(?=[${HAN}])`, 'u');

/** Picks the ruby base from the end of the pending text: the trailing run of
 *  kanji/kana, minus leading kana before the first kanji (では緊張 → 緊張). */
function splitBase(text: string): [rest: string, base: string] {
  const m = TRAILING_BASE.exec(text);
  if (!m) return [text, ''];
  let base = m[0];
  if (HAS_HAN.test(base)) base = base.replace(LEADING_KANA, '');
  return [text.slice(0, text.length - base.length), base];
}

function parseLevel(
  src: string,
  start: number,
  nested: boolean,
): { nodes: RubyNode[]; end: number; closed: boolean } {
  const nodes: RubyNode[] = [];
  let buf = '';
  const flush = () => {
    if (buf) nodes.push({ kind: 'text', text: buf });
    buf = '';
  };
  let i = start;
  while (i < src.length) {
    if (nested && src.startsWith('}}', i)) {
      flush();
      return { nodes, end: i + 2, closed: true };
    }
    if (src.startsWith('{{', i)) {
      const inner = parseLevel(src, i + 2, true);
      if (inner.closed) {
        flush();
        nodes.push({ kind: 'target', children: inner.nodes });
        i = inner.end;
        continue;
      }
      // Unbalanced "{{": keep literally.
      buf += '{{';
      i += 2;
      continue;
    }
    if (src[i] === '[') {
      const m = READING.exec(src.slice(i));
      if (m) {
        const [rest, base] = splitBase(buf);
        if (base) {
          buf = rest;
          flush();
          nodes.push({ kind: 'ruby', base, reading: m[1]!.trim() });
          i += m[0].length;
          continue;
        }
      }
    }
    // Iterate by code point so astral kanji stay intact.
    const ch = String.fromCodePoint(src.codePointAt(i)!);
    buf += ch;
    i += ch.length;
  }
  flush();
  return { nodes, end: i, closed: false };
}

export function parseRuby(src: string): RubyNode[] {
  return parseLevel(src, 0, false).nodes;
}

/** Plain text without markup (for aria/search). */
export function stripRuby(src: string): string {
  const walk = (nodes: RubyNode[]): string =>
    nodes
      .map((n) => (n.kind === 'text' ? n.text : n.kind === 'ruby' ? n.base : walk(n.children)))
      .join('');
  return walk(parseRuby(src));
}
