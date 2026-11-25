import { render } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { parseRuby, stripRuby } from './parse';
import { Ruby } from './Ruby';

const html = (text: string) => render(<Ruby text={text} />).container.firstElementChild!.innerHTML;

describe('Ruby', () => {
  it('keeps strings without markup unchanged', () => {
    expect(parseRuby('ただの文です。')).toEqual([{ kind: 'text', text: 'ただの文です。' }]);
    expect(html('Xin chào, không có cú pháp')).toBe('Xin chào, không có cú pháp');
    expect(html('')).toBe('');
  });

  it('turns 漢字[よみ] into ruby', () => {
    expect(html('漢字[かんじ]')).toBe('<ruby>漢字<rt>かんじ</rt></ruby>');
  });

  it('takes only the kanji run as base, leaving preceding kana as text', () => {
    expect(parseRuby('面接[めんせつ]では緊張[きんちょう]した')).toEqual([
      { kind: 'ruby', base: '面接', reading: 'めんせつ' },
      { kind: 'text', text: 'では' },
      { kind: 'ruby', base: '緊張', reading: 'きんちょう' },
      { kind: 'text', text: 'した' },
    ]);
  });

  it('supports mixed kanji–kana tokens as base (fallback annotation)', () => {
    expect(parseRuby('を取り扱い[とりあつかい]')).toEqual([
      { kind: 'text', text: 'を' },
      { kind: 'ruby', base: '取り扱い', reading: 'とりあつかい' },
    ]);
  });

  it('turns {{…}} into an accent underline', () => {
    expect(html('{{緊張}}する')).toBe('<u class="target">緊張</u>する');
  });

  it('supports ruby inside the underline and nested underlines', () => {
    expect(html('では{{緊張[きんちょう]して}}、')).toBe(
      'では<u class="target"><ruby>緊張<rt>きんちょう</rt></ruby>して</u>、',
    );
    expect(parseRuby('{{a{{b}}c}}')).toEqual([
      {
        kind: 'target',
        children: [
          { kind: 'text', text: 'a' },
          { kind: 'target', children: [{ kind: 'text', text: 'b' }] },
          { kind: 'text', text: 'c' },
        ],
      },
    ]);
  });

  it('keeps malformed markup literally', () => {
    expect(html('{{未完')).toBe('{{未完');
    expect(html('[よみ]だけ')).toBe('[よみ]だけ');
    expect(html('漢字[abc]')).toBe('漢字[abc]');
    expect(html('closing }} alone')).toBe('closing }} alone');
  });

  it('keeps astral-plane kanji intact', () => {
    expect(parseRuby('𠮟[しか]る')).toEqual([
      { kind: 'ruby', base: '𠮟', reading: 'しか' },
      { kind: 'text', text: 'る' },
    ]);
  });

  it('stripRuby returns plain text', () => {
    expect(stripRuby('面接[めんせつ]では{{緊張[きんちょう]}}')).toBe('面接では緊張');
  });
});
