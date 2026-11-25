import { useState } from 'react';
import { Hero } from '@/components/Hero';
import { SearchBox } from '@/components/SearchBox';

export function SearchPage() {
  const [q, setQ] = useState('');
  return <Hero search={<SearchBox value={q} onChange={setQ} />} />;
}
