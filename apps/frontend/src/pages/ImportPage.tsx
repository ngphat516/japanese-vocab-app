import * as Tabs from '@radix-ui/react-tabs';
import { useMutation, useQueries, useQuery, useQueryClient } from '@tanstack/react-query';
import { Check, Download, FileUp, Plus } from 'lucide-react';
import { useState, type FormEvent } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { clsx } from 'clsx';
import { z } from 'zod';
import { api } from '@/api/client';
import { downloadResponse, imports, textbooks, word } from '@/api/endpoints';
import type { ImportJob, ImportRow, MatchStatus, TextbookOut } from '@/api/types';
import { useAuth } from '@/auth/AuthProvider';
import { JlptBadge } from '@/components/JlptBadge';
import { Pager } from '@/components/Pager';
import { ErrorNote, Loading } from '@/components/Status';
import { Window } from '@/components/Window';

const RUNNING = new Set(['pending', 'processing', 'commit_pending', 'committing']);
const STATUS_LABEL: Record<string, string> = {
  pending: 'Đang chờ xử lý',
  processing: 'Đang đọc file',
  review: 'Chờ xem lại',
  commit_pending: 'Đang chờ ghi',
  committing: 'Đang ghi vào giáo trình',
  done: 'Hoàn tất',
  failed: 'Thất bại',
};
const ADAPTER_LABEL: Record<string, string> = {
  csv_template: 'CSV theo mẫu',
  mimikara: 'Mimikara',
  normalized_json: 'JSON chuẩn hoá',
  free_text: 'Văn bản tự do',
};
const JLPT = ['N1', 'N2', 'N3', 'N4', 'N5'] as const;

// ---------------------------------------------------------------- stepper
function Stepper({ step }: { step: 1 | 2 | 3 }) {
  const steps = ['Chọn nguồn & upload', 'Xem lại', 'Xác nhận'];
  return (
    <ol className="m-0 mt-6 flex list-none flex-wrap items-center gap-3 p-0">
      {steps.map((label, i) => {
        const n = (i + 1) as 1 | 2 | 3;
        const done = n < step;
        const current = n === step;
        return (
          <li key={label} aria-current={current ? 'step' : undefined} className="flex items-center gap-3">
            {i > 0 && <span aria-hidden="true" className={clsx('h-[2px] w-10', done || current ? 'bg-ink' : 'bg-mid')} />}
            <span
              className={clsx(
                'flex h-8 w-8 items-center justify-center border-2 font-bold',
                done ? 'border-ink bg-ink text-card' : current ? 'border-ink bg-card text-ink shadow-block-sm' : 'border-mid bg-card text-muted',
              )}
            >
              {done ? <Check aria-label="Xong" size={16} strokeWidth={3} /> : n}
            </span>
            <span className={clsx(current ? 'font-bold text-ink' : 'text-muted')}>{label}</span>
          </li>
        );
      })}
    </ol>
  );
}

// ---------------------------------------------------------------- step 1
const uploadSchema = z
  .object({
    textbook_id: z.coerce.number({ error: 'Chọn giáo trình' }).int().positive('Chọn giáo trình'),
    adapter: z.string().min(1, 'Chọn nguồn dữ liệu'),
    lesson_no: z.coerce.number().int().positive('Bài phải ≥ 1'),
    text: z.string().optional(),
    hasFile: z.boolean(),
  })
  .refine((v) => (v.adapter === 'free_text' ? Boolean(v.text?.trim()) : v.hasFile), {
    path: ['file'],
    message: 'Cần chọn file (hoặc dán văn bản với nguồn "Văn bản tự do")',
  });

function NewTextbook({ onCreated }: { onCreated: (b: TextbookOut) => void }) {
  const qc = useQueryClient();
  const [name, setName] = useState('');
  const create = useMutation({
    mutationFn: () => api<TextbookOut>('/textbooks', { method: 'POST', json: { name: name.trim(), visibility: 'private' } }),
    onSuccess: (b) => {
      void qc.invalidateQueries({ queryKey: ['textbooks'] });
      setName('');
      onCreated(b);
    },
  });
  return (
    <div className="flex flex-wrap items-center gap-2">
      <input
        aria-label="Tên giáo trình mới"
        placeholder="Tên giáo trình mới (riêng tư)"
        value={name}
        onChange={(e) => setName(e.target.value)}
        className="field h-10 max-w-[320px] flex-grow"
      />
      <button type="button" className="btn btn-secondary btn-sm h-10" disabled={!name.trim() || create.isPending} onClick={() => create.mutate()}>
        <Plus aria-hidden="true" size={16} /> Tạo
      </button>
      {create.isError && <ErrorNote error={create.error} />}
    </div>
  );
}

function UploadStep({ onJob }: { onJob: (job: ImportJob) => void }) {
  const adapters = useQuery({ queryKey: ['import-adapters'], queryFn: imports.adapters, staleTime: Infinity });
  const books = useQuery({ queryKey: ['textbooks'], queryFn: textbooks });
  const { user } = useAuth();
  const [adapter, setAdapter] = useState('csv_template');
  const [bookId, setBookId] = useState<number | ''>('');
  const [errors, setErrors] = useState<Record<string, string>>({});
  const upload = useMutation({ mutationFn: imports.upload, onSuccess: onJob });
  // Import needs write access: only the user's own textbooks.
  const owned = (books.data?.items ?? []).filter((b) => b.owner_id === user?.id);
  const current = adapters.data?.find((a) => a.name === adapter);

  const onSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    const file = fd.get('file');
    const hasFile = file instanceof File && file.size > 0;
    const parsed = uploadSchema.safeParse({
      textbook_id: bookId,
      adapter,
      lesson_no: fd.get('lesson_no'),
      text: (fd.get('text') as string | null) ?? undefined,
      hasFile,
    });
    if (!parsed.success) {
      const out: Record<string, string> = {};
      for (const i of parsed.error.issues) out[String(i.path[0])] ??= i.message;
      return setErrors(out);
    }
    setErrors({});
    const body = new FormData();
    body.set('textbook_id', String(parsed.data.textbook_id));
    body.set('adapter', adapter);
    body.set('lesson_no', String(parsed.data.lesson_no));
    body.set('include_proper_nouns', fd.get('include_proper_nouns') ? 'true' : 'false');
    body.set('exclude_jlpt', fd.getAll('exclude_jlpt').join(','));
    if (adapter === 'free_text') body.set('text', parsed.data.text ?? '');
    else if (file instanceof File) body.set('file', file);
    upload.mutate(body);
  };

  return (
    <Window title="1 · Chọn nguồn & upload" className="mt-6" bodyClassName="p-6">
      <form noValidate onSubmit={onSubmit} className="flex flex-col gap-6">
        <fieldset className="m-0 flex flex-col gap-2 border-0 p-0">
          <legend className="label mb-2">Giáo trình đích</legend>
          {books.isPending ? (
            <Loading />
          ) : (
            <select
              aria-label="Giáo trình đích"
              value={bookId}
              onChange={(e) => setBookId(e.target.value ? Number(e.target.value) : '')}
              className="field max-w-[420px]"
              aria-invalid={Boolean(errors.textbook_id)}
            >
              <option value="">— Chọn giáo trình —</option>
              {owned.map((b) => (
                <option key={b.id} value={b.id}>
                  {b.name}
                </option>
              ))}
            </select>
          )}
          {errors.textbook_id && <span className="text-[13px] font-semibold text-[var(--jlpt-n1-fg)]">{errors.textbook_id}</span>}
          <NewTextbook onCreated={(b) => setBookId(b.id)} />
        </fieldset>

        <fieldset className="m-0 border-0 p-0">
          <legend className="label mb-2">Nguồn dữ liệu (adapter)</legend>
          {adapters.isPending ? (
            <Loading />
          ) : adapters.isError ? (
            <ErrorNote error={adapters.error} />
          ) : (
            <div className="grid gap-3 [grid-template-columns:repeat(auto-fill,minmax(200px,1fr))]">
              {adapters.data.map((a) => (
                <label
                  key={a.name}
                  className={clsx(
                    'flex cursor-pointer items-start gap-2 border-2 border-ink p-3',
                    adapter === a.name ? 'bg-light shadow-block-sm' : 'bg-card',
                  )}
                >
                  <input type="radio" name="adapter" value={a.name} checked={adapter === a.name} onChange={() => setAdapter(a.name)} className="mt-1 accent-[var(--ink)]" />
                  <span>
                    <span className="block font-bold">{ADAPTER_LABEL[a.name] ?? a.name}</span>
                    <span className="text-[12px] uppercase text-muted">{a.formats.join(' · ')}</span>
                  </span>
                </label>
              ))}
            </div>
          )}
        </fieldset>

        {adapter === 'free_text' ? (
          <div className="flex flex-col gap-1">
            <label htmlFor="imp-text" className="label">Văn bản tiếng Nhật</label>
            <textarea id="imp-text" name="text" rows={6} className="field jp h-auto py-2" placeholder="面接では緊張して、うまく話せなかった。" />
          </div>
        ) : (
          <div className="flex flex-col gap-2">
            <label htmlFor="imp-file" className="label">File {current ? `(${current.formats.join(', ')})` : ''}</label>
            <input
              id="imp-file"
              name="file"
              type="file"
              accept={current?.formats.map((f) => `.${f}`).join(',')}
              className="text-[14px] file:mr-3 file:h-10 file:cursor-pointer file:border-2 file:border-ink file:bg-card file:px-3 file:font-bold file:text-ink"
            />
            <button
              type="button"
              className="btn btn-secondary btn-sm self-start"
              onClick={async () => downloadResponse(await imports.template(), 'template.csv')}
            >
              <Download aria-hidden="true" size={16} /> Tải file mẫu CSV
            </button>
          </div>
        )}
        {errors.file && <span className="text-[13px] font-semibold text-[var(--jlpt-n1-fg)]">{errors.file}</span>}

        <details className="border-2 border-dashed border-mid p-3">
          <summary className="cursor-pointer font-bold">Tuỳ chọn nâng cao</summary>
          <div className="mt-3 flex flex-col gap-3">
            <label className="flex items-center gap-2">
              Bài số
              <input name="lesson_no" type="number" min={1} defaultValue={1} className="field h-9 w-24" />
            </label>
            <label className="flex items-center gap-2">
              <input type="checkbox" name="include_proper_nouns" className="accent-[var(--ink)]" /> Giữ danh từ riêng
            </label>
            <fieldset className="m-0 flex flex-wrap items-center gap-3 border-0 p-0">
              <legend className="mb-1">Bỏ qua cấp JLPT</legend>
              {JLPT.map((l) => (
                <label key={l} className="flex items-center gap-1">
                  <input type="checkbox" name="exclude_jlpt" value={l} className="accent-[var(--ink)]" /> {l}
                </label>
              ))}
            </fieldset>
          </div>
        </details>

        {upload.isError && <ErrorNote error={upload.error} />}
        <button type="submit" className="btn btn-primary self-start" disabled={upload.isPending}>
          <FileUp aria-hidden="true" size={16} /> {upload.isPending ? 'Đang tải lên…' : 'Tải lên & phân tích'}
        </button>
      </form>
    </Window>
  );
}

// ---------------------------------------------------------------- step 2
function rowMeaning(row: ImportRow): string {
  for (const b of row.content as { type?: string; vi?: string; en?: string }[]) if (b?.type === 'meaning') return b.vi ?? b.en ?? '';
  return '';
}

function RowChoices({ job, row }: { job: ImportJob; row: ImportRow }) {
  const qc = useQueryClient();
  const words = useQueries({
    queries: row.candidate_word_ids.map((id) => ({ queryKey: ['word', id], queryFn: () => word(id), staleTime: 5 * 60_000 })),
  });
  const review = useMutation({
    mutationFn: (body: { chosen_word_id: number } | { skipped: true }) => imports.review(job.id, row.id, body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['import', job.id] });
    },
  });
  const name = `row-${row.id}`;
  const value = row.match_status === 'skipped' ? 'skip' : row.chosen_word_id ? String(row.chosen_word_id) : '';
  if (!row.candidate_word_ids.length)
    return <span className="text-[13px] text-muted">{row.match_status === 'skipped' ? 'Đã bỏ qua' : 'Không khớp từ điển · sẽ tạo từ mới'}</span>;
  return (
    <div role="radiogroup" aria-label={`Chọn từ cho dòng ${row.row_no}`} className="flex flex-wrap gap-2">
      {row.candidate_word_ids.map((id, i) => {
        const w = words[i]?.data?.word;
        return (
          <label key={id} className={clsx('flex cursor-pointer items-center gap-2 border-2 px-3 py-2', value === String(id) ? 'border-ink bg-light' : 'border-mid bg-card')}>
            <input
              type="radio"
              name={name}
              checked={value === String(id)}
              disabled={review.isPending || job.status !== 'review'}
              onChange={() => review.mutate({ chosen_word_id: id })}
              className="accent-[var(--ink)]"
            />
            <span lang="ja" className="jp">{w ? w.kanji || w.kana : `#${id}`}</span>
            {w && <span className="text-[13px] text-muted">{w.kana}{w.hanviet ? ` · ${w.hanviet}` : ''}</span>}
            {w && <JlptBadge level={w.jlpt_level} />}
          </label>
        );
      })}
      <label className={clsx('flex cursor-pointer items-center gap-2 border-2 border-dashed px-3 py-2', value === 'skip' ? 'border-ink bg-light' : 'border-mid')}>
        <input type="radio" name={name} checked={value === 'skip'} disabled={review.isPending || job.status !== 'review'} onChange={() => review.mutate({ skipped: true })} className="accent-[var(--ink)]" />
        Bỏ qua dòng
      </label>
      {review.isError && <ErrorNote error={review.error} />}
    </div>
  );
}

const TABS: { id: string; label: (j: ImportJob) => string; status?: MatchStatus }[] = [
  { id: 'all', label: (j) => `Tất cả (${j.total})` },
  { id: 'ambiguous', label: (j) => `Cần chọn (${j.ambiguous})`, status: 'ambiguous' },
  { id: 'none', label: (j) => `Lỗi / không khớp${j.failed ? ` · ${j.failed} lỗi` : ''}`, status: 'none' },
];

function RowsTable({ job, status }: { job: ImportJob; status?: MatchStatus }) {
  const [page, setPage] = useState(1);
  const rows = useQuery({
    queryKey: ['import', job.id, 'rows', status ?? 'all', page],
    queryFn: () => imports.rows(job.id, status, page, 20),
  });
  if (rows.isPending) return <Loading />;
  if (rows.isError) return <div className="p-4"><ErrorNote error={rows.error} /></div>;
  if (!rows.data.items.length) return <p className="m-0 p-5 text-muted">Không có dòng nào.</p>;
  return (
    <div className="px-4 pb-2 md:px-6">
      <div className="hidden grid-cols-[60px_1fr_2fr] gap-4 border-b-2 border-light py-3 text-[12px] font-bold uppercase text-muted md:grid">
        <span>Dòng</span>
        <span>Dữ liệu gốc</span>
        <span>Chọn từ khớp</span>
      </div>
      {rows.data.items.map((r) => (
        <div key={r.id} className="grid grid-cols-1 items-start gap-2 border-b-2 border-dashed border-light py-4 md:grid-cols-[60px_1fr_2fr] md:gap-4">
          <span className="text-muted">#{r.row_no}</span>
          <div>
            <div lang="ja" className="jp text-[18px]">{r.kanji || r.kana}</div>
            <div className="text-[13px] text-muted">
              <span lang="ja" className="jp">{r.kana}</span>
              {rowMeaning(r) ? ` · ${rowMeaning(r)}` : ''} · bài {r.lesson_no} #{r.order_no}
            </div>
          </div>
          <RowChoices job={job} row={r} />
        </div>
      ))}
      <Pager page={page} size={20} total={rows.data.total} onPage={setPage} />
    </div>
  );
}

function ReviewStep({ job, onBack, onNext }: { job: ImportJob; onBack: () => void; onNext: () => void }) {
  const [tab, setTab] = useState('all');
  if (job.status !== 'review')
    return (
      <Window title="2 · Xem lại" className="mt-6" bodyClassName="p-6 flex flex-col gap-4">
        <JobProgress job={job} />
        {job.status === 'failed' && (
          <button type="button" className="btn btn-secondary self-start" onClick={onBack}>
            ← Upload lại
          </button>
        )}
      </Window>
    );
  return (
    <>
      <section className="win mt-6">
        <div className="flex flex-wrap items-center gap-6 border-b-2 border-ink px-6 py-5">
          <div className="flex-grow">
            <div className="font-bold">{job.file_key.split('/').pop()}</div>
            <div className="text-[13px] text-muted">Nguồn: {ADAPTER_LABEL[job.adapter] ?? job.adapter}</div>
          </div>
          <div className="flex gap-5 text-[14px]">
            <div><b className="text-[20px]">{job.matched}</b> <span className="text-muted">hợp lệ</span></div>
            <div><b className="text-[20px]" style={{ color: 'var(--jlpt-n2-fg)' }}>{job.ambiguous}</b> <span className="text-muted">cần chọn</span></div>
            <div><b className="text-[20px]" style={{ color: 'var(--jlpt-n1-fg)' }}>{job.failed}</b> <span className="text-muted">lỗi</span></div>
          </div>
        </div>
        <Tabs.Root value={tab} onValueChange={setTab}>
          <Tabs.List aria-label="Lọc dòng" className="flex flex-wrap gap-1 border-b-2 border-ink bg-light px-4">
            {TABS.map((t) => (
              <Tabs.Trigger
                key={t.id}
                value={t.id}
                className="-mb-[2px] border-b-[3px] border-transparent px-[14px] py-3 font-semibold text-muted data-[state=active]:border-ink data-[state=active]:text-ink"
              >
                {t.label(job)}
              </Tabs.Trigger>
            ))}
          </Tabs.List>
          {TABS.map((t) => (
            <Tabs.Content key={t.id} value={t.id} className="outline-none">
              {tab === t.id && <RowsTable job={job} status={t.status} />}
            </Tabs.Content>
          ))}
        </Tabs.Root>
        {job.error && <div className="p-4"><ErrorNote error={new Error(job.error)} /></div>}
      </section>
      <div className="mt-5 flex flex-wrap justify-between gap-3">
        <button type="button" className="btn btn-secondary" onClick={onBack}>← Quay lại</button>
        <div className="flex items-center gap-3">
          {job.ambiguous > 0 && <span className="text-[13px] text-muted">Còn {job.ambiguous} dòng chưa chọn</span>}
          <button type="button" className="btn btn-primary" disabled={job.ambiguous > 0} onClick={onNext}>
            Tiếp tục: Xác nhận →
          </button>
        </div>
      </div>
    </>
  );
}

// ---------------------------------------------------------------- step 3
function JobProgress({ job }: { job: ImportJob }) {
  const { processed, total } = job.progress;
  const pct = total ? Math.round((processed / total) * 100) : 0;
  return (
    <div className="flex flex-col gap-2" role="status">
      <div className="font-bold">{STATUS_LABEL[job.status] ?? job.status}</div>
      {RUNNING.has(job.status) && (
        <div className="h-4 w-full max-w-[420px] border-2 border-ink bg-card">
          <div className="h-full bg-ink transition-[width]" style={{ width: `${pct}%` }} />
        </div>
      )}
      {RUNNING.has(job.status) && total > 0 && <div className="text-[13px] text-muted">{processed}/{total} dòng</div>}
      {job.status === 'failed' && <ErrorNote error={new Error(job.error ?? 'Import thất bại')} />}
    </div>
  );
}

function ConfirmStep({ job, onBack, onReset }: { job: ImportJob; onBack: () => void; onReset: () => void }) {
  const qc = useQueryClient();
  const commit = useMutation({
    mutationFn: () => imports.commit(job.id),
    onSettled: () => void qc.invalidateQueries({ queryKey: ['import', job.id] }),
  });
  const done = job.status === 'done';
  const busy = RUNNING.has(job.status) || commit.isPending;
  return (
    <Window title="3 · Xác nhận" className="mt-6" bodyClassName="p-6 flex flex-col gap-4">
      {job.status === 'review' && !commit.isPending ? (
        <>
          <p className="m-0 text-[15px]">
            Ghi <b>{job.matched}</b> dòng vào giáo trình. Các dòng không khớp từ điển sẽ tạo từ mới, dòng bị bỏ qua sẽ không được ghi.
          </p>
          {commit.isError && <ErrorNote error={commit.error} />}
          <div className="flex flex-wrap gap-3">
            <button type="button" className="btn btn-secondary" onClick={onBack}>← Xem lại</button>
            <button type="button" className="btn btn-primary" onClick={() => commit.mutate()}>Xác nhận import</button>
          </div>
        </>
      ) : (
        <JobProgress job={job} />
      )}
      {done && (
        <div className="flex flex-wrap gap-3">
          <Link to="/" className="btn btn-primary no-underline">Tra từ</Link>
          <button type="button" className="btn btn-secondary" onClick={onReset}>Import tiếp</button>
        </div>
      )}
      {busy && <p className="m-0 text-[13px] text-muted">Có thể rời trang; tiến trình vẫn chạy ở máy chủ.</p>}
    </Window>
  );
}

// ---------------------------------------------------------------- page
export default function ImportPage() {
  const [params, setParams] = useSearchParams();
  const jobId = Number(params.get('job')) || undefined;
  const confirm = params.get('step') === '3';
  const qc = useQueryClient();

  const job = useQuery({
    queryKey: ['import', jobId],
    queryFn: () => imports.job(jobId!),
    enabled: Boolean(jobId),
    refetchInterval: (q) => (q.state.data && RUNNING.has(q.state.data.status) ? 1500 : false),
  });

  const go = (next: Record<string, string>) => setParams(next, { replace: false });
  const step: 1 | 2 | 3 = !jobId ? 1 : confirm || job.data?.status === 'done' || job.data?.status === 'committing' || job.data?.status === 'commit_pending' ? 3 : 2;

  return (
    <main className="mx-auto max-w-[960px] px-4 pt-6 md:px-6">
      <h1 className="m-0 text-[28px] font-extrabold uppercase">Import giáo trình</h1>
      <Stepper step={step} />
      {step === 1 && (
        <UploadStep
          onJob={(j) => {
            qc.setQueryData(['import', j.id], j);
            go({ job: String(j.id) });
          }}
        />
      )}
      {step > 1 &&
        (job.isPending ? (
          <Loading />
        ) : job.isError ? (
          <div className="mt-6"><ErrorNote error={job.error} /></div>
        ) : step === 2 ? (
          <ReviewStep job={job.data} onBack={() => go({})} onNext={() => go({ job: String(jobId), step: '3' })} />
        ) : (
          <ConfirmStep job={job.data} onBack={() => go({ job: String(jobId) })} onReset={() => go({})} />
        ))}
    </main>
  );
}
