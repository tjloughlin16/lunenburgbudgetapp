import { useMemo, useState } from 'react'
import { ChipGrid, type Row } from './ChipGrid'
import { MODEL, expand, usd, usdShort } from '../model/engine'
import { StatusBadge } from './primitives'

export interface Tick { fy: number; cumulative: number }

/** The slider: how big a hole must be closed, and what falls below the line to close it. */
export function CutLine({ order, target, setTarget, ticks, max }: {
  order: string[]
  target: number
  setTarget: (n: number) => void
  ticks: Tick[]
  max: number
}) {
  const [view, setView] = useState<'chips' | 'list'>('chips')
  const rank = useMemo(() => new Map(order.map((c, i) => [c, i])), [order])

  const pool = useMemo(() => expand(MODEL.programs)
    .filter(p => p.status === 'funded' || p.status === 'restoring')
    .sort((a, b) =>
      (rank.get(b.cat) ?? 99) - (rank.get(a.cat) ?? 99)
      || a.tier - b.tier || a.cost - b.cost), [rank])

  // Walk the ordered pool, cutting until the target is met. Legally mandated
  // programs are skipped rather than cut.
  const { rows, cutTotal, fteLost, unclosed } = useMemo(() => {
    let remaining = target, total = 0, fte = 0
    const rows: Row[] = pool.map(p => {
      if (remaining <= 0) return { p, state: 'kept' as const }
      if (p.mandate === 'legal') return { p, state: 'mandated' as const }
      remaining -= p.cost; total += p.cost; fte += p.fte
      return { p, state: 'cut' as const }
    })
    return { rows, cutTotal: total, fteLost: fte, unclosed: Math.max(0, remaining) }
  }, [pool, target])

  const reached = ticks.filter(t => t.cumulative <= target).at(-1)

  return (
    <div>
      {/* ---- the slider ---- */}
      <div className="card p-5 mb-6 sticky top-12 z-10"
        style={{ background: 'var(--surface-1)' }}>
        <div className="flex flex-wrap items-end justify-between gap-4 mb-4">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-widest mb-1"
              style={{ color: 'var(--text-muted)' }}>Budget hole to close</p>
            <p className="text-4xl font-bold tnum leading-none"
              style={{ color: 'var(--status-critical)' }}>{usd(target)}</p>
          </div>
          <div className="text-right">
            <p className="text-[11px] font-semibold uppercase tracking-widest mb-1"
              style={{ color: 'var(--text-muted)' }}>Staff positions lost</p>
            <p className="text-4xl font-bold tnum leading-none">{fteLost.toFixed(1)}</p>
          </div>
        </div>

        <input type="range" min={0} max={max} step={5000} value={target}
          aria-label="Size of the budget gap to close"
          onChange={e => setTarget(Number(e.target.value))}
          className="w-full" />

        <div className="relative h-12 mt-1">
          {ticks.map(t => (
            <button key={t.fy}
              onClick={() => setTarget(t.cumulative)}
              className="absolute -translate-x-1/2 text-center group"
              style={{ left: `${Math.min(100, (t.cumulative / max) * 100)}%` }}>
              <span className="block w-px h-2 mx-auto" style={{ background: 'var(--axis)' }} />
              <span className="block text-[10px] font-bold tnum mt-0.5"
                style={{ color: target >= t.cumulative ? 'var(--status-critical)' : 'var(--text-muted)' }}>
                FY{t.fy}
              </span>
              <span className="block text-[9px] tnum" style={{ color: 'var(--text-muted)' }}>
                {usdShort(t.cumulative)}
              </span>
            </button>
          ))}
        </div>

        <p className="text-[13px] leading-relaxed pt-3 border-t"
          style={{ color: 'var(--text-secondary)', borderColor: 'var(--grid)' }}>
          {reached
            ? <>At this size, the hole matches the shortfall projected{' '}
              <strong>{reached.fy === ticks[0].fy
                ? `for FY${reached.fy}`
                : `cumulatively through FY${reached.fy}`}</strong> — {usd(cutTotal)} of
              programs fall below the cut line, costing {fteLost.toFixed(1)} staff
              positions.</>
            : <>Below the first projected shortfall. Drag right, or pick a year marker.</>}
          {unclosed > 0 && (
            <> <strong style={{ color: 'var(--status-critical)' }}>
              {usd(unclosed)} cannot be closed</strong> — everything legally cuttable is
              already gone.</>
          )}
        </p>
      </div>

      {/* ---- everything at a glance, then the detail on demand ---- */}
      <div className="flex items-center justify-between gap-3 mb-3">
        <h3 className="text-sm font-bold">
          {rows.filter(r => r.state === 'cut').length} of {rows.length} programs below the line
        </h3>
        <div className="flex gap-1">
          {(['chips', 'list'] as const).map(v => (
            <button key={v} onClick={() => setView(v)}
              className="px-2.5 py-1 rounded-md text-[11px] font-semibold border"
              style={{
                borderColor: view === v ? 'var(--series-cost)' : 'var(--grid)',
                background: view === v ? 'var(--series-cost)' : 'var(--surface-1)',
                color: view === v ? '#fff' : 'var(--text-secondary)',
              }}>
              {v === 'chips' ? 'All at once' : 'Full detail'}
            </button>
          ))}
        </div>
      </div>

      {view === 'chips' ? <ChipGrid rows={rows} /> : <ProgramList rows={rows} />}
    </div>
  )
}

const KEPT_PREVIEW = 4

function ProgramList({ rows }: { rows: Row[] }) {
  const [showAll, setShowAll] = useState(false)
  const firstKept = rows.findIndex(r => r.state === 'kept')
  const hiddenCount = firstKept === -1 ? 0
    : Math.max(0, rows.length - firstKept - KEPT_PREVIEW)
  const visible = showAll || hiddenCount === 0
    ? rows
    : rows.slice(0, firstKept + KEPT_PREVIEW)

  let lineDrawn = false
  return (
    <>
    <ul className="space-y-1">
      {visible.map(({ p, state }, i) => {
        const drawLine = !lineDrawn && state === 'kept' && i > 0
        if (drawLine) lineDrawn = true
        return (
          <li key={p.id}>
            {drawLine && (
              <div className="flex items-center gap-3 my-3" aria-hidden="true">
                <span className="h-px flex-1" style={{ background: 'var(--status-critical)' }} />
                <span className="text-[10px] font-bold uppercase tracking-widest"
                  style={{ color: 'var(--status-critical)' }}>The cut line</span>
                <span className="h-px flex-1" style={{ background: 'var(--status-critical)' }} />
              </div>
            )}
            <div className="card px-3.5 py-2.5 flex items-start gap-3"
              style={{ opacity: state === 'cut' ? 0.55 : 1 }}>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium leading-snug"
                  style={{ textDecoration: state === 'cut' ? 'line-through' : 'none' }}>
                  {p.name}
                </p>
                <p className="text-xs mt-0.5 leading-snug" style={{ color: 'var(--text-secondary)' }}>
                  {p.impact}
                </p>
                <p className="text-[10px] mt-1 uppercase tracking-wider font-semibold"
                  style={{ color: 'var(--text-muted)' }}>
                  {MODEL.categories[p.cat]?.label}
                  {p.source === 'EST' && ' · our estimate, not a district figure'}
                </p>
              </div>
              <div className="text-right shrink-0">
                <p className="text-sm font-bold tnum">{usd(p.cost)}</p>
                <StatusBadge kind={state} />
              </div>
            </div>
          </li>
        )
      })}
    </ul>
    {hiddenCount > 0 && (
      <button onClick={() => setShowAll(v => !v)}
        className="mt-3 w-full py-2.5 rounded-lg text-xs font-semibold border"
        style={{ borderColor: 'var(--grid)', color: 'var(--text-secondary)',
                 background: 'var(--surface-1)' }}>
        {showAll
          ? 'Collapse the list'
          : `Show ${hiddenCount} more programs still funded at this level`}
      </button>
    )}
    </>
  )
}
