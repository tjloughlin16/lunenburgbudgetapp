/** THE PAGE'S FISCAL YEAR (fy-breakdown). The year picked is drawn as part of the page's title,
 *  large, with the dates it covers, and it pops when it changes -- TJ, 27 October 2026: "call out
 *  the SELECTED ONE as if its part of the title or subtitle. so when users change it, it POPS
 *  that its for a new FY vs just being a selected tab". The chips beside it set the year for
 *  every chart on the page (fy-year.ts). Once it scrolls out of view a compact copy is pinned
 *  under the site header. (CSS `sticky` cannot do that: it holds an element only inside its own
 *  block, and this block is the picker alone.) */
import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import type { CustomProps } from './index'
import { useFyYear } from './fy-year'

type Data = { years: string[]; label: string; spans: Record<string, string> }

/** A short emphasis when the year changes: grows a little and settles, in the accent colour. */
function usePop<T extends HTMLElement>(dep: string) {
  const el = useRef<T>(null)
  const first = useRef(true)
  useEffect(() => {
    if (first.current) { first.current = false; return }
    if (!el.current || typeof el.current.animate !== 'function') return
    if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return
    el.current.animate([
      { transform: 'scale(1.12)', color: 'var(--link, var(--thread-2))' },
      { transform: 'scale(1)', color: 'var(--text-primary)' }],
    { duration: 550, easing: 'cubic-bezier(.2,.8,.2,1)' })
  }, [dep])
  return el
}

function Chips({ d, fy, setFy, small }: { d: Data; fy: string; setFy: (v: string) => void; small?: boolean }) {
  return (
    <>
      {d.years.map(v => {
        const on = v === fy
        return (
          <button key={v} type="button" onClick={() => setFy(v)} aria-pressed={on}
            className={`${small ? 'px-2.5 py-0.5 text-[12.5px]' : 'px-3 py-1 text-[13px]'} rounded-full border leading-tight`}
            style={{ borderColor: on ? 'var(--text-secondary)' : 'var(--grid)', color: on ? 'var(--text-primary)' : 'var(--text-muted)',
              background: on ? 'var(--surface-2)' : 'transparent', fontWeight: on ? 600 : 400 }}>{v}</button>)
      })}
    </>)
}

export default function FyYearPicker({ data, alt }: CustomProps) {
  const d = data as Data
  const [fy, setFy] = useFyYear(d.years)
  const box = useRef<HTMLDivElement>(null)
  const big = usePop<HTMLSpanElement>(fy)
  const small = usePop<HTMLSpanElement>(fy)
  const [away, setAway] = useState(false)
  useEffect(() => {
    if (!box.current || typeof IntersectionObserver === 'undefined') return
    const io = new IntersectionObserver(([e]) => setAway(!e.isIntersecting && e.boundingClientRect.top < 0))
    io.observe(box.current)
    return () => io.disconnect()
  }, [])
  return (
    <>
      <div ref={box} role="group" aria-label={alt} className="flex flex-wrap items-end justify-between gap-x-6 gap-y-2 pb-3 border-b" style={{ borderColor: 'var(--grid)' }}>
        <div aria-live="polite">
          <span ref={big} className="inline-block origin-left text-[40px] sm:text-[48px] font-bold leading-none tracking-tight tabular-nums">{fy}</span>
          <span className="block text-[14px] mt-1.5" style={{ color: 'var(--text-secondary)' }}>{d.spans[fy]}</span>
        </div>
        <div className="flex flex-wrap gap-1.5 items-center">
          <span className="text-[12px] mr-0.5" style={{ color: 'var(--text-muted)' }}>{d.label}</span>
          <Chips d={d} fy={fy} setFy={setFy} />
        </div>
      </div>
      {away ? createPortal(
        <div role="group" aria-label={alt} className="fixed left-1/2 -translate-x-1/2 top-[52px] z-40 pl-4 pr-2 py-1.5 rounded-full shadow flex flex-wrap gap-1 items-center max-w-[calc(100vw-16px)]"
          style={{ background: 'var(--surface-1, var(--bg))', border: '1px solid var(--grid)' }}>
          <span ref={small} className="inline-block text-[15px] font-bold mr-2 tabular-nums">{fy}</span>
          <Chips d={d} fy={fy} setFy={setFy} small />
        </div>, document.body) : null}
    </>)
}
