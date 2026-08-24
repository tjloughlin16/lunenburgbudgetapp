import { useState } from 'react'
import { usd, usdShort } from '../model/engine'
import { BEARERS } from '../model/answers'
import { TARGETS, targetYear, verdict, type PriceRow } from '../model/price'

/** The price list: one target, every lever, what each one takes.
 *
 *  Laid out as a stack of cards rather than a table on purpose. A table invites reading
 *  down one column — "which is cheapest" — and the honest answer is not in any single
 *  column; it is in how many rows say "not possible". So each lever gets the same block
 *  in the same shape, and the ceiling bar is the thing the eye catches.
 *
 *  Everything here is arithmetic on this year. Nothing on this page compounds. */
export function PriceList() {
  const [target, setTarget] = useState(TARGETS[0])
  const v = verdict(target)
  const year = targetYear(target)

  return (
    <div>
      <div className="flex flex-wrap items-center gap-2 mb-5">
        <span className="text-[11px] font-semibold uppercase tracking-widest mr-1"
          style={{ color: 'var(--text-muted)' }}>Find</span>
        {TARGETS.map(t => (
          <button key={t} onClick={() => setTarget(t)}
            aria-pressed={t === target}
            className="text-[13px] font-bold tnum px-3 py-1.5 rounded-md border transition-colors"
            style={t === target
              ? { background: 'var(--text-primary)', color: 'var(--surface-1)',
                  borderColor: 'var(--text-primary)' }
              : { background: 'var(--surface-1)', color: 'var(--text-secondary)',
                  borderColor: 'var(--grid)' }}>
            {t >= 1e6 ? `$${(t / 1e6).toFixed(t % 1e6 ? 1 : 0)}M` : `$${t / 1e3}k`}
          </button>
        ))}
      </div>

      <div className="card p-4 sm:p-5 mb-6">
        <p className="text-[15px] leading-relaxed">
          <strong>{usd(target)}</strong> is {year.over ? 'past ' : ''}roughly where this
          lands in <strong>FY{year.fy}</strong>. Of the {v.rows.length} levers anyone has
          proposed, <strong style={{ color: v.reachable.length > 3
            ? 'var(--text-primary)' : 'var(--status-critical)' }}>
            {v.reachable.length}</strong> can produce it on their own.
          The other {v.short.length} cannot, at any price, in any year.
        </p>
      </div>

      <div className="space-y-8">
        {BEARERS.map(b => {
          const rows = v.rows.filter(r => r.bears === b.id)
          if (!rows.length) return null
          return (
            <div key={b.id}>
              <div className="mb-3">
                <h3 className="text-[15px] font-bold">{b.label}</h3>
                <p className="text-[12px]" style={{ color: 'var(--text-muted)' }}>{b.sub}</p>
              </div>
              <div className="grid gap-3 lg:grid-cols-2 items-start">
                {rows.map(r => <Row key={r.id} row={r} target={target} />)}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

/** One lever, priced. Same six parts every time, whether or not it works. */
function Row({ row, target }: { row: PriceRow; target: number }) {
  const tone = row.reachable ? 'var(--text-primary)' : 'var(--status-critical)'
  const reach = row.ceiling === null ? null : Math.min(1, row.ceiling / target)

  return (
    <div className="card p-4 flex flex-col">
      <div className="flex items-baseline justify-between gap-3 mb-2">
        <p className="text-[13px] font-semibold leading-snug min-w-0">{row.label}</p>
        <span aria-hidden="true" className="text-[13px] font-bold shrink-0" style={{ color: tone }}>
          {row.reachable ? '✓' : '✕'}
        </span>
      </div>

      <p className="text-[17px] font-bold leading-snug" style={{ color: tone }}>{row.ask}</p>
      <p className="text-[13px] leading-relaxed mt-1.5" style={{ color: 'var(--text-secondary)' }}>
        {row.detail}
      </p>

      {/* The names, at full size. A count of things cut is an abstraction; the list is
          the fact. This sits above the ceiling bar deliberately — it is the part of the
          card a reader should not be able to skip. */}
      {row.items && (
        <ul className="mt-3 rounded-lg overflow-hidden" style={{ background: 'var(--surface-3)' }}>
          {row.items.map((it, i) => (
            <li key={it.label + i}
              className="flex items-baseline justify-between gap-3 px-3 py-2"
              style={i ? { borderTop: '1px solid var(--grid)' } : undefined}>
              <span className="text-[13px] leading-snug min-w-0">{it.label}</span>
              <span className="text-[13px] font-semibold tnum shrink-0"
                style={{ color: 'var(--text-secondary)' }}>{usd(it.amount)}</span>
            </li>
          ))}
        </ul>
      )}

      {/* How far the lever gets, for the ones with a hard stop. The bar is the argument:
          a fee that reaches a third of the way is not a small version of a solution. */}
      {reach !== null && (
        <div className="mt-3">
          <div className="h-1.5 rounded-full overflow-hidden" style={{ background: 'var(--surface-3)' }}>
            <div className="h-full rounded-full" style={{
              width: `${Math.max(reach * 100, 1)}%`,
              background: row.reachable ? 'var(--status-good)' : 'var(--status-critical)',
            }} />
          </div>
          <p className="text-[11px] mt-1.5" style={{ color: 'var(--text-muted)' }}>
            {row.reachable
              ? `Ceiling ${usdShort(row.ceiling!)}. ${row.ceilingNote}.`
              : `Gets you ${Math.round(reach * 100)}% of the way. ${row.ceilingNote}.`}
          </p>
        </div>
      )}

      {/* Not a footnote. A card that overlaps another one, or that quietly loses revenue
          when you take the saving, is misleading at a glance — so this sits in the body
          with a rule beside it rather than in muted grey underneath. */}
      {row.caveat && (
        <p className="text-[12px] leading-relaxed mt-3 pl-3"
          style={{ borderLeft: '3px solid var(--status-warning)',
                   color: 'var(--text-secondary)' }}>
          {row.caveat}
        </p>
      )}

      <p className="text-[11px] leading-relaxed mt-3 pt-2.5 border-t tnum"
        style={{ borderColor: 'var(--grid)', color: 'var(--text-muted)' }}>
        <span className="font-semibold">Check it: </span>{row.math}
      </p>
    </div>
  )
}
