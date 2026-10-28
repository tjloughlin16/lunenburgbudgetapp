/** What the fy-breakdown tables share: the wide, sideways-scrolling frame with its cue, and the
 *  column heading's definition on hover. One copy, so the big table and the table of other funds
 *  cannot drift apart. */
import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'

const muted = { color: 'var(--text-muted)' }

/** WIDE (TJ, 26 October 2026: "make this a wide table"): out of the page's reading column to the
 *  window, less a gutter each side, centred on it -- the column is centred too.
 *  SCROLL CUE: on a narrow screen the table is wider than the window and nothing said so. A
 *  shadow on whichever edge hides columns, and a line saying more are to the right, both only
 *  while there is somewhere to scroll. */
export function WideScroll({ cue, children }: { cue: string; children: React.ReactNode }) {
  const scroller = useRef<HTMLDivElement>(null)
  const [edge, setEdge] = useState({ left: false, right: false })
  useEffect(() => {
    const el = scroller.current
    if (!el) return
    const upd = () => setEdge(e => {
      const left = el.scrollLeft > 2, right = el.scrollLeft + el.clientWidth < el.scrollWidth - 2
      return e.left === left && e.right === right ? e : { left, right }
    })
    upd()
    el.addEventListener('scroll', upd, { passive: true })
    const ro = new ResizeObserver(upd)
    ro.observe(el)
    if (el.firstElementChild) ro.observe(el.firstElementChild)
    return () => { el.removeEventListener('scroll', upd); ro.disconnect() }
  }, [])
  const shade = (side: 'left' | 'right', on: boolean) => (
    <div aria-hidden className={`pointer-events-none absolute inset-y-0 ${side}-0 w-4 transition-opacity`}
      style={{ opacity: on ? 1 : 0, background: `linear-gradient(to ${side === 'left' ? 'right' : 'left'}, rgba(0,0,0,0.16), transparent)` }} />)
  return (
    <div className="mt-3 relative left-1/2 -translate-x-1/2 w-[calc(100vw-32px)] sm:w-[calc(100vw-96px)] lg:w-[calc(100vw-160px)] max-w-[1600px]">
      {edge.right || edge.left ? (
        <button type="button" className="mb-1 text-[12.5px]" style={muted}
          onClick={() => scroller.current?.scrollBy({ left: (edge.right ? 1 : -1) * scroller.current.clientWidth * 0.8, behavior: 'smooth' })}>
          {edge.right ? `${cue} →` : `← ${cue}`}</button>) : null}
      <div className="relative">
        <div ref={scroller} className="overflow-x-auto">{children}</div>
        {shade('left', edge.left)}{shade('right', edge.right)}
      </div>
    </div>)
}

/** A column heading's definition, on hover or on tapping its ⓘ. */
export function HeadTip({ label, means, children }: { label: string; means: string; children: React.ReactNode }) {
  const [on, setOn] = useState(false)
  const [at, setAt] = useState<{ top: number; left: number } | null>(null)
  const el = useRef<HTMLSpanElement>(null)
  const timer = useRef<number | undefined>(undefined)
  const enter = () => { window.clearTimeout(timer.current); setOn(true) }
  const leave = () => { window.clearTimeout(timer.current); timer.current = window.setTimeout(() => setOn(false), 150) }
  useEffect(() => () => window.clearTimeout(timer.current), [])
  useEffect(() => {
    if (!on || !el.current) return
    const b = el.current.getBoundingClientRect()
    const w = Math.min(280, window.innerWidth - 16)
    setAt({ top: b.bottom + 6, left: Math.max(8, Math.min(b.right - w, window.innerWidth - w - 8)) })
    const close = () => setOn(false)
    window.addEventListener('scroll', close, { passive: true, capture: true })
    return () => window.removeEventListener('scroll', close, { capture: true } as EventListenerOptions)
  }, [on])
  return (
    <span ref={el} className="inline" onMouseEnter={enter} onMouseLeave={leave}>
      {children}
      <button type="button" aria-label={label} aria-expanded={on} className="ml-1 align-baseline text-[11px]" style={muted}
        onClick={e => { e.stopPropagation(); setOn(o => !o) }} onFocus={enter} onBlur={() => setOn(false)}>ⓘ</button>
      {on && at ? createPortal(
        <span role="tooltip" onMouseEnter={enter} onMouseLeave={leave}
          className="fixed z-50 w-[280px] max-w-[calc(100vw-16px)] px-2.5 py-2 rounded text-left text-[12.5px] leading-snug shadow whitespace-normal"
          style={{ top: at.top, left: at.left, background: 'var(--surface-1)', border: '1px solid var(--grid)', color: 'var(--text-primary)', fontWeight: 400 }}>
          <span className="block font-semibold mb-0.5">{label}</span>{means}</span>, document.body) : null}
    </span>)
}

// the weekly chart's colours, by payer, so a fund is one colour across the page
export const PAYER = { gf: 'var(--thread-1)', idea: 'var(--thread-2)', grants: 'var(--thread-5)', cb: 'var(--thread-4)',
  fees: 'var(--thread-3)', other: 'var(--thread-6, var(--text-secondary))' } as Record<string, string>
export const hatch = (c: string) => `repeating-linear-gradient(135deg, ${c} 0 3px, transparent 3px 6px)`

/** A chart row: its label and a line under it on the left, the chart beside it (stacked on a phone). */
export function Row({ label, sub, children }: { label: string; sub?: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col sm:flex-row sm:items-center gap-x-3 py-1">
      <div className="sm:w-56 shrink-0 text-[13px] leading-tight">{label}
        {sub ? <span className="block text-[11.5px]" style={muted}>{sub}</span> : null}</div>
      {children}
    </div>)
}

/** A popup's table: column headers that sort (click again to reverse), a text filter over every
 *  column, and an optional filter by one column's values. TJ, 27 October 2026: "every posting
 *  needs column headers, filters, and sorting". Cells are display text; `sort` holds what a column
 *  sorts by when that is not its text (a date's ISO form, an amount's number). */
export type STCol = { key: string; label: string; right?: boolean; wide?: boolean }
export type STRow = { cells: Record<string, React.ReactNode>; text: string; sort: Record<string, string | number> }
export function SortTable({ cols, rows, filter, count, pick, pickAll, first }: {
  cols: STCol[]; rows: STRow[]; filter: string; count: string
  pick?: { key: string; values: string[] }; pickAll?: string; first?: { key: string; dir: 1 | -1 } }) {
  const [q, setQ] = useState('')
  const [only, setOnly] = useState('')
  const [sort, setSort] = useState<{ key: string; dir: 1 | -1 } | null>(first ?? null)
  const shown = (() => {
    const ql = q.trim().toLowerCase()
    const out = rows.filter(r => (!ql || r.text.toLowerCase().includes(ql)) && (!only || !pick || r.sort[pick.key] === only))
    if (!sort) return out
    return [...out].sort((a, b) => {
      const x = a.sort[sort.key], y = b.sort[sort.key]
      return sort.dir * (typeof x === 'number' && typeof y === 'number' ? x - y : String(x).localeCompare(String(y)))
    })
  })()
  const sel = { borderColor: 'var(--grid)', background: 'var(--surface-1)', color: 'var(--text-primary)' }
  return (
    <div>
      <div className="flex flex-wrap gap-2 mb-2">
        <input value={q} onChange={e => setQ(e.target.value)} placeholder={filter} aria-label={filter}
          className="w-full max-w-sm px-2 py-1 rounded border text-[13px]" style={sel} />
        {pick && pick.values.length > 1 ? (
          <select value={only} onChange={e => setOnly(e.target.value)} className="px-2 py-1 rounded border text-[13px]" style={sel} aria-label={pickAll}>
            <option value="">{pickAll}</option>
            {pick.values.map(v => <option key={v} value={v}>{v}</option>)}
          </select>) : null}
      </div>
      <p className="text-[12px] mb-1" style={muted}>{shown.length} · {count}</p>
      <div className="overflow-x-auto">
        <table className="w-full text-[12.5px] tabular-nums border-collapse">
          <thead>
            <tr className="border-b" style={{ borderColor: 'var(--grid)' }}>
              {cols.map(c => (
                <th key={c.key} className={`px-1.5 py-1 font-semibold whitespace-nowrap cursor-pointer select-none ${c.right ? 'text-right' : 'text-left'}`}
                  onClick={() => setSort(s => ({ key: c.key, dir: s?.key === c.key ? (s.dir === 1 ? -1 : 1) : (c.right ? -1 : 1) }))}>
                  {c.label}{sort?.key === c.key ? (sort.dir < 0 ? ' ↓' : ' ↑') : ''}</th>))}
            </tr>
          </thead>
          <tbody>
            {shown.map((r, i) => (
              <tr key={i} className="border-b align-top" style={{ borderColor: 'var(--grid)' }}>
                {cols.map(c => <td key={c.key} className={`px-1.5 py-1 ${c.right ? 'text-right whitespace-nowrap font-semibold' : ''} ${c.wide ? 'min-w-[12rem]' : ''}`}>{r.cells[c.key]}</td>)}
              </tr>))}
          </tbody>
        </table>
      </div>
    </div>)
}
