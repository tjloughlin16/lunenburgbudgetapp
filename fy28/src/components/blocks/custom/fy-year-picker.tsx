/** THE PAGE'S FISCAL YEAR (fy-breakdown): one row of chips that sets the year for every chart on
 *  the page (fy-year.ts). Once it scrolls out of view a compact copy is pinned under the site
 *  header, so the year can be changed from anywhere on the page. (A CSS `sticky` cannot do it:
 *  sticky holds an element only inside its own block, and this block is the picker alone.) */
import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import type { CustomProps } from './index'
import { useFyYear } from './fy-year'

type Data = { years: string[]; label: string }

function Chips({ d, fy, setFy, small }: { d: Data; fy: string; setFy: (v: string) => void; small?: boolean }) {
  return (
    <>
      <span className={`${small ? 'text-[12px]' : 'text-[13px]'} font-semibold mr-1`}>{d.label}</span>
      {d.years.map(v => {
        const on = v === fy
        return (
          <button key={v} type="button" onClick={() => setFy(v)} aria-pressed={on}
            className={`${small ? 'px-2.5 py-0.5 text-[12.5px]' : 'px-3 py-1 text-[13.5px]'} rounded-full border leading-tight`}
            style={{ borderColor: on ? 'var(--text-secondary)' : 'var(--grid)', color: on ? 'var(--text-primary)' : 'var(--text-muted)',
              background: on ? 'var(--surface-2)' : 'transparent', fontWeight: on ? 600 : 400 }}>{v}</button>)
      })}
    </>)
}

export default function FyYearPicker({ data, alt }: CustomProps) {
  const d = data as Data
  const [fy, setFy] = useFyYear(d.years)
  const box = useRef<HTMLDivElement>(null)
  const [away, setAway] = useState(false)
  useEffect(() => {
    if (!box.current || typeof IntersectionObserver === 'undefined') return
    const io = new IntersectionObserver(([e]) => setAway(!e.isIntersecting && e.boundingClientRect.top < 0))
    io.observe(box.current)
    return () => io.disconnect()
  }, [])
  return (
    <>
      <div ref={box} role="group" aria-label={alt} className="flex flex-wrap gap-1.5 items-center py-1">
        <Chips d={d} fy={fy} setFy={setFy} />
      </div>
      {away ? createPortal(
        <div role="group" aria-label={alt} className="fixed left-1/2 -translate-x-1/2 top-[52px] z-40 px-3 py-1.5 rounded-full shadow flex flex-wrap gap-1 items-center max-w-[calc(100vw-16px)]"
          style={{ background: 'var(--surface-1, var(--bg))', border: '1px solid var(--grid)' }}>
          <Chips d={d} fy={fy} setFy={setFy} small />
        </div>, document.body) : null}
    </>)
}
