import { useEffect, useState } from 'react'
import { abs } from '../lib/abs'

/** The furniture the four special education reports share.
 *
 *  WHY THIS IS A COMPONENT AND NOT FOUR COPIES. Four reports that must stay apart still
 *  have to LOOK like four readings of one archive, or a reader will take the difference in
 *  presentation for a difference in confidence. What is shared here is the frame — the
 *  headings, the "what this does not show" box, the hypothesis box, the provenance block,
 *  the coverage note. What is emphatically NOT shared is a number: no component in this
 *  file accepts a figure from more than one report at a time.
 *
 *  THE HYPOTHESIS BOX HAS ITS OWN COLOUR AND ITS OWN LABEL. Rule 7: a figure is a fact and
 *  an explanation for it is not, and the whole of this project's error history is the two
 *  being set in the same voice one paragraph apart. */

export type Said = {
  key: string; board: string; date: string; quote: string; why: string
  cite: string; town: string
}

export type Source = {
  path: string; sha256: string; bytes: number; url: string; docs_url: string
  table: string; publisher: string; note: string
}

export type Minutes = {
  published: number; held: number; searchable: number; unsearchable: number
  image_scan: number; searchable_share: number; text_files_present: number
  first_date: string; last_date: string
}

export type Base = {
  about: string; grain: string; sources: Source[]
  said: Said[]; searched: { term: string; documents: number }[]
  minutes: Minutes; not_established: string[]; closes: string
}

export function H2({ id, children }: { id?: string; children: React.ReactNode }) {
  return (
    <h2 id={id} className="text-2xl font-bold tracking-tight mt-14 mb-3 max-w-3xl
                           scroll-mt-[calc(var(--header-h)+1rem)]">{children}</h2>
  )
}

export function H3({ children }: { children: React.ReactNode }) {
  return <h3 className="text-[15px] font-bold mt-9 mb-1 max-w-2xl">{children}</h3>
}

export function Body({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-[15px] leading-relaxed max-w-2xl mt-3"
      style={{ color: 'var(--text-secondary)' }}>{children}</p>
  )
}

export function Stat({ value, tone, children }: {
  value: string; tone?: string; children: React.ReactNode
}) {
  return (
    <div>
      <div className="text-3xl font-bold tracking-tight tnum"
        style={tone ? { color: tone } : undefined}>{value}</div>
      <div className="text-[13px] leading-snug mt-1 max-w-[15rem]"
        style={{ color: 'var(--text-secondary)' }}>{children}</div>
    </div>
  )
}

export function Insight({ n, headline, children }: {
  n: number; headline: React.ReactNode; children: React.ReactNode
}) {
  return (
    <div className="card p-5">
      <div className="text-[11px] font-semibold uppercase tracking-widest mb-2"
        style={{ color: 'var(--text-muted)' }}>Finding {n}</div>
      <p className="text-[17px] font-bold leading-snug">{headline}</p>
      <div className="text-[14px] leading-relaxed mt-2.5"
        style={{ color: 'var(--text-secondary)' }}>{children}</div>
    </div>
  )
}

/** The half of every section that says what the measurement does NOT establish. */
export function NotShown({ children }: { children: React.ReactNode }) {
  return (
    <div className="card p-4 mt-5 max-w-2xl" style={{ borderLeft: '4px solid var(--axis)' }}>
      <p className="text-[11px] font-semibold uppercase tracking-widest mb-1.5"
        style={{ color: 'var(--text-muted)' }}>What this does not show</p>
      <div className="text-[14px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
        {children}
      </div>
    </div>
  )
}

/** A hypothesis, marked as one. Never rendered in the same voice as a measurement. */
export function Maybe({ settle, children }: {
  settle: React.ReactNode; children: React.ReactNode
}) {
  return (
    <div className="card p-4 mt-4 max-w-2xl"
      style={{ borderLeft: '4px solid var(--status-warning)' }}>
      <p className="text-[11px] font-semibold uppercase tracking-widest mb-1.5"
        style={{ color: 'var(--text-muted)' }}>
        A possible explanation &mdash; nothing here tests it
      </p>
      <div className="text-[14px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
        {children}
        <p className="mt-2.5"><strong>What would settle it:</strong> {settle}</p>
      </div>
    </div>
  )
}

/** What GRAIN this report is at, said at the top of it. The four reports exist because
 *  these four are different, so each one states its own before anything else. */
export function Grain({ children }: { children: React.ReactNode }) {
  return (
    <div className="card p-3.5 mt-6 max-w-2xl"
      style={{ borderLeft: '4px solid var(--fund-school)' }}>
      <p className="text-[11px] font-semibold uppercase tracking-widest mb-1"
        style={{ color: 'var(--text-muted)' }}>What this report counts</p>
      <p className="text-[13.5px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
        {children}
      </p>
    </div>
  )
}

export function Quote({ q }: { q: Said }) {
  return (
    <div className="card p-4">
      <p className="text-[15px] leading-relaxed">&ldquo;{q.quote}&rdquo;</p>
      <p className="text-[12px] mt-2" style={{ color: 'var(--text-muted)' }}>
        {q.board} &middot; {q.date} &middot;{' '}
        <a className="underline" style={{ color: 'var(--series-cost)' }}
          href={abs(q.cite)}>our copy</a>{' '}
        &middot; <a className="underline" style={{ color: 'var(--series-cost)' }}
          href={q.town}>the town&rsquo;s</a>
      </p>
      <p className="text-[13.5px] leading-relaxed mt-2.5"
        style={{ color: 'var(--text-secondary)' }}>{q.why}</p>
    </div>
  )
}

const kb = (n: number) => (n >= 1e6 ? `${(n / 1e6).toFixed(1)} MB` : `${Math.round(n / 1024)} KB`)

/** Rule 12, rendered: the address, the publisher's own filename, our copy, the sha256. */
export function Provenance({ sources }: { sources: Source[] }) {
  return (
    <div className="grid gap-3 mt-5 sm:grid-cols-2">
      {sources.map(s => (
        <div key={s.path} className="card p-4">
          <p className="text-[13.5px] font-bold leading-snug break-words">
            {s.path.split('/').pop()}
          </p>
          <p className="text-[12.5px] mt-1" style={{ color: 'var(--text-secondary)' }}>
            {s.publisher}
          </p>
          <p className="text-[13px] leading-relaxed mt-2"
            style={{ color: 'var(--text-secondary)' }}>{s.note}</p>
          <p className="text-[11.5px] mt-2.5" style={{ color: 'var(--text-muted)' }}>
            table <code>{s.table}</code> &middot; {kb(s.bytes)}
          </p>
          <p className="text-[11px] mt-1 break-all" style={{ color: 'var(--text-muted)' }}>
            sha256 {s.sha256.slice(0, 16)}&hellip;
          </p>
          <p className="text-[12px] mt-2">
            <a className="underline" style={{ color: 'var(--series-cost)' }}
              href={abs(s.docs_url)}>our copy</a>
            {s.url ? <> &middot; <a className="underline"
              style={{ color: 'var(--series-cost)' }} href={s.url}>the publisher&rsquo;s</a></> : null}
          </p>
        </div>
      ))}
    </div>
  )
}

/** The denominator, printed beside every search. A grep that finds nothing prints
 *  nothing, and nothing reads as "nobody said it". */
export function Coverage({ m, searched }: {
  m: Minutes; searched: { term: string; documents: number }[]
}) {
  return (
    <>
      <div className="flex flex-wrap gap-x-10 gap-y-4 mt-5">
        {searched.map(s => (
          <div key={s.term}>
            <div className="text-2xl font-bold tnum">{s.documents}</div>
            <div className="text-[12.5px] mt-0.5" style={{ color: 'var(--text-secondary)' }}>
              documents mention &ldquo;{s.term}&rdquo;
            </div>
          </div>
        ))}
      </div>
      <p className="text-[13px] leading-relaxed max-w-2xl mt-4"
        style={{ color: 'var(--text-muted)' }}>
        Searched {m.searchable.toLocaleString()} of the {m.held.toLocaleString()} meeting
        documents this archive holds ({Math.round(m.searchable_share * 100)}%), covering{' '}
        {m.first_date} to {m.last_date}. The other{' '}
        {m.unsearchable.toLocaleString()} carry no text a search can match &mdash;{' '}
        {m.image_scan.toLocaleString()} of them are image scans awaiting OCR. An empty
        result above is a statement about what can be read, never about what was said.
      </p>
    </>
  )
}

export function NotEstablished({ rows, closes }: { rows: string[]; closes: string }) {
  return (
    <>
      <ul className="mt-5 space-y-3 max-w-2xl">
        {rows.map(r => (
          <li key={r} className="text-[14px] leading-relaxed pl-4 border-l-2"
            style={{ color: 'var(--text-secondary)', borderColor: 'var(--axis)' }}>{r}</li>
        ))}
      </ul>
      <div className="card p-4 mt-5 max-w-2xl"
        style={{ borderLeft: '4px solid var(--status-good)' }}>
        <p className="text-[11px] font-semibold uppercase tracking-widest mb-1.5"
          style={{ color: 'var(--text-muted)' }}>What would close these</p>
        <p className="text-[14px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
          {closes} Every limit on this page is also a row in{' '}
          <a className="underline" style={{ color: 'var(--series-cost)' }}
            href={abs('/what-we-cannot-answer')}>what we cannot answer</a>, which is the
          single registry the records request reads from.
        </p>
      </div>
    </>
  )
}

/** The four reports, as links, at the foot of each of them. Named for what each COUNTS,
 *  so a reader crossing from one to another is told the grain changed. */
export function OtherReports({ here }: { here: string }) {
  const all = [
    { slug: 'how-many-students-are-on-an-iep', name: 'How many students', what: 'children' },
    { slug: 'where-students-go-instead', name: 'Who leaves, and where they go', what: 'children, with no disability flag' },
    { slug: 'what-special-education-costs', name: 'What it costs, and what comes back', what: 'dollars' },
    { slug: 'who-ends-up-out-of-district', name: 'The route out of district', what: 'placements' },
  ].filter(r => r.slug !== here)
  return (
    <div className="grid gap-3 mt-5 sm:grid-cols-3">
      {all.map(r => (
        <a key={r.slug} href={abs(`/${r.slug}`)}
          className="card block p-4 min-h-[44px] transition-opacity hover:opacity-90">
          <span className="text-[15px] font-bold leading-tight"
            style={{ color: 'var(--series-cost)' }}>{r.name} &rarr;</span>
          <span className="block text-[12.5px] mt-1.5" style={{ color: 'var(--text-muted)' }}>
            counts {r.what}
          </span>
        </a>
      ))}
    </div>
  )
}

/** Load one payload, and render nothing rather than something stale if it is missing. */
export function useReport<T>(file: string) {
  const [d, setD] = useState<T | null>(null)
  const [err, setErr] = useState<string | null>(null)
  useEffect(() => {
    let live = true
    fetch(`/data/${file}`)
      .then(r => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then(j => { if (live) setD(j as T) })
      .catch(e => { if (live) setErr(String(e)) })
    return () => { live = false }
  }, [file])
  return { d, err }
}

export function Shell({ title, standfirst, err, loading, children }: {
  title: string; standfirst?: string; err?: string | null; loading?: boolean
  children?: React.ReactNode
}) {
  return (
    <div className="mx-auto max-w-6xl px-5 pt-14 pb-16">
      <h1 className="text-3xl font-bold tracking-tight max-w-3xl">{title}</h1>
      {standfirst && (
        <p className="text-[15px] leading-relaxed max-w-2xl mt-3"
          style={{ color: 'var(--text-secondary)' }}>{standfirst}</p>
      )}
      {err && (
        <div className="card p-5 mt-8" style={{ borderLeft: '4px solid var(--status-warning)' }}>
          <p className="text-[15px] font-bold mb-1">The series did not load</p>
          <p className="text-[13.5px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
            {err}. Nothing on this page is typed into it, so with the file missing there is
            nothing to show rather than something stale.
          </p>
        </div>
      )}
      {loading && !err && (
        <p className="mt-6 text-[15px]" style={{ color: 'var(--text-muted)' }}>
          Loading the measured series&hellip;
        </p>
      )}
      {children}
    </div>
  )
}
