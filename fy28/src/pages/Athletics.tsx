import { useState } from 'react'
import { MODEL, usd } from '../model/engine'
import type { Tab } from '../routes'

const H = MODEL.athleticsHistory
const S = MODEL.splitReporting

type Row = (typeof H.rows)[number]

/** Totals by year for one side, and the line items under it. */
function fold(side: 'general' | 'revolving', rows: Row[]) {
  const items = new Map<string, Map<number, number>>()
  for (const r of rows) {
    if (r.side !== side || r.item.startsWith('REVENUE')) continue
    if (!items.has(r.item)) items.set(r.item, new Map())
    const m = items.get(r.item)!
    m.set(r.fy, (m.get(r.fy) ?? 0) + r.amount)
  }
  const totals = new Map<number, number>()
  for (const m of items.values())
    for (const [fy, v] of m) totals.set(fy, (totals.get(fy) ?? 0) + v)
  const order = [...items.entries()]
    .sort((a, b) => [...b[1].values()].reduce((x, y) => x + y, 0)
                  - [...a[1].values()].reduce((x, y) => x + y, 0))
  return { order, totals }
}

const FY = (y: number) => `FY${String(y).slice(2)}`

/** One side of the money, as a table of line items by year. */
function SideTable({ side, title, note, rows }: {
  side: 'general' | 'revolving'; title: string; note: React.ReactNode; rows: Row[]
}) {
  const { order, totals } = fold(side, rows)
  const unpub = new Set(H.fundUnpublished)
  const partial = new Set(H.fundPartial)
  return (
    <div className="card p-5">
      <h3 className="text-sm font-bold mb-1">{title}</h3>
      <p className="text-[12px] leading-relaxed mb-4"
        style={{ color: 'var(--text-secondary)' }}>{note}</p>
      {/* Wide table: scrolls inside its own box rather than pushing the page sideways. */}
      <div className="overflow-x-auto -mx-2 px-2">
        <table className="w-full text-[12px] tnum whitespace-nowrap">
          <thead>
            <tr style={{ color: 'var(--text-muted)' }}>
              <th className="text-left font-bold uppercase tracking-widest text-[10px] pb-1 pr-3">line</th>
              {H.years.map(y => (
                <th key={y} className="text-right font-bold uppercase tracking-widest text-[10px] pb-1 pl-3">
                  {FY(y)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {order.map(([item, m]) => (
              <tr key={item} className="border-t" style={{ borderColor: 'var(--grid)' }}>
                <td className="py-1 pr-3" style={{ whiteSpace: 'normal', minWidth: '11rem' }}>{item}</td>
                {H.years.map(y => (
                  <td key={y} className="text-right pl-3"
                    style={{ color: m.get(y) ? undefined : 'var(--text-muted)' }}>
                    {m.get(y) ? usd(m.get(y)!) : '—'}
                  </td>
                ))}
              </tr>
            ))}
            <tr className="border-t-2 font-bold" style={{ borderColor: 'var(--grid)' }}>
              <td className="py-1.5 pr-3">total</td>
              {H.years.map(y => (
                <td key={y} className="text-right pl-3">
                  {side === 'revolving' && unpub.has(y)
                    ? <span className="font-normal text-[10px] uppercase tracking-wide"
                        style={{ color: 'var(--status-serious)' }}>not published</span>
                    : totals.get(y)
                      ? <>{usd(totals.get(y)!)}{side === 'revolving' && partial.has(y) &&
                          <span className="font-normal text-[10px] ml-1"
                            style={{ color: 'var(--status-serious)' }}>partial</span>}</>
                      : '—'}
                </td>
              ))}
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  )
}

/** The distribution: how much of all-in athletics each side carried, year by year. */
function Distribution() {
  const g = fold('general', H.rows).totals
  const r = fold('revolving', H.rows).totals
  const unpub = new Set(H.fundUnpublished)
  const partial = new Set(H.fundPartial)
  const known = H.years.filter(y => !unpub.has(y) && !partial.has(y))
  const shares = known.map(y => (r.get(y) ?? 0) / ((g.get(y) ?? 0) + (r.get(y) ?? 0)))
  const lo = Math.min(...shares) * 100, hi = Math.max(...shares) * 100

  return (
    <div className="card p-5">
      <h3 className="text-sm font-bold mb-1">Who paid for athletics</h3>
      <p className="text-[12px] leading-relaxed mb-4" style={{ color: 'var(--text-secondary)' }}>
        Each bar is one year. The dark part is the town&rsquo;s appropriation; the light part
        is the fee-funded revolving fund. Where the fund is hatched, no document published
        its figures &mdash; the bar is a floor, not a total.
      </p>
      <div className="space-y-1.5">
        {H.years.map(y => {
          const gv = g.get(y) ?? 0, rv = r.get(y) ?? 0
          const all = gv + rv
          const max = Math.max(...H.years.map(z => (g.get(z) ?? 0) + (r.get(z) ?? 0)))
          const missing = unpub.has(y)
          return (
            <div key={y} className="flex items-center gap-2 text-[11px] tnum">
              <span className="w-10 shrink-0" style={{ color: 'var(--text-muted)' }}>{FY(y)}</span>
              <div className="flex-1 flex h-5 rounded-sm overflow-hidden"
                style={{ background: 'var(--surface-3)' }}>
                <div style={{ width: `${(gv / max) * 100}%`, background: 'var(--text-primary)' }} />
                <div title={missing ? 'not published' : undefined}
                  style={{
                    width: `${(rv / max) * 100}%`,
                    background: 'var(--status-good)',
                    opacity: partial.has(y) ? 0.45 : 1,
                  }} />
                {missing && (
                  <div style={{
                    width: '8%',
                    backgroundImage:
                      'repeating-linear-gradient(45deg, var(--status-serious) 0 2px, transparent 2px 6px)',
                  }} />
                )}
              </div>
              <span className="w-24 text-right shrink-0">
                {missing ? <span style={{ color: 'var(--status-serious)' }}>fund unknown</span>
                  : <>{usd(all)}{partial.has(y) && <span style={{ color: 'var(--status-serious)' }}> +</span>}</>}
              </span>
              <span className="w-14 text-right shrink-0" style={{ color: 'var(--text-secondary)' }}>
                {missing || !rv ? '—' : `${partial.has(y) ? '≥' : ''}${Math.round((rv / all) * 100)}%`}
              </span>
            </div>
          )
        })}
      </div>
      <p className="text-[13px] leading-relaxed mt-4 pt-3 border-t" style={{ borderColor: 'var(--grid)' }}>
        In every year where both sides were published, the fund carried between{' '}
        <strong>{lo.toFixed(0)}% and {hi.toFixed(0)}%</strong> of what athletics actually
        cost. None of it appears in the town&rsquo;s athletics lines.
      </p>
    </div>
  )
}

/** Transportation on its own — the line the whole question turns on. */
function TransportFocus() {
  const t = S.transportation.map(r => ({ ...r, total: r.general + r.revolving }))
  return (
    <div className="card p-5" style={{ borderColor: 'var(--status-good)' }}>
      <h3 className="text-sm font-bold mb-1">
        <span aria-hidden="true" style={{ color: 'var(--status-good)' }}>★ </span>
        Athletic transportation, both sides
      </h3>
      <p className="text-[12px] leading-relaxed mb-4" style={{ color: 'var(--text-secondary)' }}>
        From <a className="underline" href={`/docs/${S.doc}`}>{S.title}</a> &mdash; the only
        document the district published that lists this line twice, once as an appropriation
        and once as the {S.fund}.
      </p>
      <table className="w-full text-[13px] tnum">
        <thead>
          <tr style={{ color: 'var(--text-muted)' }}>
            <th className="text-left font-bold uppercase tracking-widest text-[10px] pb-1">FY</th>
            <th className="text-right font-bold uppercase tracking-widest text-[10px] pb-1">appropriated</th>
            <th className="text-right font-bold uppercase tracking-widest text-[10px] pb-1">revolving fund</th>
            <th className="text-right font-bold uppercase tracking-widest text-[10px] pb-1">all in</th>
            <th className="text-right font-bold uppercase tracking-widest text-[10px] pb-1">fund&nbsp;share</th>
          </tr>
        </thead>
        <tbody>
          {t.map(r => (
            <tr key={r.fy} className="border-t" style={{ borderColor: 'var(--grid)' }}>
              <td className="py-1.5">{FY(r.fy)}
                {r.basis !== 'actual' && <span className="ml-1.5 text-[10px] uppercase tracking-wide"
                  style={{ color: 'var(--text-muted)' }}>{r.basis}</span>}</td>
              <td className="text-right">{usd(r.general)}</td>
              <td className="text-right font-bold">{usd(r.revolving)}</td>
              <td className="text-right">{usd(r.total)}</td>
              <td className="text-right">{Math.round((r.revolving / r.total) * 100)}%</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="text-[13px] leading-relaxed mt-4">{S.establishes}</p>
      <p className="text-[12px] leading-relaxed mt-3 pt-3 border-t"
        style={{ borderColor: 'var(--grid)', color: 'var(--text-muted)' }}>
        <strong style={{ color: 'var(--text-primary)' }}>What it does not show. </strong>
        {S.doesNotEstablish} {S.roundingNote}
      </p>
    </div>
  )
}

/** Athletics, in full, as a drill-in rather than a chapter.
 *
 *  This page carries ACTUAL SPENDING, which nothing else in the app does. That is
 *  deliberate and it is the point of the page: the whole argument here is that an
 *  appropriation is not what a thing costs, and the only way to show that is to put the
 *  two side by side. Nothing on this page feeds a projection — audit_provenance.py fails
 *  the build if it ever does. */
export function Athletics({ onJump }: { onJump: (t: Tab) => void }) {
  const [showAll, setShowAll] = useState(false)
  return (
    <div className="mx-auto max-w-6xl px-5 pt-14 pb-16">
      <p className="text-xs font-semibold uppercase tracking-widest mb-3"
        style={{ color: 'var(--text-muted)' }}>Context, not a projection</p>
      <h1 className="text-4xl sm:text-5xl font-bold tracking-tight leading-[1.05] max-w-3xl">
        Athletics, both sides of the money
      </h1>
      <p className="mt-5 text-lg leading-relaxed max-w-2xl"
        style={{ color: 'var(--text-secondary)' }}>
        Every other page here measures what the town appropriates, because that is what the
        district publishes. Athletics is the one place we can see the other side too &mdash;
        the fee-funded revolving account that pays for a large part of it and appears in no
        budget line anywhere.
      </p>
      <p className="mt-4 text-[15px] leading-relaxed max-w-2xl"
        style={{ color: 'var(--text-secondary)' }}>
        This page is here to explain where the money comes from. It changes no number
        anywhere else on this site, and it is the only page that shows actual spending
        rather than budgets.
      </p>

      <div className="mt-10 grid gap-4">
        <TransportFocus />
        <Distribution />
        <SideTable side="general" title="General fund appropriation"
          rows={H.rows}
          note={<>What Town Meeting funds. FY14&ndash;FY19 from the FY19 athletics document,
            FY20&ndash;FY25 actual spending, FY26 the final budget.</>} />
        {showAll ? (
          <SideTable side="revolving" title="Chapter 658 revolving fund — where the fees go"
            rows={H.rows}
            note={<><strong>The blank years are the finding.</strong> FY20&ndash;FY23 is
              empty because nothing was published, not because the fund paid nothing.
              FY24 and FY25 carry two lines only, from a resident&rsquo;s records request
              that we have not yet been able to verify. FY26 is the fund&rsquo;s own
              year-end reconciliation, obtained by request.</>} />
        ) : (
          <button onClick={() => setShowAll(true)}
            className="card p-4 text-left text-[13px]"
            style={{ color: 'var(--text-secondary)' }}>
            <strong style={{ color: 'var(--text-primary)' }}>Show the revolving fund line
            by line →</strong> Including the four years where nobody published it.
          </button>
        )}
      </div>

      <div className="mt-10 flex flex-wrap gap-3">
        <button onClick={() => onJump('context')}
          className="text-xs font-semibold px-3 py-2 rounded-md"
          style={{ background: 'var(--surface-3)', color: 'var(--text-primary)' }}>
          ← The situation
        </button>
        <a href="/docs/analyses/athletics.md"
          className="text-xs font-semibold px-3 py-2 rounded-md"
          style={{ background: 'var(--surface-3)', color: 'var(--text-primary)' }}>
          The full analysis, with sources
        </a>
      </div>
    </div>
  )
}
