import { useEffect, useState } from 'react'
import { abs } from '../lib/abs'
import { AREA_LABEL, AREA_TABS, LABEL, SLUG, areaOf, type Tab } from '../routes'

/** THE ONE SHELL EVERY REPORT ON THIS SITE IS BUILT IN.
 *
 *  WHY IT EXISTS. Twenty-odd analysis pages were written one at a time, each inventing its
 *  own header, its own loading sentence, its own error card and its own provenance block.
 *  They said the same things in slightly different words and set them at slightly different
 *  sizes, and a reader takes a difference in PRESENTATION for a difference in CONFIDENCE.
 *  Four readings of one archive must look like four readings of one archive.
 *
 *  WHAT IS SHARED IS THE FRAME, NEVER A FIGURE. Rule 2 governs this file absolutely: no
 *  component here accepts, computes, holds or prints a number of its own. Every figure on
 *  every report arrives from that report's own generated payload. This file is furniture.
 *
 *  THE RHYTHM IS RULE 7b, AND IT IS A COMPONENT RATHER THAN A CONVENTION. A drill-in page
 *  opens with what it MEANS -- conclusions a reader could repeat at a meeting -- then the
 *  organised categorical data that supports them, then the raw table, the method and what
 *  it does not show. `Section` takes that as a named prop, so the order is legible in the
 *  page source and a page that skips a movement is visible in a diff.
 *
 *  THE HYPOTHESIS BOX HAS ITS OWN COLOUR AND ITS OWN LABEL. Rule 7: a figure is a fact and
 *  an explanation for it is not, and the whole of this project's error history is the two
 *  being set in the same voice one paragraph apart.
 *
 *  PRINTING IS A FIRST-CLASS OUTPUT, NOT AN ACCIDENT. Residents and officials take these
 *  to meetings on paper. The shell puts a Print / Save as PDF control on every report and
 *  marks the structure the print stylesheet in index.css needs -- see `.report`,
 *  `.no-print`, `.print-only` and `.avoid-break` there. Nothing renders the PDF for us: the
 *  browser does, from the same DOM a reader sees, which is the only way the paper copy
 *  cannot drift from the page. */

/* ---- the payload shapes the generated reports share ---------------------- */

export type Said = {
  key: string; board: string; date: string; quote: string; why: string
  cite: string; town: string
  // Optional because the generators differ: some name the KIND of meeting document a
  // quote came from and some do not, and a page must print what its own payload holds
  // rather than a blank where a field would be.
  kind?: string
  who?: string
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

/* ---- headings and prose -------------------------------------------------- */

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
    <div className="avoid-break">
      <div className="text-3xl font-bold tracking-tight tnum"
        style={tone ? { color: tone } : undefined}>{value}</div>
      <div className="text-[13px] leading-snug mt-1 max-w-[15rem]"
        style={{ color: 'var(--text-secondary)' }}>{children}</div>
    </div>
  )
}

/* ---- rule 7b, as a component --------------------------------------------- */

/** The three movements of a drill-in, in the order rule 7b fixes them.
 *
 *  `conclusions` is what the page establishes, in sentences. `categorical` is the
 *  breakdown that supports them -- by year, by category, by school -- and is where charts
 *  belong. `raw` is the table, the method, the provenance and what the page does not show.
 *
 *  A page may have several `categorical` sections. It should have exactly one of the other
 *  two, and they are the first and last things on it. */
export function Section({ kind, id, title, children }: {
  kind: 'conclusions' | 'categorical' | 'raw'
  id?: string; title?: React.ReactNode; children: React.ReactNode
}) {
  return (
    <section id={id} data-section={kind}
      className="report-section scroll-mt-[calc(var(--header-h)+1rem)]">
      {title ? <H2>{title}</H2> : null}
      {children}
    </section>
  )
}

/** One conclusion, in the voice rule 7b's first movement requires: a claim a reader
 *  could repeat at a meeting.
 *
 *  TWO MODES, AND THE DIFFERENCE IS WHETHER THE FINDING HAS A HEADLINE FIGURE.
 *
 *    - WITHOUT `figure`, the card is labelled `Finding 1` and leads with the claim. This
 *      is the right shape where the finding is a relation rather than an amount -- "two
 *      sources report different counts and cannot be reconciled" has no number to set.
 *    - WITH `figure`, the amount is set large above the claim, numbered `01`. This is the
 *      right shape where the finding IS an amount, and it is what /what-sports-cost has
 *      always done. The figure is passed in already formatted by the page; rule 2 means
 *      nothing here computes or rounds it.
 *
 *  `tone` colours the figure, or draws a rule across the top of a card that has none,
 *  where the page's findings map onto its own chart hues.
 *
 *  Both modes are here rather than in two components because they are one thing said two
 *  ways, and a reader must not read the difference as a difference in confidence. */
export function Insight({ n, tone, figure, headline, children }: {
  n?: number; tone?: string; figure?: string
  headline: React.ReactNode; children: React.ReactNode
}) {
  return (
    <div className="card p-5 avoid-break"
      style={tone && !figure ? { borderTop: `3px solid ${tone}` } : undefined}>
      {figure !== undefined ? (
        <div className="flex items-baseline gap-3">
          {n === undefined ? null : (
            <span className="text-[11px] font-bold tabular-nums"
              style={{ color: 'var(--text-muted)' }}>{String(n).padStart(2, '0')}</span>
          )}
          <span className="text-2xl font-bold tracking-tight tnum"
            style={tone ? { color: tone } : undefined}>{figure}</span>
        </div>
      ) : n === undefined ? null : (
        <div className="text-[11px] font-semibold uppercase tracking-widest mb-2"
          style={{ color: 'var(--text-muted)' }}>Finding {n}</div>
      )}
      <p className={figure !== undefined
        ? 'text-[15.5px] font-semibold leading-snug mt-2'
        : 'text-[17px] font-bold leading-snug'}>{headline}</p>
      <div className={figure !== undefined
        ? 'text-[13.5px] leading-relaxed mt-2'
        : 'text-[14px] leading-relaxed mt-2.5'}
        style={{ color: 'var(--text-secondary)' }}>{children}</div>
    </div>
  )
}

/** The half of every section that says what the measurement does NOT establish. */
export function NotShown({ children }: { children: React.ReactNode }) {
  return (
    <div className="card p-4 mt-5 max-w-2xl avoid-break"
      style={{ borderLeft: '4px solid var(--axis)' }}>
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
    <div className="card p-4 mt-4 max-w-2xl avoid-break"
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

/** What GRAIN this report is at, said at the top of it. Reports exist separately because
 *  their grains differ, so each one states its own before anything else. */
export function Grain({ children }: { children: React.ReactNode }) {
  return (
    <div className="card p-3.5 mt-6 max-w-2xl avoid-break"
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
    <div className="card p-4 avoid-break">
      <p className="text-[15px] leading-relaxed">&ldquo;{q.quote}&rdquo;</p>
      <p className="text-[12px] mt-2" style={{ color: 'var(--text-muted)' }}>
        {q.board} &middot;{q.kind ? ` ${q.kind.toLowerCase()} \u00b7` : ''} {q.date} &middot;{' '}
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

/** Rule 12, rendered: the address, the publisher's own filename, our copy, the sha256.
 *
 *  Marked `report-provenance` so the print stylesheet can guarantee it survives onto
 *  paper. A printed figure whose source did not print is a figure nobody can check. */
export function Provenance({ sources }: { sources: Source[] }) {
  return (
    <div className="report-provenance grid gap-3 mt-5 sm:grid-cols-2">
      {sources.map(s => (
        <div key={s.path} className="card p-4 avoid-break">
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
      <div className="card p-4 mt-5 max-w-2xl avoid-break"
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

/* ---- moving between reports ---------------------------------------------- */

/** The four special education reports, as links, at the foot of each of them. Named for
 *  what each COUNTS, so a reader crossing from one to another is told the grain changed. */
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
          className="card block p-4 min-h-[44px] transition-opacity hover:opacity-90 avoid-break">
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

/** Every other report in the Analyses area, at the foot of each of them.
 *
 *  Read off `AREA_TABS.analyses` rather than listed here, for the reason rule-of-thumb 1
 *  in CLAUDE.md gives: a hand-kept list of one's own pages is the artefact that goes stale
 *  first and is least likely to be noticed doing it. A report added to the area appears
 *  here the same day. */
export function MoreReports({ here }: { here?: Tab }) {
  const others = AREA_TABS.analyses.filter(t => t !== here && t !== 'reports')
  return (
    <div className="no-print">
      <H2>Every other report</H2>
      <div className="grid gap-2 mt-5 sm:grid-cols-2 lg:grid-cols-3">
        {others.map(t => (
          <a key={t} href={abs(`/${SLUG[t]}`)}
            className="card block p-3 min-h-[44px] text-[13.5px] font-semibold leading-snug
                       transition-opacity hover:opacity-90"
            style={{ color: 'var(--series-cost)' }}>{LABEL[t]} &rarr;</a>
        ))}
      </div>
      <p className="text-[13px] leading-relaxed max-w-2xl mt-4"
        style={{ color: 'var(--text-muted)' }}>
        Every analysis this project has written, in one index, is at{' '}
        <a className="underline" style={{ color: 'var(--series-cost)' }}
          href={abs('/reports')}>reports</a>.
      </p>
    </div>
  )
}

/* ---- loading ------------------------------------------------------------- */

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

/* ---- the shell ----------------------------------------------------------- */

/** Print / Save as PDF.
 *
 *  `window.print()` and nothing else. The browser already renders this page perfectly and
 *  already knows the reader's paper size, their margins and their printer; a server-side
 *  renderer would have to be told all three and would then be producing a SECOND document
 *  that can disagree with the first. The print stylesheet in index.css is what makes the
 *  output worth having.
 *
 *  Hidden from print itself -- a button on paper is a button nobody can press. */
export function PrintButton({ label = 'Print / Save as PDF' }: { label?: string }) {
  return (
    <button type="button" onClick={() => window.print()}
      className="no-print inline-flex items-center gap-1.5 text-xs font-semibold
                 px-2.5 py-1.5 rounded border min-h-[32px] shrink-0
                 transition-opacity hover:opacity-80"
      style={{ borderColor: 'var(--grid)', color: 'var(--text-secondary)',
               background: 'var(--surface-1)' }}>
      <span aria-hidden="true">&#x2399;</span>{label}
    </button>
  )
}

/** The frame every report is drawn in.
 *
 *  `kicker` is the area or family the report belongs to, `title` is the report, and
 *  `standfirst` is ONE line under it -- rule 7a: if the standfirst needs three sentences
 *  the page is doing two jobs. `dataUrl`, where a report has one, is the published payload
 *  the page is computed from, and it is named in the error so a reader who hits a missing
 *  file still gets the rows.
 *
 *  `sourceUrl` is the report's own document where one exists -- the Markdown analyses keep
 *  theirs at /docs/analyses/<id>.md, which is rule 12's third leg. */
export function ReportShell({
  tab, kicker, title, standfirst, err, loading, dataUrl, sourceUrl, meta, children,
}: {
  title: React.ReactNode
  /** The page's own tab. The kicker is derived from the area it belongs to, so it cannot
   *  go stale the way six hand-typed ones had: they still read `The money` after those
   *  reports moved into the Analyses area. Rule 2 applied to a word rather than a figure. */
  tab?: Tab
  kicker?: React.ReactNode
  standfirst?: React.ReactNode
  err?: string | null
  loading?: boolean
  dataUrl?: string
  sourceUrl?: string
  meta?: React.ReactNode
  children?: React.ReactNode
}) {
  const area = tab ? areaOf(tab) : null
  const eyebrow = kicker ?? (area ? AREA_LABEL[area] : null)
  return (
    <article className="report mx-auto max-w-6xl px-5 pt-14 pb-16">
      <header className="report-head">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            {eyebrow && (
              <p className="text-xs font-semibold uppercase tracking-widest mb-3"
                style={{ color: 'var(--text-muted)' }}>{eyebrow}</p>
            )}
            {/* ONE h1 treatment for every report on the site. Some titles are the report's
                NAME and some are the finding itself, in a sentence -- both are the first
                thing on the page and both are set the same, because a reader takes a
                difference in setting for a difference in weight. */}
            <h1 className="text-4xl sm:text-5xl font-bold tracking-tight leading-[1.05]
                           max-w-3xl">{title}</h1>
          </div>
          <PrintButton />
        </div>
        {standfirst && (
          <p className="mt-5 text-lg leading-relaxed max-w-2xl"
            style={{ color: 'var(--text-secondary)' }}>{standfirst}</p>
        )}
        {meta}
        {/* Printed only. On screen the address bar says where this came from; on paper
            nothing does, and a printout with no address is a page nobody can get back to.
            Rule 12 applied to the report itself rather than to its sources. */}
        <p className="print-only report-address">
          lunenburgbudgetproject.org &mdash; written by the Lunenburg Budget Project, an
          independent tool for residents. Not affiliated with the Town of Lunenburg, the
          School Committee or the school district.
          {sourceUrl ? ` The document this page renders: ${sourceUrl}` : ''}
          {dataUrl ? ` The data this page is computed from: ${dataUrl}` : ''}
        </p>
      </header>

      {err && (
        <div className="card p-5 mt-8" style={{ borderLeft: '4px solid var(--status-warning)' }}>
          <p className="text-[15px] font-bold mb-1">This report did not load</p>
          <p className="text-[13.5px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
            {err}. Nothing on this page is typed into it, so with the file missing there is
            nothing to show rather than something stale.
            {dataUrl ? <> The underlying rows are published at{' '}
              <a className="underline" style={{ color: 'var(--series-cost)' }}
                href={abs(dataUrl)}>{dataUrl}</a>.</> : null}
          </p>
        </div>
      )}
      {loading && !err && (
        <p className="mt-6 text-[15px]" style={{ color: 'var(--text-muted)' }}>
          Loading the measured series&hellip;
        </p>
      )}
      {children}
    </article>
  )
}

/** The name the shell went by while it was only the four special education reports.
 *  Kept as an alias so those pages read the same as every other report page. */
export const Shell = ReportShell
