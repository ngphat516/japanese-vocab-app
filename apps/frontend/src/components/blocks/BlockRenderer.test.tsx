import { render, screen, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import { BlockRenderer, circled, countExamples } from './BlockRenderer';

const renderBlocks = (blocks: unknown[], startNumber?: number) =>
  render(
    <MemoryRouter>
      <BlockRenderer blocks={blocks} startNumber={startNumber} />
    </MemoryRouter>,
  );

describe('BlockRenderer', () => {
  it('renders nothing for empty content', () => {
    const { container } = renderBlocks([]);
    expect(container).toBeEmptyDOMElement();
  });

  it('renders meaning (vi + en)', () => {
    renderBlocks([{ type: 'meaning', vi: 'Căng thẳng, hồi hộp', en: 'tension' }]);
    expect(screen.getByText('Căng thẳng, hồi hộp')).toBeInTheDocument();
    expect(screen.getByText('tension')).toBeInTheDocument();
  });

  it('numbers examples ①②… and renders furigana + translation', () => {
    const { container } = renderBlocks([
      { type: 'example', ja: '面接[めんせつ]では{{緊張[きんちょう]して}}', vi: 'Tôi căng thẳng.' },
      { type: 'meaning', vi: 'xen giữa' },
      { type: 'example', ja: '初めての舞台', vi: null },
    ]);
    const examples = container.querySelectorAll('[data-block="example"]');
    expect(examples).toHaveLength(2);
    expect(examples[0]).toHaveTextContent('①');
    expect(examples[1]).toHaveTextContent('②');
    expect(examples[0]!.querySelector('ruby rt')).toHaveTextContent('めんせつ');
    expect(examples[0]!.querySelector('u.target')).toHaveTextContent('緊張');
    expect(screen.getByText('→ Tôi căng thẳng.')).toBeInTheDocument();
  });

  it('continues numbering from startNumber', () => {
    const { container } = renderBlocks([{ type: 'example', ja: '文' }], 3);
    expect(container.querySelector('[data-block="example"]')).toHaveTextContent('③');
  });

  it('renders usage chips: correct ✓ with --ok border, incorrect ✗ struck through on --light', () => {
    const { container } = renderBlocks([
      {
        type: 'usage',
        variants: [
          { ja: '緊張している', correct: true },
          { ja: '緊張だ', correct: false },
        ],
      },
    ]);
    const items = container.querySelectorAll('[data-block="usage"] li');
    expect(items[0]).toHaveClass('border-ok');
    expect(within(items[0] as HTMLElement).getByLabelText('Đúng')).toBeInTheDocument();
    expect(items[0]!.querySelector('s')).toBeNull();
    expect(items[1]).toHaveClass('bg-light');
    expect(within(items[1] as HTMLElement).getByLabelText('Sai')).toBeInTheDocument();
    expect(items[1]!.querySelector('s')).toHaveTextContent('緊張だ');
  });

  it('renders collocations joined by ·', () => {
    const { container } = renderBlocks([{ type: 'collocation', items: ['〜が解ける', '〜が高まる'] }]);
    const el = container.querySelector('[data-block="collocation"]')!;
    expect(el).toHaveTextContent('Kết hợp');
    expect(el).toHaveTextContent('〜が解ける · 〜が高まる');
  });

  it('links synonym/antonym/related items with a word_id to /?w=', () => {
    renderBlocks([
      { type: 'synonym', items: [{ text: '不安', word_id: 42 }, { text: '心配' }] },
      { type: 'antonym', items: [{ text: '安心', word_id: 7 }] },
      { type: 'related', items: [{ text: '緊迫' }] },
    ]);
    expect(screen.getByText('Đồng nghĩa')).toBeInTheDocument();
    expect(screen.getByText('Trái nghĩa')).toBeInTheDocument();
    expect(screen.getByText('Liên quan')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '不安' })).toHaveAttribute('href', '/?w=42');
    expect(screen.getByRole('link', { name: '安心' })).toHaveAttribute('href', '/?w=7');
    expect(screen.queryByRole('link', { name: '心配' })).toBeNull();
    expect(screen.getByText('心配')).toBeInTheDocument();
  });

  it('renders notes', () => {
    renderBlocks([{ type: 'note', text: 'Dùng trong văn viết.' }]);
    expect(screen.getByText('Ghi chú')).toBeInTheDocument();
    expect(screen.getByText('Dùng trong văn viết.')).toBeInTheDocument();
  });

  it('renders raw blocks (and unknown types) as JSON inside <details>', () => {
    const { container } = renderBlocks([
      { type: 'raw', data: { col: 'x', n: 1 } },
      { type: 'mystery', foo: 1 },
      'not-an-object',
    ]);
    const details = container.querySelectorAll('details');
    expect(details).toHaveLength(3);
    expect(details[0]!.querySelector('pre')!.textContent).toBe(JSON.stringify({ col: 'x', n: 1 }, null, 2));
    expect(details[1]).toHaveTextContent('mystery');
  });

  it('circled() and countExamples()', () => {
    expect([1, 2, 20, 21, 35, 36, 50].map(circled)).toEqual(['①', '②', '⑳', '㉑', '㉟', '㊱', '㊿']);
    expect(circled(51)).toBe('(51)');
    expect(countExamples([{ type: 'example', ja: 'a' }, { type: 'meaning', vi: 'b' }, { type: 'example', ja: 'c' }])).toBe(2);
  });
});
