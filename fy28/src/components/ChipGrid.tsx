import { useState } from 'react'
import { MODEL, usd, type Program } from '../model/engine'
import { StatusBadge } from './primitives'

export type Row = { p: Program; state: 'kept' | 'cut' | 'mandated' }

/** Every program on one screen, so the slider's effect is visible without scrolling. */
export function ChipGrid({ rows }: { rows: Row[] }) {
  const [open, setOpen] = useState<Row | null>(null)

  const style = (s: Row['state']) =>
    s === 'cut'
      ? { background: 'color-mix(in srgb, var(--status-critical) 14%, var(--surface-1))',
          borderColor: 'var(--status-critical)', color: 'var(--text-secondary)' }
      : s === 'mandated'
      ? { background: 'color-mix(in srgb, var(--status-warning) 16%, var(--surface-1))',
          borderColor: 'var(--status-warning)', color: 'var(--text-primary)' }
      : { background: 'var(--surface-1)', borderColor: 'var(--grid)',
          color: 'var(--text-primary)' }

  return (
    <>
      <div className="flex flex-wrap gap-1.5">
        {rows.map(r => (
          <button key={r.p.id} onClick={() => setOpen(r)}
            title={`${r.p.name} — ${usd(r.p.cost)}`}
            className="text-left px-2.5 py-1.5 rounded-lg border text-[11px] leading-tight
                       max-w-[190px] transition-colors hover:opacity-80"
            style={style(r.state)}>
            <span className="block font-semibold truncate"
              style={{ textDecoration: r.state === 'cut' ? 'line-through' : 'none' }}>
              {r.p.name}
            </span>
            <span className="flex items-center gap-1.5 mt-0.5">
              <span className="tnum font-bold">{usd(r.p.cost)}</span>
              <span aria-hidden="true" style={{
                color: r.state === 'cut' ? 'var(--status-critical)'
                  : r.state === 'mandated' ? 'var(--status-warning)' : 'var(--status-good)',
              }}>
                {r.state === 'cut' ? '✕' : r.state === 'mandated' ? '⚖' : '✓'}
              </span>
            </span>
          </button>
        ))}
      </div>

      <p className="text-[11px] mt-3 flex flex-wrap gap-x-4 gap-y-1"
        style={{ color: 'var(--text-muted)' }}>
        <span><span aria-hidden="true" style={{ color: 'var(--status-good)' }}>✓ </span>Kept</span>
        <span><span aria-hidden="true" style={{ color: 'var(--status-critical)' }}>✕ </span>Cut</span>
        <span><span aria-hidden="true" style={{ color: 'var(--status-warning)' }}>⚖ </span>Protected by law — skipped, not cut</span>
        <span>Open any program for the detail.</span>
      </p>

      {open && <Detail row={open} onClose={() => setOpen(null)} />}
    </>
  )
}

function Detail({ row, onClose }: { row: Row; onClose: () => void }) {
  const { p, state } = row
  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-4"
      style={{ background: 'rgba(0,0,0,.45)' }}
      onClick={onClose} role="dialog" aria-modal="true" aria-label={p.name}>
      <div className="card w-full max-w-lg p-6" onClick={e => e.stopPropagation()}>
        <div className="flex items-start justify-between gap-4 mb-3">
          <h3 className="text-lg font-bold leading-snug">{p.name}</h3>
          <button onClick={onClose} aria-label="Close"
            className="shrink-0 w-8 h-8 rounded-lg border text-sm"
            style={{ borderColor: 'var(--grid)', color: 'var(--text-secondary)' }}>✕</button>
        </div>

        <div className="flex flex-wrap items-center gap-4 mb-4">
          <span className="text-2xl font-bold tnum">{usd(p.cost)}</span>
          {p.fte > 0 && (
            <span className="text-sm" style={{ color: 'var(--text-secondary)' }}>
              {p.fte} staff position{p.fte === 1 ? '' : 's'}
            </span>
          )}
          <StatusBadge kind={state} />
        </div>

        <p className="text-[14px] leading-relaxed mb-4">{p.impact}</p>

        <dl className="text-xs space-y-1.5 pt-3 border-t" style={{ borderColor: 'var(--grid)' }}>
          <Pair k="Category" v={MODEL.categories[p.cat]?.label ?? p.cat} />
          <Pair k="Status in the FY27 budget" v={
            p.status === 'funded' ? 'Currently funded'
              : p.status === 'restoring' ? 'Being restored at the September town meeting — one-time money'
              : p.status === 'cut' ? 'Already cut' : 'Requested but not funded'} />
          <Pair k="Can it legally be cut?" v={
            p.mandate === 'legal' ? 'No — required by state or federal law'
              : p.mandate === 'contract' ? 'Bound by collective bargaining this year'
              : 'Yes — the School Committee can cut it by vote'} />
          <Pair k="Where the figure comes from" v={
            p.source === 'EST' ? 'Our estimate — the district has not published a price for this'
              : p.source === 'ADD' ? 'District Multi-Scenario Financial Analysis, 13 Mar 2026'
              : p.source === 'ATRP' ? 'Additional Town Revenue Spending Plan'
              : 'FY27 line-item budget'} />
        </dl>
      </div>
    </div>
  )
}

function Pair({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex gap-3">
      <dt className="shrink-0 w-44" style={{ color: 'var(--text-muted)' }}>{k}</dt>
      <dd className="flex-1" style={{ color: 'var(--text-secondary)' }}>{v}</dd>
    </div>
  )
}
