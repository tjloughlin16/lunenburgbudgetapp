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
