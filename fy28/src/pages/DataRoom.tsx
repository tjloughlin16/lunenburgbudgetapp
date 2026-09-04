import { Fragment, useEffect, useMemo, useRef, useState } from 'react'
import { Section, Note, Stat } from '../components/primitives'

/** The data room — what we hold, line by line and year by year.
 *
 *  UNLISTED, not private. It is in no nav, no sitemap and no index, and it is not
 *  prerendered, so nothing links to it and nothing crawls to it. But anyone with the URL
 *  can read it, and if the link is ever posted anywhere it will be indexed like any other
 *  page. Treat it as a page you hand to someone, not as a page behind a lock.
 *
 *  The name is the standard one: a data room is the underlying-document repository you
 *  open to somebody doing diligence, as distinct from the argument built on top of it.
 *  Every other page on this site is the argument. This one is the room.
 *
 *  Three questions, in the order somebody checking our work would ask them:
 *
 *    1. What do you actually have? -- the coverage matrix, derived from the database
 *       rather than from a list somebody maintains, so an empty cell is a real gap.
 *    2. How has each line moved? -- budget year over year, and actual against budget.
 *    3. Does it add up? -- year totals, and the surplus that falls out of them.
 *
 *  Loaded at runtime from /data/ledger.json rather than bundled: half a megabyte of
 *  ledger has no business in the bundle every other page pays for.
 */

type DocRef = {
  citedAs: string; path: string; basis: string | null; url: string | null
  sha256: string | null; hiddenColumns: string | null
}
type UnreadDoc = {
  document: string; dataRows: number; reason: string
  covers: string; statesInItsHeader: string
}
type Cell = {
  state: 'obtained' | 'partial' | 'missing' | 'unread'
  n?: number; note?: string; documents: DocRef[]; unresolvedDocuments?: string[]
  /** Documents we HOLD whose figures have never been extracted. A cell with these is
   *  not a gap in the archive; it is a gap in our reading of it, and the two must never
   *  be shown as the same thing — one is a request to the town, the other is our job. */
  heldNotRead?: UnreadDoc[]
}
type RowDef = {
  id: string; group: string; label: string; why: string
  publisher: string; howToGet: string; effort: 'public' | 'records request'
}
type YearRow = {
  fy: number; budget?: number; stage?: string; actual?: number
  variance?: number; sameDoc?: boolean; disagree?: boolean
}
type Line = {
  key: string; label: string; section: string | null; group: string | null
  years: YearRow[]; sources: string[]; row?: number
  workbook?: Record<string, Record<string, number>>
}
type Stated = {
  amount: number; statedOn: string; statedBy: string; quote: string
  docId: string; sourceRef: string | null; supersedes: number | null; note: string | null
}
type Total = {
  fy: number; budget: number | null; actual: number | null
  actualToDate?: number | null; encumberedToDate?: number | null
  halves: string; whatThisIs: string
  canComputeSurplus: boolean; blockedBy: string[]
  restatementVariance?: number; restatementVariancePct?: number
  committed?: number; uncommitted?: number
  stated?: Stated[]; townFigure?: number; gapToTownFigure?: number
}
type Dept = {
  dept: string; name: string; fy: number; period: number; original: number
  transfers: number; revised: number; expended: number; encumbered: number
  available: number; pct_used: number; doc_id: string
}
type GrossRow = {
  org: string; object: string; label: string; accountId: string
  net: {
    state: string; appropriated: number; transfers: number; revised: number
    spent: number; encumbered: number; unspent: number; docId: string
  }
  offsets: { state: string; items: unknown[]; blockedBy: string }
  gross: { state: string; note: string }
}
type GrossBudget = {
  fy: number; period: number; asOf: string
  rows: GrossRow[]
  unattributed: { fund: string; name: string | null; kind: string | null
                  restriction: string | null; spent: number; doc_id: string }[]
  grants: { name: string; amount: number; kind: string | null; owner: string | null }[]
  totals: Record<string, number | string>
  legend: { state: string; means: string }[]
}
type Ledger = {
  coverage: { years: number[]; rowDefs: RowDef[]; cells: Record<string, Record<string, Cell>> }
  lines: Line[]
  totals: Total[]
  departments: Dept[]
  grossBudget: GrossBudget
  funding: {
    revenue: { object: string; name: string; budgeted: number; received: number; pct_received: number }[]
    interfund: { fund: string; object: string; name: string; budgeted: number; received: number }[]
    funds: { fund: string; name: string; kind: string | null; restriction: string | null; fy: number; revenue: number; spent: number; closing_balance: number }[]
  }
  meta: {
    commit: string | null
    counts: Record<string, number>
    crosswalkNote: string
    lineSourceOverlap: { total: number; both: number; documentsOnly: number; workbookOnly: number }
  }
}

const usd = (n: number | null | undefined, dp = 0) =>
  n === null || n === undefined ? '—'
    : (n < 0 ? '-$' : '$') + Math.abs(n).toLocaleString('en-US',
      { minimumFractionDigits: dp, maximumFractionDigits: dp })
const usdK = (n: number | null | undefined) =>
  n === null || n === undefined ? '—'
    : Math.abs(n) >= 1e6 ? `${n < 0 ? '-' : ''}$${(Math.abs(n) / 1e6).toFixed(2)}M`
      : `${n < 0 ? '-' : ''}$${Math.round(Math.abs(n) / 1000)}k`
const pct = (n: number | null | undefined, dp = 1) =>
  n === null || n === undefined ? '—' : `${n > 0 ? '+' : ''}${n.toFixed(dp)}%`

/** Status is never carried by colour alone: every cell pairs a glyph with a word. */
const STATE = {
  obtained: { glyph: '■', word: 'Obtained', color: 'var(--status-good)' },
  partial: { glyph: '▤', word: 'Partial', color: 'var(--status-warning)' },
  missing: { glyph: '□', word: 'Not held', color: 'var(--text-muted)' },
  // Held, and not read. Kept visually distinct from 'Not held' because the action is the
  // opposite: nothing to ask anybody for, the document is already on the shelf.
  unread: { glyph: '▨', word: 'Held, not read', color: 'var(--status-warning)' },
} as const

export function DataRoom() {
  const [data, setData] = useState<Ledger | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let live = true
    fetch('/data/ledger.json')
      .then(r => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then(d => { if (live) setData(d) })
      .catch(e => { if (live) setError(String(e)) })
    return () => { live = false }
  }, [])

  if (error) {
    return (
      <div className="mx-auto max-w-6xl px-5 py-20">
        <h1 className="text-2xl font-bold mb-3">The data room could not load</h1>
        <p style={{ color: 'var(--text-secondary)' }}>
          <code>/data/ledger.json</code> did not answer: {error}. Rebuild it with{' '}
          <code>python3 scripts/build_db.py &amp;&amp; python3 scripts/export_ledger.py</code>.
        </p>
      </div>
    )
  }
  if (!data) {
    return (
      <div className="mx-auto max-w-6xl px-5 py-20">
        <p style={{ color: 'var(--text-muted)' }}>Loading the ledger…</p>
      </div>
    )
  }

  return (
    <>
      <header className="mx-auto max-w-6xl px-5 pt-12 pb-2">
        <p className="text-xs font-semibold uppercase tracking-widest mb-2"
          style={{ color: 'var(--status-warning)' }}>Unlisted working page</p>
        <h1 className="text-3xl sm:text-4xl font-bold tracking-tight mb-4">
          The data room
        </h1>
        <div className="max-w-3xl text-[15px] leading-relaxed space-y-3"
          style={{ color: 'var(--text-secondary)' }}>
          <p>
            Everything this project holds about the school budget, as data rather than as
            argument: what we have for each year, how every line has moved, and whether
            the years add up. Nothing here is a conclusion. It is the material a
            conclusion would have to be built from.
          </p>
          <p>
            <strong style={{ color: 'var(--text-primary)' }}>This page is unlisted, not
            private.</strong> It appears in no navigation, no index and no sitemap, and
            nothing on the site links to it. Anyone holding the address can read it.
          </p>
        </div>
      </header>

      <Coverage cov={data.coverage} />
      <Totals totals={data.totals} />
      <Lines lines={data.lines} meta={data.meta} />
      <Gross g={data.grossBudget} />
      <Departments rows={data.departments} />
      <Funding funding={data.funding} />
      <Provenance meta={data.meta} />
    </>
  )
}

/* ---------------------------------------------------------------- coverage matrix */

/** The coverage matrix, and the thing that makes it useful: every cell opens.
 *
 *  A grid of coloured squares tells a reader we have gaps. It does not tell them where a
 *  figure came from, or what to do about a gap, and the honest complaint is that the
 *  sources blur together -- some are the district's, some the town's, some the state's,
 *  and the grid flattens that distinction away.
 *
 *  So three things open:
 *    a cell     -> the documents behind it, with address and sha256, OR what to obtain
 *    a year     -> everything that year still needs, grouped by who to ask
 *    a row      -> what that document is, who publishes it, and how it is obtained
 */
function Coverage({ cov }: { cov: Ledger['coverage'] }) {
  const [open, setOpen] = useState<{ fy: number | null; row: string | null } | null>(null)

  const groups = useMemo(() => {
    const g: { name: string; rows: RowDef[] }[] = []
    for (const r of cov.rowDefs) {
      const last = g[g.length - 1]
      if (last && last.name === r.group) last.rows.push(r)
      else g.push({ name: r.group, rows: [r] })
    }
    return g
  }, [cov.rowDefs])

  const tally = useMemo(() => {
    let obtained = 0, partial = 0, unread = 0, missing = 0
    for (const fy of cov.years) for (const rd of cov.rowDefs) {
      const st = cov.cells[String(fy)]?.[rd.id]?.state
      if (st === 'obtained') obtained++
      else if (st === 'partial') partial++
      else if (st === 'unread') unread++
      else missing++
    }
    return { obtained, partial, unread, missing,
      total: cov.years.length * cov.rowDefs.length }
  }, [cov])

  const at = (fy: number, id: string): Cell =>
    cov.cells[String(fy)]?.[id] ?? { state: 'missing', documents: [] }
  const def = (id: string) => cov.rowDefs.find(r => r.id === id)!

  return (
    <Section id="coverage" eyebrow="1 — What we actually hold"
      title="Completeness, by fiscal year"
      lede={<>
        <p className="mb-3">
          The same {cov.rowDefs.length} rows for every year, computed from the database
          rather than read off a list somebody maintains — so a document that arrives
          shows up here without anybody ticking a box, and one that is missing cannot be
          quietly marked present.
        </p>
        <p>
          <strong style={{ color: 'var(--text-primary)' }}>Everything here opens.</strong>{' '}
          Click a square to see the documents behind it, or what to obtain if it is empty.
          Click a year to get everything that year still needs, grouped by who to ask.
          Click a row label for what that document is and who publishes it.
        </p>
      </>}>

      <div className="flex flex-wrap gap-4 mb-5 text-xs">
        {(Object.keys(STATE) as (keyof typeof STATE)[]).map(k => (
          <span key={k} className="inline-flex items-center gap-1.5" style={{ color: STATE[k].color }}>
            <span aria-hidden="true" className="text-base leading-none">{STATE[k].glyph}</span>
            {STATE[k].word}
          </span>
        ))}
        <span style={{ color: 'var(--text-muted)' }}>
          {tally.obtained} obtained · {tally.partial} partial · {tally.unread} held but
          not read · {tally.missing} not held, of {tally.total}
        </span>
      </div>

      <div className="overflow-x-auto -mx-5 px-5">
        <table className="w-full text-[13px] border-collapse min-w-[900px]">
          <thead>
            <tr>
              <th className="text-left font-semibold pb-2 pr-3 sticky left-0 z-10"
                style={{ background: 'var(--surface-1)' }}>Document</th>
              {cov.years.map(y => (
                <th key={y} className="pb-2 px-1 font-semibold">
                  <button onClick={() => setOpen(
                    open?.fy === y && !open?.row ? null : { fy: y, row: null })}
                    aria-expanded={open?.fy === y && !open?.row}
                    className="tnum whitespace-nowrap px-1 py-0.5 rounded"
                    style={{
                      color: open?.fy === y ? 'var(--text-primary)' : 'var(--text-secondary)',
                      background: open?.fy === y && !open?.row ? 'var(--surface-3)' : 'transparent',
                    }}
                    title={`Everything FY${y} still needs`}>
                    FY{String(y).slice(2)}
                  </button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {groups.map(g => (
              <Fragment key={g.name}>
                <tr>
                  <td colSpan={cov.years.length + 1}
                    className="pt-4 pb-1 text-[11px] font-semibold uppercase tracking-widest"
                    style={{ color: 'var(--text-muted)' }}>{g.name}</td>
                </tr>
                {g.rows.map(rd => (
                  <tr key={rd.id} className="border-t" style={{ borderColor: 'var(--grid)' }}>
                    <td className="py-2 pr-3 align-top sticky left-0 z-10"
                      style={{ background: 'var(--surface-1)' }}>
                      <button onClick={() => setOpen(
                        open?.row === rd.id && !open?.fy ? null : { fy: null, row: rd.id })}
                        aria-expanded={open?.row === rd.id && !open?.fy}
                        className="text-left">
                        <span className="font-medium underline decoration-dotted underline-offset-2">
                          {rd.label}
                        </span>
                        <span className="block text-[11px] leading-snug max-w-[22rem]"
                          style={{ color: 'var(--text-muted)' }}>{rd.why}</span>
                      </button>
                    </td>
                    {cov.years.map(y => {
                      const c = at(y, rd.id)
                      const st = STATE[c.state]
                      const on = open?.fy === y && open?.row === rd.id
                      return (
                        <td key={y} className="text-center py-1 px-1">
                          <button
                            onClick={() => setOpen(on ? null : { fy: y, row: rd.id })}
                            aria-expanded={on}
                            aria-label={`FY${y}, ${rd.label}: ${st.word}`}
                            className="w-7 h-7 rounded leading-none text-lg"
                            style={{ color: st.color,
                                     background: on ? 'var(--surface-3)' : 'transparent',
                                     outline: on ? '1px solid var(--grid)' : 'none' }}>
                            {st.glyph}
                          </button>
                        </td>
                      )
                    })}
                  </tr>
                ))}
              </Fragment>
            ))}
          </tbody>
        </table>
      </div>

      {open && (
        <Modal onClose={() => setOpen(null)}>
          {open.fy !== null && open.row !== null && (
            <CellDetail fy={open.fy} rd={def(open.row)} cell={at(open.fy, open.row)}
              onClose={() => setOpen(null)} />
          )}
          {open.fy !== null && open.row === null && (
            <YearReport fy={open.fy} cov={cov} onClose={() => setOpen(null)}
              onPick={(row) => setOpen({ fy: open.fy, row })} />
          )}
          {open.fy === null && open.row !== null && (
            <RowDetail rd={def(open.row)} cov={cov} onClose={() => setOpen(null)}
              onPick={(fy) => setOpen({ fy, row: open.row })} />
          )}
        </Modal>
      )}
    </Section>
  )
}

/** A real dialog, because the answer has to arrive where the click happened.
 *
 *  These panels used to render below a 19-column table, which meant clicking a square
 *  scrolled the answer somewhere the reader could not see and gave no sign anything had
 *  happened. A grid that wide has no usable "below".
 *
 *  Escape closes, the backdrop closes, focus moves in on open and back to whatever was
 *  focused before on close, and the page behind does not scroll while it is up.
 */
function Modal({ onClose, children }: { onClose: () => void; children: React.ReactNode }) {
  const ref = useRef<HTMLDivElement>(null)
  const returnTo = useRef<HTMLElement | null>(null)

  useEffect(() => {
    returnTo.current = document.activeElement as HTMLElement | null
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', onKey)
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    ref.current?.focus()
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = prev
      returnTo.current?.focus?.()
    }
  }, [onClose])

  return (
    <div role="dialog" aria-modal="true"
      className="fixed inset-0 z-50 flex items-start sm:items-center justify-center p-3 sm:p-6"
      style={{ background: 'rgba(0,0,0,0.55)' }}
      onClick={e => { if (e.target === e.currentTarget) onClose() }}>
      <div ref={ref} tabIndex={-1}
        className="w-full max-w-2xl max-h-[85vh] overflow-y-auto rounded-lg shadow-2xl outline-none"
        style={{ background: 'var(--surface-1)', border: '1px solid var(--grid)' }}>
        {children}
      </div>
    </div>
  )
}

function Panel({ eyebrow, title, onClose, children }: {
  eyebrow: string; title: string; onClose: () => void; children: React.ReactNode
}) {
  return (
    <div className="p-4 sm:p-5">
      <div className="flex items-start justify-between gap-4 mb-3">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-widest mb-0.5"
            style={{ color: 'var(--text-muted)' }}>{eyebrow}</p>
          <h3 className="text-lg font-bold leading-tight">{title}</h3>
        </div>
        <button onClick={onClose} className="text-sm px-2 py-1 rounded shrink-0"
          style={{ color: 'var(--text-muted)' }} aria-label="Close">✕</button>
      </div>
      {children}
    </div>
  )
}

function EffortTag({ effort }: { effort: RowDef['effort'] }) {
  const pub = effort === 'public'
  return (
    <span className="inline-flex items-center gap-1 text-[11px] font-semibold px-1.5 py-0.5 rounded"
      style={{ color: pub ? 'var(--status-good)' : 'var(--status-warning)',
               background: 'var(--surface-2)' }}>
      {pub ? '↓ public download' : '✉ records request'}
    </span>
  )
}

/** One cell. Either the files it rests on, or what to obtain. */
function CellDetail({ fy, rd, cell, onClose }: {
  fy: number; rd: RowDef; cell: Cell; onClose: () => void
}) {
  const st = STATE[cell.state]
  return (
    <Panel eyebrow={`FY${fy} · ${st.word}`} title={rd.label} onClose={onClose}>
      {cell.note && (
        <p className="text-sm mb-3 leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
          {cell.note}
        </p>
      )}

      {cell.documents.length > 0 ? (
        <>
          <p className="text-[11px] font-semibold uppercase tracking-widest mb-2"
            style={{ color: 'var(--text-muted)' }}>
            {cell.documents.length === 1 ? 'The document behind this'
              : `The ${cell.documents.length} documents behind this`}
            {cell.n ? ` · ${cell.n.toLocaleString()} figures` : ''}
          </p>
          <ul className="space-y-2 mb-3">
            {cell.documents.map(d => <DocLine key={d.citedAs} d={d} />)}
          </ul>
        </>
      ) : (
        <p className="text-sm mb-3" style={{ color: 'var(--text-secondary)' }}>
          Nothing in the archive supplies this for FY{fy}.
        </p>
      )}

      {cell.heldNotRead && cell.heldNotRead.length > 0 && (
        <div className="mb-3">
          <p className="text-[11px] font-semibold uppercase tracking-widest mb-2"
            style={{ color: 'var(--text-muted)' }}>
            {cell.heldNotRead.length} document(s) held, never read
          </p>
          <ul className="space-y-2">
            {cell.heldNotRead.map(u => (
              <li key={u.document} className="text-[12px] leading-relaxed">
                <span className="font-mono">{u.document}</span>
                <span style={{ color: 'var(--text-muted)' }}> · {u.dataRows} rows</span>
                <span className="block" style={{ color: 'var(--text-secondary)' }}>
                  {u.reason}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {cell.unresolvedDocuments && (
        <p className="text-xs mb-3" style={{ color: 'var(--status-critical)' }}>
          {cell.unresolvedDocuments.length} cited document(s) could not be resolved to an
          address: {cell.unresolvedDocuments.join(', ')}. Figures resting on them are
          uncheckable.
        </p>
      )}

      {cell.state === 'unread' ? (
        <div className="pt-3 border-t" style={{ borderColor: 'var(--grid)' }}>
          <p className="text-[11px] font-semibold uppercase tracking-widest mb-1.5"
            style={{ color: 'var(--text-muted)' }}>
            What would make this green
          </p>
          <p className="text-sm leading-relaxed">
            Nothing from anybody. The documents above are in the archive and their figures
            have never been extracted — the gap is ours, not the town’s.
          </p>
        </div>
      ) : cell.state !== 'obtained' && (
        <div className="pt-3 border-t" style={{ borderColor: 'var(--grid)' }}>
          <p className="text-[11px] font-semibold uppercase tracking-widest mb-1.5"
            style={{ color: 'var(--text-muted)' }}>
            What would make this green
          </p>
          <p className="text-sm leading-relaxed mb-2">{rd.howToGet}</p>
          <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>
            Published by <strong>{rd.publisher}</strong> <EffortTag effort={rd.effort} />
          </p>
        </div>
      )}
    </Panel>
  )
}

function DocLine({ d }: { d: DocRef }) {
  return (
    <li className="text-[13px]">
      <span className="font-mono text-[12px] break-all">{d.path}</span>
      <span className="block text-[11px] mt-0.5" style={{ color: 'var(--text-muted)' }}>
        {d.basis && <>basis: {d.basis} · </>}
        {d.sha256 ? <>sha256 {d.sha256.slice(0, 16)}…</> : 'no checksum recorded'}
        {d.url && <> · <a href={d.url} target="_blank" rel="noreferrer"
          className="underline" style={{ color: 'var(--series-cost)' }}>publisher’s copy</a></>}
      </span>
      {d.hiddenColumns && (
        <span className="block text-[11px]" style={{ color: 'var(--status-warning)' }}>
          hides columns a reader does not see: {d.hiddenColumns}
        </span>
      )}
    </li>
  )
}

/** One year: everything still needed, grouped by who to ask. */
function YearReport({ fy, cov, onClose, onPick }: {
  fy: number; cov: Ledger['coverage']; onClose: () => void; onPick: (row: string) => void
}) {
  const cells = cov.cells[String(fy)] ?? {}
  const rows = cov.rowDefs.map(rd => ({
    rd, cell: (cells[rd.id] ?? { state: 'missing', documents: [] }) as Cell,
  }))
  const have = rows.filter(r => r.cell.state === 'obtained')
  // `unread` is deliberately NOT a gap. This list is grouped into "Ask <publisher>", and
  // a row that is unread would put a document already sitting in the archive into a
  // records request — which is how a request for ten held documents nearly went to the
  // Superintendent. Held-but-unread gets its own block below, addressed to us.
  const unread = rows.filter(r => r.cell.state === 'unread')
  const gaps = rows.filter(r => r.cell.state !== 'obtained' && r.cell.state !== 'unread')
  const byPublisher = new Map<string, typeof gaps>()
  for (const g of gaps) {
    const k = `${g.rd.publisher}|${g.rd.effort}`
    byPublisher.set(k, [...(byPublisher.get(k) ?? []), g])
  }

  return (
    <Panel eyebrow={`FY${fy}`} onClose={onClose}
      title={gaps.length === 0 ? `FY${fy} is complete`
        : `FY${fy} needs ${gaps.length} more document${gaps.length === 1 ? '' : 's'}`}>
      {unread.length > 0 && (
        <div className="mb-5">
          <p className="text-sm font-semibold mb-2">
            Ask nobody — {unread.length} row{unread.length === 1 ? '' : 's'} held, not read
          </p>
          <ul className="space-y-2.5">
            {unread.map(({ rd, cell }) => (
              <li key={rd.id} className="text-[13px]">
                <button onClick={() => onPick(rd.id)} className="text-left">
                  <span className="font-medium underline decoration-dotted underline-offset-2">
                    {rd.label}
                  </span>
                  <span className="ml-1.5" style={{ color: STATE[cell.state].color }}>
                    {STATE[cell.state].glyph} {STATE[cell.state].word}
                  </span>
                </button>
                <span className="block text-[12px] leading-relaxed mt-0.5"
                  style={{ color: 'var(--text-secondary)' }}>
                  {cell.heldNotRead?.length ?? 0} document(s) for FY{fy} are in the
                  archive with their figures never extracted. Nothing to request.
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
      {[...byPublisher.entries()].map(([k, items]) => {
        const [publisher, effort] = k.split('|')
        return (
          <div key={k} className="mb-5">
            <p className="text-sm font-semibold mb-2">
              Ask {publisher} <EffortTag effort={effort as RowDef['effort']} />
            </p>
            <ul className="space-y-2.5">
              {items.map(({ rd, cell }) => (
                <li key={rd.id} className="text-[13px]">
                  <button onClick={() => onPick(rd.id)} className="text-left">
                    <span className="font-medium underline decoration-dotted underline-offset-2">
                      {rd.label}
                    </span>
                    <span className="ml-1.5" style={{ color: STATE[cell.state].color }}>
                      {STATE[cell.state].glyph} {STATE[cell.state].word}
                    </span>
                  </button>
                  <span className="block text-[12px] leading-relaxed mt-0.5"
                    style={{ color: 'var(--text-secondary)' }}>{rd.howToGet}</span>
                </li>
              ))}
            </ul>
          </div>
        )
      })}

      {have.length > 0 && (
        <div className="pt-3 border-t" style={{ borderColor: 'var(--grid)' }}>
          <p className="text-[11px] font-semibold uppercase tracking-widest mb-2"
            style={{ color: 'var(--text-muted)' }}>
            Already held for FY{fy} — {have.length} of {rows.length}
          </p>
          <ul className="space-y-1">
            {have.map(({ rd, cell }) => (
              <li key={rd.id} className="text-[13px]">
                <button onClick={() => onPick(rd.id)}
                  className="underline decoration-dotted underline-offset-2 text-left">
                  {rd.label}
                </button>
                <span style={{ color: 'var(--text-muted)' }}>
                  {' '}— {cell.documents.length} document
                  {cell.documents.length === 1 ? '' : 's'}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </Panel>
  )
}

/** One row: what this document is, who publishes it, and which years we hold. */
function RowDetail({ rd, cov, onClose, onPick }: {
  rd: RowDef; cov: Ledger['coverage']; onClose: () => void; onPick: (fy: number) => void
}) {
  const held = cov.years.filter(y => cov.cells[String(y)]?.[rd.id]?.state === 'obtained')
  const partial = cov.years.filter(y => cov.cells[String(y)]?.[rd.id]?.state === 'partial')
  return (
    <Panel eyebrow={rd.group} title={rd.label} onClose={onClose}>
      <p className="text-sm mb-3 leading-relaxed">{rd.why}</p>
      <p className="text-[11px] font-semibold uppercase tracking-widest mb-1.5"
        style={{ color: 'var(--text-muted)' }}>How it is obtained</p>
      <p className="text-sm leading-relaxed mb-2">{rd.howToGet}</p>
      <p className="text-xs mb-4" style={{ color: 'var(--text-secondary)' }}>
        Published by <strong>{rd.publisher}</strong> <EffortTag effort={rd.effort} />
      </p>
      <p className="text-[13px]">
        <strong>Held for {held.length} of {cov.years.length} years.</strong>{' '}
        {held.length > 0 && (
          <span>
            {held.map((y, i) => (
              <Fragment key={y}>
                {i > 0 && ', '}
                <button onClick={() => onPick(y)} className="underline decoration-dotted"
                  style={{ color: 'var(--series-cost)' }}>FY{y}</button>
              </Fragment>
            ))}
            .
          </span>
        )}
        {partial.length > 0 && (
          <span style={{ color: 'var(--status-warning)' }}>
            {' '}Partial in {partial.map(y => `FY${y}`).join(', ')}.
          </span>
        )}
      </p>
    </Panel>
  )
}

/* ------------------------------------------------------------------- year totals */

/** Not "here is the surplus". Here is what we can and cannot say about each year.
 *
 *  This section used to be a table with a column headed "Under budget", a number in it
 *  for FY25 and a dash everywhere else. That said two wrong things at once: that the
 *  number was the surplus, and that a dash meant no variance rather than no data.
 *
 *  It is neither. The town arrives at a surplus by CLOSING THE BOOKS -- revised
 *  appropriation, less expended, less encumbrances still open after purchase orders are
 *  closed in the lapse period. We hold no year-end ledger for any year, so we cannot do
 *  that arithmetic for any year. What we can do is subtract two columns of a document the
 *  district wrote about itself, which is a different quantity that happens to look like
 *  the same one. */
function Totals({ totals }: { totals: Total[] }) {
  const [openFy, setOpenFy] = useState<number | null>(null)
  const anyComputable = totals.some(t => t.canComputeSurplus)
  const blockers = [...new Set(totals.flatMap(t => t.blockedBy))]

  return (
    <Section id="totals" eyebrow="2 — Does it add up"
      title="What we can and cannot say about each year"
      lede={<>
        <p className="mb-3">
          A surplus is what a closed set of books says was left: the revised appropriation,
          less what was spent, less encumbrances still open once purchase orders are closed
          after year end. That last step is real money — it moved FY25 by $21,770.53
          between two School Committee meetings a fortnight apart.
        </p>
        <p>
          <strong style={{ color: 'var(--text-primary)' }}>We cannot do that arithmetic for
          any year, because we hold no year-end ledger for any year.</strong> What follows
          is the nearest thing the documents allow, clearly labelled as the different
          quantity it is.
        </p>
      </>}>

      {!anyComputable && (
        <div className="card p-4 mb-6 max-w-3xl"
          style={{ borderLeft: '3px solid var(--status-critical)' }}>
          <p className="text-[11px] font-semibold uppercase tracking-widest mb-1.5"
            style={{ color: 'var(--status-critical)' }}>
            Not computable from what we hold — 0 of {totals.length} years
          </p>
          <p className="text-sm leading-relaxed mb-2" style={{ color: 'var(--text-secondary)' }}>
            Two documents are missing for every single year, and both are ordinary reports
            the Finance Department already produces:
          </p>
          <ul className="text-sm space-y-1" style={{ color: 'var(--text-secondary)' }}>
            {blockers.map(b => (
              <li key={b} className="flex gap-2">
                <span aria-hidden="true" style={{ color: 'var(--text-muted)' }}>□</span>
                <span>{b}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="overflow-x-auto -mx-5 px-5">
        <table className="w-full text-sm border-collapse min-w-[760px]">
          <thead>
            <tr className="text-left" style={{ color: 'var(--text-secondary)' }}>
              <th className="pb-2 font-semibold">Year</th>
              <th className="pb-2 font-semibold text-right">Budget column</th>
              <th className="pb-2 font-semibold text-right">Actual column</th>
              <th className="pb-2 font-semibold text-right">Difference</th>
              <th className="pb-2 font-semibold pl-4">What that difference is</th>
            </tr>
          </thead>
          <tbody>
            {totals.map(t => (
              <Fragment key={t.fy}>
                <tr className="border-t align-top" style={{ borderColor: 'var(--grid)' }}>
                  <td className="py-3 font-semibold tnum">FY{t.fy}</td>
                  <td className="py-3 text-right tnum">
                    {t.budget === null ? <NotHeld /> : usd(t.budget)}
                  </td>
                  <td className="py-3 text-right tnum">
                    {t.actual !== null && t.actual !== undefined ? usd(t.actual)
                      : t.actualToDate
                        ? <span>{usd(t.actualToDate)}<span className="block text-[11px]"
                            style={{ color: 'var(--status-warning)' }}>to date only</span></span>
                        : <NotHeld />}
                  </td>
                  <td className="py-3 text-right tnum font-semibold">
                    {t.restatementVariance !== undefined
                      ? usd(t.restatementVariance)
                      : <span className="font-normal text-xs"
                          style={{ color: 'var(--text-muted)' }}>cannot subtract</span>}
                    {t.restatementVariancePct !== undefined && (
                      <span className="block text-[11px] font-normal"
                        style={{ color: 'var(--text-secondary)' }}>
                        {t.restatementVariancePct.toFixed(2)}% of budget
                      </span>
                    )}
                  </td>
                  <td className="py-3 pl-4 text-xs leading-relaxed max-w-[26rem]"
                    style={{ color: 'var(--text-muted)' }}>
                    {t.whatThisIs}
                    {t.committed !== undefined && (
                      <span className="block mt-1">
                        {usdK(t.committed)} committed, {usdK(t.uncommitted)} uncommitted at
                        that point.
                      </span>
                    )}
                    {t.stated && (
                      <button onClick={() => setOpenFy(openFy === t.fy ? null : t.fy)}
                        aria-expanded={openFy === t.fy}
                        className="block mt-1.5 font-semibold text-[12px]"
                        style={{ color: 'var(--series-cost)' }}>
                        {openFy === t.fy ? 'Hide' : 'The town states'} {usd(t.townFigure)}{' '}
                        for this year {openFy === t.fy ? '▲' : '▼'}
                      </button>
                    )}
                  </td>
                </tr>
                {openFy === t.fy && t.stated && (
                  <tr style={{ background: 'var(--surface-2)' }}>
                    <td colSpan={5} className="px-4 py-4">
                      <StatedFigures t={t} />
                    </td>
                  </tr>
                )}
              </Fragment>
            ))}
          </tbody>
        </table>
      </div>

      <Note>
        &ldquo;Cannot subtract&rdquo; means a half is missing, not that the two halves
        matched. Which half, and for which year, is the coverage matrix above.
      </Note>
    </Section>
  )
}

/** A missing half, said out loud. A dash reads as zero and this must not. */
function NotHeld() {
  return (
    <span className="inline-flex items-center gap-1 text-xs font-normal"
      style={{ color: 'var(--text-muted)' }}>
      <span aria-hidden="true">□</span> not held
    </span>
  )
}

/** What the town said, when, and how far it is from our arithmetic.
 *
 *  The gap is shown and NOT explained, because nothing we hold explains it. Two
 *  mechanisms could: transfers into the department during the year, which raise the base
 *  our subtraction never sees, and encumbrances still open, which lower the surplus. They
 *  pull in opposite directions and neither is measured for FY25. */
function StatedFigures({ t }: { t: Total }) {
  return (
    <div className="max-w-3xl">
      <p className="text-[11px] font-semibold uppercase tracking-widest mb-2"
        style={{ color: 'var(--text-muted)' }}>
        Quoted from the town, not computed here
      </p>
      <ol className="space-y-3 mb-4">
        {t.stated!.map(s => (
          <li key={s.amount} className="text-sm">
            <span className="tnum font-bold">{usd(s.amount, 2)}</span>
            <span style={{ color: 'var(--text-muted)' }}> — {s.statedOn}, {s.statedBy}</span>
            <blockquote className="mt-1 pl-3 text-[13px] italic border-l"
              style={{ borderColor: 'var(--grid)', color: 'var(--text-secondary)' }}>
              &ldquo;{s.quote}&rdquo;
              <span className="not-italic block text-[11px] mt-0.5"
                style={{ color: 'var(--text-muted)' }}>
                {s.docId}{s.sourceRef ? `, ${s.sourceRef}` : ''}
              </span>
            </blockquote>
            {s.note && (
              <p className="text-[12px] mt-1" style={{ color: 'var(--text-muted)' }}>{s.note}</p>
            )}
          </li>
        ))}
      </ol>

      {t.gapToTownFigure !== undefined && (
        <div className="card p-3">
          <p className="text-sm leading-relaxed">
            Our subtraction is <strong className="tnum">{usd(t.restatementVariance)}</strong>.
            The town&rsquo;s closing figure is <strong className="tnum">{usd(t.townFigure, 2)}</strong>.
            They differ by <strong className="tnum"
              style={{ color: 'var(--status-warning)' }}>{usd(t.gapToTownFigure, 2)}</strong>.
          </p>
          <p className="text-xs mt-2 leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
            <strong style={{ color: 'var(--text-primary)' }}>That gap is not explained
            here.</strong> They are different quantities measured different ways, so they
            were never going to agree, and neither is wrong. Two mechanisms sit between
            them and both are unmeasured for this year: transfers into the department
            during the year, which raise a base our subtraction never sees, and
            encumbrances still open at the close, which lower a surplus. They pull in
            opposite directions. The town&rsquo;s figure is the one to quote — it is
            theirs, it comes from closing the books, and it is what the people who voted
            the budget were told.
          </p>
        </div>
      )}
    </div>
  )
}

/* ----------------------------------------------------------------- line explorer */

function Lines({ lines, meta }: { lines: Line[]; meta: Ledger['meta'] }) {
  const [q, setQ] = useState('')
  const [sel, setSel] = useState<string | null>(null)
  const [onlyBoth, setOnlyBoth] = useState(false)

  const filtered = useMemo(() => {
    const needle = q.trim().toLowerCase()
    return lines.filter(l => {
      if (onlyBoth && l.sources.length < 2) return false
      if (!needle) return true
      return l.label.toLowerCase().includes(needle)
        || (l.group ?? '').toLowerCase().includes(needle)
    })
  }, [lines, q, onlyBoth])

  const selected = sel ? lines.find(l => l.key === sel) ?? null : null

  return (
    <Section id="lines" eyebrow="3 — How each line moves"
      title="Every line, every year"
      lede={<>
        <p className="mb-3">
          {meta.lineSourceOverlap.total.toLocaleString()} distinct budget lines. For each,
          how the budget for it changed year over year, and — where the same document
          printed both halves — how the actual compared.
        </p>
        <p>
          <strong style={{ color: 'var(--text-primary)' }}>Two sources name lines
          differently, and only {meta.lineSourceOverlap.both} names appear in both.</strong>{' '}
          {meta.lineSourceOverlap.documentsOnly} lines come only from the mirrored budget
          documents and {meta.lineSourceOverlap.workbookOnly} only from the FY27 workbook.
          They are not merged on a fuzzy name match — that would be a guess wearing a
          join&rsquo;s clothes — so a line may have a shorter history than it looks like it
          should.
        </p>
      </>}>

      <div className="flex flex-wrap gap-3 items-center mb-4">
        <input value={q} onChange={e => setQ(e.target.value)}
          placeholder="Search a line or a function group…"
          className="px-3 py-2 text-sm rounded border w-full sm:w-96"
          style={{ background: 'var(--surface-2)', borderColor: 'var(--grid)',
                   color: 'var(--text-primary)' }} />
        <label className="text-xs inline-flex items-center gap-2"
          style={{ color: 'var(--text-secondary)' }}>
          <input type="checkbox" checked={onlyBoth}
            onChange={e => setOnlyBoth(e.target.checked)} />
          Only lines both sources name
        </label>
        <span className="text-xs tnum" style={{ color: 'var(--text-muted)' }}>
          {filtered.length.toLocaleString()} shown
        </span>
      </div>

      <div className="grid lg:grid-cols-[minmax(0,22rem)_minmax(0,1fr)] gap-6">
        <div className="max-h-[32rem] overflow-y-auto rounded border"
          style={{ borderColor: 'var(--grid)' }}>
          {filtered.slice(0, 400).map(l => {
            const on = l.key === sel
            return (
              <button key={l.key} onClick={() => setSel(on ? null : l.key)}
                aria-pressed={on}
                className="w-full text-left px-3 py-2 border-b block"
                style={{ borderColor: 'var(--grid)',
                         background: on ? 'var(--surface-3)' : 'transparent' }}>
                <span className="text-[13px] font-medium block">{l.label}</span>
                <span className="text-[11px] block" style={{ color: 'var(--text-muted)' }}>
                  {l.group ?? 'no function group'} · {l.years.length} year
                  {l.years.length === 1 ? '' : 's'}
                  {l.sources.length === 2 ? ' · both sources' : ''}
                </span>
              </button>
            )
          })}
          {filtered.length > 400 && (
            <p className="px-3 py-2 text-[11px]" style={{ color: 'var(--text-muted)' }}>
              {(filtered.length - 400).toLocaleString()} more — narrow the search.
            </p>
          )}
        </div>

        <div>
          {selected ? <LineDetail line={selected} />
            : <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
                Pick a line to see its history.
              </p>}
        </div>
      </div>
    </Section>
  )
}

function LineDetail({ line }: { line: Line }) {
  const years = line.years
  const budgets = years.filter(y => y.budget !== undefined)
  const first = budgets[0], last = budgets[budgets.length - 1]
  const span = first && last && last.fy > first.fy && first.budget! > 0
    ? (Math.pow(last.budget! / first.budget!, 1 / (last.fy - first.fy)) - 1) * 100
    : null

  return (
    <div>
      <h3 className="text-lg font-bold mb-0.5">{line.label}</h3>
      <p className="text-xs mb-4" style={{ color: 'var(--text-muted)' }}>
        {line.group ?? 'no function group'}
        {line.row ? ` · workbook row ${line.row}` : ''}
        {' · '}named by {line.sources.join(' and ')}
      </p>

      {span !== null && (
        <p className="text-sm mb-4">
          Budget moved from <strong className="tnum">{usd(first!.budget)}</strong> (FY{first!.fy})
          to <strong className="tnum">{usd(last!.budget)}</strong> (FY{last!.fy}) —{' '}
          <strong className="tnum" style={{
            color: span > 3 ? 'var(--status-critical)'
              : span < 0 ? 'var(--status-good)' : 'var(--text-primary)' }}>
            {pct(span, 2)} a year
          </strong>{' '}compounded.
          {budgets.length < 4 && (
            <span style={{ color: 'var(--text-muted)' }}>
              {' '}Off {budgets.length} points — read the years before calling it a trend.
            </span>
          )}
        </p>
      )}

      <div className="overflow-x-auto">
        <table className="w-full text-[13px] border-collapse">
          <thead>
            <tr className="text-left" style={{ color: 'var(--text-secondary)' }}>
              <th className="pb-1.5 font-semibold">FY</th>
              <th className="pb-1.5 font-semibold text-right">Budget</th>
              <th className="pb-1.5 font-semibold text-right">Change</th>
              <th className="pb-1.5 font-semibold text-right">Actual</th>
              <th className="pb-1.5 font-semibold text-right">vs budget</th>
              <th className="pb-1.5 font-semibold pl-3">Basis</th>
            </tr>
          </thead>
          <tbody>
            {years.map((y, i) => {
              const prev = [...years.slice(0, i)].reverse().find(p => p.budget !== undefined)
              const chg = prev && y.budget !== undefined && prev.budget! > 0
                ? (y.budget! / prev.budget! - 1) * 100 : null
              return (
                <tr key={y.fy} className="border-t" style={{ borderColor: 'var(--grid)' }}>
                  <td className="py-1.5 tnum font-medium">FY{y.fy}</td>
                  <td className="py-1.5 text-right tnum">{usd(y.budget)}</td>
                  <td className="py-1.5 text-right tnum text-xs"
                    style={{ color: chg === null ? 'var(--text-muted)'
                      : chg > 0 ? 'var(--status-critical)' : 'var(--status-good)' }}>
                    {chg === null ? '—' : pct(chg)}
                  </td>
                  <td className="py-1.5 text-right tnum">{usd(y.actual)}</td>
                  <td className="py-1.5 text-right tnum text-xs"
                    style={{ color: 'var(--text-secondary)' }}>
                    {y.variance !== undefined ? usd(y.variance) : '—'}
                  </td>
                  <td className="py-1.5 pl-3 text-[11px]" style={{ color: 'var(--text-muted)' }}>
                    {y.stage === 'settled' ? 'approved' : y.stage === 'proposed' ? 'proposed' : ''}
                    {y.disagree ? ' · documents disagree' : ''}
                    {y.budget !== undefined && y.actual !== undefined && y.sameDoc === false
                      ? ' · halves from different documents, not subtracted' : ''}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {line.workbook && (
        <div className="mt-4">
          <p className="text-[11px] font-semibold uppercase tracking-widest mb-1.5"
            style={{ color: 'var(--text-muted)' }}>FY27 workbook, same line</p>
          <div className="flex flex-wrap gap-x-5 gap-y-1 text-[12px]">
            {Object.entries(line.workbook).sort().map(([fy, cols]) =>
              Object.entries(cols).map(([kind, v]) => (
                <span key={fy + kind} className="tnum">
                  <span style={{ color: 'var(--text-muted)' }}>FY{fy} {kind.replace(/_/g, ' ')} </span>
                  {usd(v)}
                </span>
              )))}
          </div>
        </div>
      )}

      <Note>
        A variance is shown only where the budget and the actual were read from the same
        row of the same document. Where they come from different documents the pair is
        printed and not subtracted — the documents disagree with themselves by more than
        the effect a variance would measure.
      </Note>
    </div>
  )
}

/* ------------------------------------------------------------- gross budget template */

/** The school budget with every source of money on the page — and the blanks called out.
 *
 *  The district publishes a NET budget: each line is what the town must raise after
 *  grants, fees and reimbursements have paid for part of the thing. A $20,000 line may be
 *  a $220,000 line. Nothing in the document marks it.
 *
 *  So the empty column is the point of this table, and it is styled to be as loud as the
 *  figures beside it. "Not held" must never be allowed to read as "nothing there" — that
 *  is the exact reading this whole page exists to prevent.
 */
function Gross({ g }: { g: GrossBudget }) {
  const [q, setQ] = useState('')
  const [sort, setSort] = useState<'org' | 'spend' | 'variance'>('spend')

  const rows = useMemo(() => {
    const needle = q.trim().toLowerCase()
    const r = g.rows.filter(x => !needle
      || x.label.toLowerCase().includes(needle)
      || x.org.toLowerCase().includes(needle)
      || x.object.includes(needle))
    return [...r].sort((a, b) =>
      sort === 'org' ? a.org.localeCompare(b.org)
        : sort === 'spend' ? b.net.spent - a.net.spent
          : Math.abs(b.net.unspent) - Math.abs(a.net.unspent))
  }, [g.rows, q, sort])

  const t = g.totals as Record<string, number>
  return (
    <Section id="gross" eyebrow="5 — The budget with all the money on it"
      title={`Gross school budget, FY${g.fy}`}
      lede={<>
        <p className="mb-3">
          The district publishes a <strong style={{ color: 'var(--text-primary)' }}>net
          </strong> budget: every line is what the town must raise <em>after</em> grants,
          fees and reimbursements have paid for part of the thing. A line reading $20,000
          can be a $220,000 line. Nothing in the document marks which.
        </p>
        <p className="mb-3">
          This is the same budget with the other money beside it. Today almost every
          &ldquo;other money&rdquo; cell is empty — and it is drawn to be as visible as the
          figures, because <strong style={{ color: 'var(--text-primary)' }}>&ldquo;not
          held&rdquo; must never be read as &ldquo;nothing there&rdquo;.</strong>
        </p>
        <p style={{ color: 'var(--text-muted)' }}>{g.asOf}</p>
      </>}>

      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
        <Stat label="Town appropriation" value={usd(t.netAppropriated)}
          sub="What the district’s own budget document publishes" />
        <Stat label="Spent from the general fund" value={usd(t.netSpent)}
          sub={`258 accounts, period ${g.period}`} />
        <Stat label="Known spent outside it" value={usd(t.knownOutsideGeneralFund)}
          sub={`${g.unattributed.length} school funds — none attributable to a line`}
          tone="critical" />
        <Stat label="Gross floor" value={usd(t.grossFloor)}
          sub="A floor, never a total" tone="critical" />
      </div>

      <div className="card p-4 mb-6 max-w-3xl" style={{ borderLeft: '3px solid var(--status-critical)' }}>
        <p className="text-[11px] font-semibold uppercase tracking-widest mb-1.5"
          style={{ color: 'var(--status-critical)' }}>
          0 of {g.rows.length} lines have their outside funding attached
        </p>
        <p className="text-sm leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
          {String(t.attributableNote)} {String(t.grossFloorNote)}
        </p>
      </div>

      <div className="flex flex-wrap gap-3 items-center mb-3">
        <input value={q} onChange={e => setQ(e.target.value)}
          placeholder="Search an account, org or object code…"
          className="px-3 py-2 text-sm rounded border w-full sm:w-80"
          style={{ background: 'var(--surface-2)', borderColor: 'var(--grid)',
                   color: 'var(--text-primary)' }} />
        {(['spend', 'variance', 'org'] as const).map(k => (
          <button key={k} onClick={() => setSort(k)} aria-pressed={sort === k}
            className="text-xs px-2 py-1 rounded font-semibold"
            style={{ background: sort === k ? 'var(--surface-3)' : 'transparent',
                     color: sort === k ? 'var(--text-primary)' : 'var(--text-muted)' }}>
            {k === 'spend' ? 'by spending' : k === 'variance' ? 'by variance' : 'by account'}
          </button>
        ))}
        <span className="text-xs tnum" style={{ color: 'var(--text-muted)' }}>
          {rows.length} of {g.rows.length}
        </span>
      </div>

      <div className="overflow-x-auto -mx-5 px-5">
        <table className="w-full text-[13px] border-collapse min-w-[900px]">
          <thead>
            <tr className="text-left" style={{ color: 'var(--text-secondary)' }}>
              <th className="pb-2 font-semibold">Account</th>
              <th className="pb-2 font-semibold text-right">Town budget</th>
              <th className="pb-2 font-semibold text-right">Town spent</th>
              <th className="pb-2 font-semibold text-right">Variance</th>
              <th className="pb-2 font-semibold text-center">Grants &amp; other funds</th>
              <th className="pb-2 font-semibold text-right">Gross</th>
            </tr>
          </thead>
          <tbody>
            {rows.slice(0, 80).map(r => (
              <tr key={r.accountId} className="border-t" style={{ borderColor: 'var(--grid)' }}>
                <td className="py-2">
                  <span className="font-medium">{r.label}</span>
                  <span className="block text-[11px] tnum" style={{ color: 'var(--text-muted)' }}>
                    {r.org} · {r.object}
                  </span>
                </td>
                <td className="py-2 text-right tnum">{usd(r.net.revised)}</td>
                <td className="py-2 text-right tnum">{usd(r.net.spent)}</td>
                <td className="py-2 text-right tnum"
                  style={{ color: r.net.unspent < -0.5 ? 'var(--status-critical)'
                    : r.net.unspent > 0.5 ? 'var(--status-good)' : 'var(--text-muted)' }}>
                  {Math.abs(r.net.unspent) < 0.5 ? '—' : usd(r.net.unspent)}
                </td>
                <td className="py-2 text-center">
                  <NotHeldCell why={r.offsets.blockedBy} />
                </td>
                <td className="py-2 text-right text-[11px]" style={{ color: 'var(--text-muted)' }}>
                  unknown
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {rows.length > 80 && (
        <Note>Showing the first 80 of {rows.length}. Narrow the search to see others.</Note>
      )}

      <h3 className="text-sm font-semibold mt-8 mb-2">
        Money we know was spent on the schools, and cannot attach to any line
      </h3>
      <p className="text-[13px] mb-3 max-w-3xl" style={{ color: 'var(--text-secondary)' }}>
        These funds paid for real staff and real programmes in FY{g.fy}. Every dollar
        belongs against one of the lines above and we cannot say which. Spreading it in
        proportion to line size would look right and be invented.
      </p>
      <div className="overflow-x-auto -mx-5 px-5">
        <table className="w-full text-[13px] border-collapse min-w-[560px]">
          <thead>
            <tr className="text-left" style={{ color: 'var(--text-secondary)' }}>
              <th className="pb-2 font-semibold">Fund</th>
              <th className="pb-2 font-semibold">Restricted to</th>
              <th className="pb-2 font-semibold text-right">Spent</th>
              <th className="pb-2 font-semibold text-center">Which lines</th>
            </tr>
          </thead>
          <tbody>
            {g.unattributed.filter(u => u.spent > 0)
              .sort((a, b) => b.spent - a.spent).slice(0, 14).map(u => (
              <tr key={u.fund} className="border-t" style={{ borderColor: 'var(--grid)' }}>
                <td className="py-2">
                  <span className="tnum text-xs mr-2" style={{ color: 'var(--text-muted)' }}>
                    {u.fund}
                  </span>{u.name}
                </td>
                <td className="py-2 text-xs" style={{ color: 'var(--text-muted)' }}>
                  {u.restriction ?? <span style={{ color: 'var(--status-warning)' }}>
                    not stated in any document we hold</span>}
                </td>
                <td className="py-2 text-right tnum">{usd(u.spent)}</td>
                <td className="py-2 text-center"><NotHeldCell why="Fund-level spending detail, by account." /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="mt-6 flex flex-wrap gap-x-6 gap-y-2 text-[11px]">
        {g.legend.map(l => (
          <span key={l.state} style={{ color: 'var(--text-muted)' }}>
            <strong style={{ color: 'var(--text-secondary)' }}>{l.state}</strong> — {l.means}
          </span>
        ))}
      </div>
    </Section>
  )
}

/** A gap, drawn to be seen. A blank cell reads as zero; this must not. */
function NotHeldCell({ why }: { why: string }) {
  return (
    <span title={why}
      className="inline-block text-[11px] font-semibold px-2 py-0.5 rounded"
      style={{ color: 'var(--status-warning)', background: 'var(--surface-2)',
               border: '1px dashed var(--status-warning)' }}>
      not held
    </span>
  )
}

/* -------------------------------------------------------------- department ledger */

function Departments({ rows }: { rows: Dept[] }) {
  const [all, setAll] = useState(false)
  const shown = all ? rows : rows.slice(0, 12)
  const fy = rows[0]?.fy, period = rows[0]?.period
  return (
    <Section id="departments" eyebrow="4 — The town's own ledger"
      title={`Every department, FY${fy ?? ''} at period ${period ?? ''}`}
      lede={<>
        <p>
          The Town Accountant&rsquo;s year-to-date budget report: appropriation, transfers,
          spent, encumbered, and what is left. At year-end close the last column{' '}
          <em>is</em> the surplus. This is period {period} — three quarters through — so it
          is a position, not an outcome. Sorted by what was unspent at that moment.
        </p>
      </>}>
      <div className="overflow-x-auto -mx-5 px-5">
        <table className="w-full text-[13px] border-collapse min-w-[760px]">
          <thead>
            <tr className="text-left" style={{ color: 'var(--text-secondary)' }}>
              <th className="pb-2 font-semibold">Department</th>
              <th className="pb-2 font-semibold text-right">Appropriated</th>
              <th className="pb-2 font-semibold text-right">Transfers</th>
              <th className="pb-2 font-semibold text-right">Spent</th>
              <th className="pb-2 font-semibold text-right">Encumbered</th>
              <th className="pb-2 font-semibold text-right">Unspent</th>
              <th className="pb-2 font-semibold text-right">Used</th>
            </tr>
          </thead>
          <tbody>
            {shown.map(d => (
              <tr key={d.dept} className="border-t" style={{ borderColor: 'var(--grid)' }}>
                <td className="py-2">
                  <span className="tnum text-xs mr-2"
                    style={{ color: 'var(--text-muted)' }}>{d.dept}</span>
                  {d.name}
                </td>
                <td className="py-2 text-right tnum">{usdK(d.original)}</td>
                <td className="py-2 text-right tnum text-xs"
                  style={{ color: d.transfers ? 'var(--status-warning)' : 'var(--text-muted)' }}>
                  {d.transfers ? usd(d.transfers) : '—'}
                </td>
                <td className="py-2 text-right tnum">{usdK(d.expended)}</td>
                <td className="py-2 text-right tnum">{usdK(d.encumbered)}</td>
                <td className="py-2 text-right tnum font-semibold">{usdK(d.available)}</td>
                <td className="py-2 text-right tnum text-xs"
                  style={{ color: d.pct_used > 100 ? 'var(--status-critical)'
                    : 'var(--text-secondary)' }}>{d.pct_used.toFixed(1)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {rows.length > 12 && (
        <button onClick={() => setAll(!all)} className="mt-3 text-sm font-semibold"
          style={{ color: 'var(--series-cost)' }}>
          {all ? 'Show fewer' : `Show all ${rows.length} departments`}
        </button>
      )}
      <Note>
        The appropriation columns are printed rounded to whole dollars while spent and
        encumbered carry cents, so a row does not reconcile to itself by a few pence and a
        sum of rows cannot equal the report&rsquo;s own grand total exactly. That is
        arithmetic, not a missing row.
      </Note>
    </Section>
  )
}

/* --------------------------------------------------------------- funding sources */

function Funding({ funding }: { funding: Ledger['funding'] }) {
  const top = funding.revenue.filter(r => Math.abs(r.budgeted) > 20000).slice(0, 18)
  return (
    <Section id="funding" eyebrow="5 — Where the money comes from"
      title="Revenue, transfers in, and the funds beside the budget"
      lede={<>
        <p className="mb-3">
          A budget line is <strong style={{ color: 'var(--text-primary)' }}>net</strong> —
          what the town has to raise after everything else that pays for the thing has
          been subtracted. So a line can rise because the thing cost more, or because a
          grant stopped covering part of it, and the expense side cannot tell them apart.
          This is the other side.
        </p>
      </>}>

      <h3 className="text-sm font-semibold mb-2">General fund revenue, largest first</h3>
      <div className="overflow-x-auto -mx-5 px-5 mb-8">
        <table className="w-full text-[13px] border-collapse min-w-[560px]">
          <thead>
            <tr className="text-left" style={{ color: 'var(--text-secondary)' }}>
              <th className="pb-2 font-semibold">Account</th>
              <th className="pb-2 font-semibold text-right">Budgeted</th>
              <th className="pb-2 font-semibold text-right">Received</th>
              <th className="pb-2 font-semibold text-right">%</th>
            </tr>
          </thead>
          <tbody>
            {top.map(r => (
              <tr key={r.object} className="border-t" style={{ borderColor: 'var(--grid)' }}>
                <td className="py-2">
                  <span className="tnum text-xs mr-2"
                    style={{ color: 'var(--text-muted)' }}>{r.object}</span>{r.name}
                </td>
                <td className="py-2 text-right tnum">{usdK(r.budgeted)}</td>
                <td className="py-2 text-right tnum">{usdK(r.received)}</td>
                <td className="py-2 text-right tnum text-xs"
                  style={{ color: 'var(--text-secondary)' }}>
                  {r.pct_received === null ? '—' : `${r.pct_received.toFixed(0)}%`}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h3 className="text-sm font-semibold mb-2">Money arriving from another fund</h3>
      <div className="overflow-x-auto -mx-5 px-5 mb-8">
        <table className="w-full text-[13px] border-collapse min-w-[560px]">
          <thead>
            <tr className="text-left" style={{ color: 'var(--text-secondary)' }}>
              <th className="pb-2 font-semibold">Fund</th>
              <th className="pb-2 font-semibold">Account</th>
              <th className="pb-2 font-semibold text-right">Budgeted</th>
              <th className="pb-2 font-semibold text-right">Received</th>
            </tr>
          </thead>
          <tbody>
            {funding.interfund.map((r, i) => (
              <tr key={i} className="border-t" style={{ borderColor: 'var(--grid)' }}>
                <td className="py-2 tnum text-xs">{r.fund}</td>
                <td className="py-2">
                  <span className="tnum text-xs mr-2"
                    style={{ color: 'var(--text-muted)' }}>{r.object}</span>{r.name}
                </td>
                <td className="py-2 text-right tnum">{usdK(r.budgeted)}</td>
                <td className="py-2 text-right tnum">{usdK(r.received)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Note>
        <code>FBCYBUDGET</code> is free cash voted into the operating budget — one-time
        money doing recurring work, which is the argument the free cash page makes at
        length. <code>OP TRAN</code> and <code>TRANS ENT</code> are operating transfers in
        from special revenue, capital projects and the enterprise funds.
      </Note>

      <h3 className="text-sm font-semibold mb-2 mt-8">
        Revolving, grant and gift funds, by balance
      </h3>
      <div className="overflow-x-auto -mx-5 px-5">
        <table className="w-full text-[13px] border-collapse min-w-[620px]">
          <thead>
            <tr className="text-left" style={{ color: 'var(--text-secondary)' }}>
              <th className="pb-2 font-semibold">Fund</th>
              <th className="pb-2 font-semibold text-right">Revenue</th>
              <th className="pb-2 font-semibold text-right">Spent</th>
              <th className="pb-2 font-semibold text-right">Balance</th>
            </tr>
          </thead>
          <tbody>
            {funding.funds.slice(0, 15).map((f, i) => (
              <tr key={i} className="border-t" style={{ borderColor: 'var(--grid)' }}>
                <td className="py-2">
                  <span className="tnum text-xs mr-2"
                    style={{ color: 'var(--text-muted)' }}>{f.fund}</span>{f.name}
                  {f.restriction && (
                    <span className="block text-[11px]"
                      style={{ color: 'var(--text-muted)' }}>{f.restriction}</span>
                  )}
                </td>
                <td className="py-2 text-right tnum">{usdK(f.revenue)}</td>
                <td className="py-2 text-right tnum">{usdK(f.spent)}</td>
                <td className="py-2 text-right tnum font-semibold">{usdK(f.closing_balance)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Note>
        A fund balance rolls forward from year to year. A department appropriation lapses
        at year end. They are printed in the same units and they are not the same
        quantity, and nothing here adds them together.
      </Note>
    </Section>
  )
}

/* -------------------------------------------------------------------- provenance */

function Provenance({ meta }: { meta: Ledger['meta'] }) {
  return (
    <Section id="provenance" eyebrow="6 — What this rests on"
      title="The database behind this page"
      lede={<p>
        Built by <code>scripts/build_db.py</code> from the extracted CSVs, which are the
        source of truth. The database is rebuilt from scratch on every run and nothing is
        ever edited in it — a row in a database has no address, no publisher filename and
        no checksum. Every fact row carries the document it came from.
      </p>}>
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 mb-6">
        {Object.entries(meta.counts).map(([k, v]) => (
          <div key={k} className="card p-3">
            <p className="text-[11px] font-semibold uppercase tracking-widest mb-1"
              style={{ color: 'var(--text-muted)' }}>{k.replace(/_/g, ' ')}</p>
            <p className="text-lg font-bold tnum leading-none"
              style={{ color: v === 0 ? 'var(--status-critical)' : 'var(--text-primary)' }}>
              {v.toLocaleString()}
            </p>
          </div>
        ))}
      </div>
      <div className="card p-4 max-w-3xl">
        <p className="text-[11px] font-semibold uppercase tracking-widest mb-1.5"
          style={{ color: 'var(--status-critical)' }}>Crosswalk: 0 rows</p>
        <p className="text-sm leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
          {meta.crosswalkNote}
        </p>
      </div>
      {meta.commit && (
        <Note>Generated from commit <code>{meta.commit}</code>.</Note>
      )}
    </Section>
  )
}
