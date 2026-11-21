/** EVERY REQUEST, EVERY YEAR (the capital-rankings hub's signature).
 *
 *  TJ, 20 November 2026: the table is FULL, no pruning -- "all items by FY in priority order. a LINE
 *  connects the FY items visually ... it should look like a table with the connected info drawn".
 *  So: one column per fiscal year, each the whole list in the Capital Planning Committee's order,
 *  one fixed-height row per rank; and a drawing layer UNDER the cells joining the same project
 *  across years. Because the cells are opaque, a line shows only in the gutters, and one that skips
 *  a year passes visibly behind that year's column. A split (one request becoming three) is three
 *  lines from one cell. Solid: the town's own project number joins them; dashed: we joined them by
 *  name (scripts/build_capital_rankings.py LINKS). Below each year's ranked list, in dotted cells,
 *  the requests departments made for that year that the committee never ranked (status_text says
 *  what happened: dropped, withdrawn, moved), joined to the years they were ranked.
 *
 *  Fixed row height is the point of the layout: every line's end is arithmetic on (column, slot),
 *  so nothing is measured after render and nothing reflows. Each column's dashed rule sits above its
 *  highest-ranked unfunded request, as on the year pages' ranked list. Hover or tap a request to
 *  light its whole thread. Every figure is formatted by the generator. On a phone the figure
 *  scrolls sideways inside itself. */
import { useState } from 'react'
import type { CustomProps } from './index'

type Cell = { gap: true } | {
  gap?: false; project: string; rank_text: string | null; amount_text: string; funded: boolean
  dept: string; thread: number | null
  never?: boolean; status_text?: string   // asked for that year, never on the committee's list
}
type Col = { label: string; count_text: string; cells: Cell[]; cut: number | null }
type Line = { a: [number, number]; b: [number, number]; ours: boolean; thread: number }
type Data = {
  columns: Col[]; lines: Line[]; note: string
  text: { funded: string; unfunded: string; town: string; ours: string; cut: string; gap: string; unranked: string; hint: string; never?: string }
}

const COLW = 172, GAP = 40, ROWH = 38, HEAD = 44, PAD = 3
const FUNDED = 'var(--thread-1)'
const UNFUNDED = 'var(--thread-2)'

export default function CapitalThreadTable({ data, alt }: CustomProps) {
  const d = data as Data
  // Hover follows the pointer exactly: entering any request replaces the last one, and leaving a
  // request clears it. A request on no thread lights only itself and fades nothing.
  const [hover, setHover] = useState<number | null>(null)
  const [here, setHere] = useState<string | null>(null)
  const [pinned, setPinned] = useState<number | null>(null)
  const active = here !== null && hover === null ? null : hover ?? pinned
  const rows = Math.max(...d.columns.map(c => c.cells.length))
  const W = d.columns.length * COLW + (d.columns.length - 1) * GAP
  const H = HEAD + rows * ROWH
  const x0 = (c: number) => c * (COLW + GAP)
  const yc = (s: number) => HEAD + s * ROWH + ROWH / 2
  const lit = (t: number | null) => active === null || t === active
  return (
    <figure className="my-2 w-full max-w-full min-w-0" aria-label={alt}>
      <div className="flex flex-wrap gap-x-4 gap-y-1 mb-2 text-[12.5px]" style={{ color: 'var(--text-secondary)' }}>
        <span className="inline-flex items-center gap-1.5">
          <span className="inline-block w-4 h-3 rounded-sm" style={{ background: `color-mix(in srgb, ${FUNDED} 16%, var(--surface-1))`, borderLeft: `3px solid ${FUNDED}` }} />{d.text.funded}</span>
        <span className="inline-flex items-center gap-1.5">
          <span className="inline-block w-4 h-3 rounded-sm" style={{ border: '1px solid var(--grid)', borderLeft: `3px solid ${UNFUNDED}` }} />{d.text.unfunded}</span>
        <span className="inline-flex items-center gap-1.5">
          <svg width="22" height="6"><line x1="0" y1="3" x2="22" y2="3" stroke="var(--text-secondary)" strokeWidth="1.6" /></svg>{d.text.town}</span>
        <span className="inline-flex items-center gap-1.5">
          <svg width="22" height="6"><line x1="0" y1="3" x2="22" y2="3" stroke="var(--text-secondary)" strokeWidth="1.6" strokeDasharray="4 3" /></svg>{d.text.ours}</span>
        <span className="inline-flex items-center gap-1.5">
          <svg width="22" height="6"><line x1="0" y1="3" x2="22" y2="3" stroke="var(--status-warning)" strokeWidth="1.6" strokeDasharray="5 3" /></svg>{d.text.cut}</span>
        {d.text.never ? (
          <span className="inline-flex items-center gap-1.5">
            <span className="inline-block w-4 h-3 rounded-sm" style={{ border: '1px dotted var(--text-muted)' }} />{d.text.never}</span>
        ) : null}
      </div>
      <p className="text-[12px] mb-2" style={{ color: 'var(--text-muted)' }}>{d.text.hint}</p>
      <div className="overflow-x-auto -mx-1 px-1 pb-2">
        <div className="relative" style={{ width: W, height: H }} onMouseLeave={() => { setHover(null); setHere(null) }}>
          <svg className="absolute inset-0" width={W} height={H} aria-hidden="true" style={{ zIndex: 0 }}>
            {d.lines.map((l, i) => {
              const x1 = x0(l.a[0]) + COLW, y1 = yc(l.a[1]), x2 = x0(l.b[0]), y2 = yc(l.b[1])
              const k = Math.min(GAP * 0.9, (x2 - x1) / 2)
              const on = active !== null && l.thread === active
              return (
                <path key={i} d={`M${x1},${y1} C${x1 + k},${y1} ${x2 - k},${y2} ${x2},${y2}`} fill="none"
                  stroke={on ? 'var(--text-primary)' : 'var(--text-secondary)'} strokeWidth={on ? 2.4 : 1.5}
                  strokeDasharray={l.ours ? '5 4' : undefined} opacity={lit(l.thread) ? (on ? 1 : 0.75) : 0.12} />)
            })}
          </svg>
          {d.columns.map((c, ci) => (
            <div key={c.label}>
              <div className="absolute" style={{ left: x0(ci), top: 0, width: COLW, height: HEAD, zIndex: 1 }}>
                <p className="text-[14px] font-semibold" style={{ color: 'var(--text-primary)' }}>{c.label}</p>
                <p className="text-[11.5px]" style={{ color: 'var(--text-muted)' }}>{c.count_text}</p>
              </div>
              {c.cells.map((cell, s) => {
                const style: React.CSSProperties = { left: x0(ci), top: HEAD + s * ROWH + PAD / 2, width: COLW, height: ROWH - PAD, zIndex: 1 }
                if (cell.gap) return (
                  <div key={s} className="absolute rounded-sm flex items-center px-2 text-[11px] italic"
                    style={{ ...style, background: 'var(--surface-1)', border: '1px dashed var(--grid)', color: 'var(--text-muted)' }}>
                    {d.text.gap}</div>)
                const t = cell.thread
                const key = `${ci}-${s}`
                const on = (active !== null && t === active) || here === key
                return (
                  <button key={s} type="button" title={`${cell.project} · ${cell.dept} · ${cell.amount_text}${cell.status_text ? ' · ' + cell.status_text : ''}`}
                    className="absolute rounded-sm text-left px-2 py-[3px] overflow-hidden"
                    onMouseEnter={() => { setHover(t); setHere(key) }}
                    onMouseLeave={() => { setHover(null); setHere(null) }}
                    onFocus={() => { setHover(t); setHere(key) }}
                    onBlur={() => { setHover(null); setHere(null) }}
                    onClick={() => setPinned(t === null || pinned === t ? null : t)}
                    style={{
                      ...style, cursor: t !== null ? 'pointer' : 'default',
                      background: cell.funded ? `color-mix(in srgb, ${FUNDED} 16%, var(--surface-1))` : 'var(--surface-1)',
                      border: `1px ${cell.never ? 'dotted' : 'solid'} ${on ? 'var(--text-primary)' : cell.never ? 'var(--text-muted)' : 'var(--grid)'}`,
                      borderLeft: cell.never ? `1px dotted ${on ? 'var(--text-primary)' : 'var(--text-muted)'}` : `3px solid ${cell.funded ? FUNDED : UNFUNDED}`,
                      opacity: lit(t) ? 1 : 0.35,
                    }}>
                    <span className="block truncate text-[12px] leading-tight" style={{ color: 'var(--text-primary)', fontWeight: t !== null ? 600 : 400 }}>{cell.project}</span>
                    <span className="block text-[11px] leading-tight tabular-nums mt-[2px]" style={{ color: 'var(--text-muted)' }}>
                      {cell.rank_text ?? cell.status_text ?? d.text.unranked} · {cell.amount_text}</span>
                  </button>)
              })}
              {c.cut !== null ? (
                <div className="absolute pointer-events-none" style={{ left: x0(ci) - 4, top: HEAD + c.cut * ROWH - 1, width: COLW + 8, borderTop: '2px dashed var(--status-warning)', zIndex: 2 }} />
              ) : null}
            </div>))}
        </div>
      </div>
      <figcaption className="mt-2 text-[12.5px]" style={{ color: 'var(--text-muted)' }}>{d.note}</figcaption>
    </figure>
  )
}
