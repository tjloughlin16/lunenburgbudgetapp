import { Fragment, useEffect, useMemo, useState } from 'react'
import { Section, Note } from '../components/primitives'

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

type Cell = { state: 'obtained' | 'partial' | 'missing'; n?: number; docs?: number; note?: string }
type RowDef = { id: string; group: string; label: string; why: string }
type YearRow = {
  fy: number; budget?: number; stage?: string; actual?: number
  variance?: number; sameDoc?: boolean; disagree?: boolean
}
type Line = {
  key: string; label: string; section: string | null; group: string | null
  years: YearRow[]; sources: string[]; row?: number
  workbook?: Record<string, Record<string, number>>
}
type Total = {
  fy: number; budget: number | null; actual: number | null
  actualToDate?: number | null; encumberedToDate?: number | null
  surplus?: number; surplusPct?: number
  committed?: number; uncommitted?: number; partial?: boolean
}
type Dept = {
  dept: string; name: string; fy: number; period: number; original: number
  transfers: number; revised: number; expended: number; encumbered: number
  available: number; pct_used: number; doc_id: string
}
type Ledger = {
  coverage: { years: number[]; rowDefs: RowDef[]; cells: Record<string, Record<string, Cell>> }
  lines: Line[]
  totals: Total[]
  departments: Dept[]
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
      <Departments rows={data.departments} />
      <Funding funding={data.funding} />
      <Provenance meta={data.meta} />
    </>
  )
}

/* ---------------------------------------------------------------- coverage matrix */

function Coverage({ cov }: { cov: Ledger['coverage'] }) {
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
    let obtained = 0, partial = 0, missing = 0
    for (const fy of cov.years) for (const rd of cov.rowDefs) {
      const s = cov.cells[String(fy)]?.[rd.id]?.state
      if (s === 'obtained') obtained++
      else if (s === 'partial') partial++
      else missing++
    }
    return { obtained, partial, missing, total: cov.years.length * cov.rowDefs.length }
  }, [cov])

  return (
    <Section id="coverage" eyebrow="1 — What we actually hold"
      title="Completeness, by fiscal year"
      lede={<>
        <p className="mb-3">
          The same twelve rows for every year, so a gap is visible rather than argued
          about. This matrix is computed from the database — it asks what is present
          rather than reading a list somebody maintains, so a document that arrives shows
          up here without anybody remembering to tick a box.
        </p>
        <p>
          <strong style={{ color: 'var(--text-primary)' }}>Partial is its own state and it
          matters.</strong> The FY26 quarterly spend report exists, but it was run as a
          department rollup: the whole school district is one row. That cannot be traced
          to a line, so it is not the same document as a line-level report and is not
          marked as one.
        </p>
      </>}>

      <div className="flex flex-wrap gap-4 mb-5 text-xs">
        {(Object.keys(STATE) as (keyof typeof STATE)[]).map(k => (
          <span key={k} className="inline-flex items-center gap-1.5"
            style={{ color: STATE[k].color }}>
            <span aria-hidden="true" className="text-base leading-none">{STATE[k].glyph}</span>
            {STATE[k].word}
          </span>
        ))}
        <span style={{ color: 'var(--text-muted)' }}>
          {tally.obtained} obtained · {tally.partial} partial · {tally.missing} not held,
          of {tally.total} cells
        </span>
      </div>

      <div className="overflow-x-auto -mx-5 px-5">
        <table className="w-full text-[13px] border-collapse min-w-[860px]">
          <thead>
            <tr>
              <th className="text-left font-semibold pb-2 pr-3 sticky left-0"
                style={{ background: 'var(--surface-1)' }}>Document</th>
              {cov.years.map(y => (
                <th key={y} className="pb-2 px-1 font-semibold tnum text-center whitespace-nowrap"
                  style={{ color: 'var(--text-secondary)' }}>FY{String(y).slice(2)}</th>
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
                    <td className="py-2 pr-3 align-top sticky left-0"
                      style={{ background: 'var(--surface-1)' }}>
                      <div className="font-medium">{rd.label}</div>
                      <div className="text-[11px] leading-snug max-w-[22rem]"
                        style={{ color: 'var(--text-muted)' }}>{rd.why}</div>
                    </td>
                    {cov.years.map(y => {
                      const c = cov.cells[String(y)]?.[rd.id] ?? { state: 'missing' as const }
                      const s = STATE[c.state]
                      const title = [rd.label, `FY${y}`, s.word, c.note,
                        c.n ? `${c.n} rows` : null, c.docs ? `${c.docs} documents` : null]
                        .filter(Boolean).join(' · ')
                      return (
                        <td key={y} className="text-center py-2 px-1" title={title}>
                          <span aria-label={`FY${y}: ${s.word}`} className="text-lg leading-none"
                            style={{ color: s.color }}>{s.glyph}</span>
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
      <Note>
        Hover any cell for the row count and the number of documents behind it. Every
        &ldquo;purchase orders closed after close&rdquo; cell is empty for every year: that
        step is what moved the FY25 surplus from $582,115.44 on 3 September 2025 to
        $603,885.97 on 17 September, and it cannot be recovered from a single report run.
      </Note>
    </Section>
  )
}

/* ------------------------------------------------------------------- year totals */

function Totals({ totals }: { totals: Total[] }) {
  const closed = totals.filter(t => t.surplus !== undefined)
  return (
    <Section id="totals" eyebrow="2 — Does it add up"
      title="Budget against actual, whole years"
      lede={<>
        <p className="mb-3">
          Both halves of a year, from the one source that prints them side by side: the
          FY27 projection workbook. The line rows sum exactly to the totals the sheet
          itself prints, which is the check that matters — our sum of the lines is not the
          same claim as the sheet&rsquo;s own total.
        </p>
        <p>
          <strong style={{ color: 'var(--text-primary)' }}>These are restatements, not
          ledger figures.</strong> An &ldquo;actual&rdquo; here is a prior year
          re-presented by the people who spent it, inside the argument for next
          year&rsquo;s budget. The town&rsquo;s own closing figure for FY25 is
          $603,885.97, arrived at by closing the books rather than by subtracting two
          columns, and it is the better number to quote.
        </p>
      </>}>

      <div className="overflow-x-auto -mx-5 px-5">
        <table className="w-full text-sm border-collapse min-w-[680px]">
          <thead>
            <tr className="text-left" style={{ color: 'var(--text-secondary)' }}>
              <th className="pb-2 font-semibold">Year</th>
              <th className="pb-2 font-semibold text-right">Budgeted</th>
              <th className="pb-2 font-semibold text-right">Spent</th>
              <th className="pb-2 font-semibold text-right">Under budget</th>
              <th className="pb-2 font-semibold text-right">%</th>
              <th className="pb-2 font-semibold pl-4">Note</th>
            </tr>
          </thead>
          <tbody>
            {totals.map(t => (
              <tr key={t.fy} className="border-t" style={{ borderColor: 'var(--grid)' }}>
                <td className="py-2.5 font-semibold tnum">FY{t.fy}</td>
                <td className="py-2.5 text-right tnum">{usd(t.budget)}</td>
                <td className="py-2.5 text-right tnum">
                  {t.actual !== null && t.actual !== undefined ? usd(t.actual)
                    : t.actualToDate ? usd(t.actualToDate) : '—'}
                </td>
                <td className="py-2.5 text-right tnum font-semibold"
                  style={{ color: t.surplus ? 'var(--status-warning)' : 'var(--text-muted)' }}>
                  {t.surplus !== undefined ? usd(t.surplus) : '—'}
                </td>
                <td className="py-2.5 text-right tnum"
                  style={{ color: 'var(--text-secondary)' }}>
                  {t.surplusPct !== undefined ? `${t.surplusPct.toFixed(2)}%` : '—'}
                </td>
                <td className="py-2.5 pl-4 text-xs" style={{ color: 'var(--text-muted)' }}>
                  {t.partial
                    ? `Incomplete year — the column is headed “Actuals to date”. ${usdK(t.committed)} committed, ${usdK(t.uncommitted)} uncommitted.`
                    : t.budget === null ? 'No budget column in this workbook for this year'
                      : ''}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {closed.length > 0 && (
        <Note>
          Only {closed.length} of {totals.length} years here have both halves. The rest
          have one column or the other, which is the coverage matrix above restated as
          arithmetic. A year with one half cannot produce a variance, and none is shown.
        </Note>
      )}
    </Section>
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
