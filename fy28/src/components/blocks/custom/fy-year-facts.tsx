/** THE YEAR IN FIGURES (fy-breakdown): the picked year's facts and conclusions, switched by the
 *  page's year picker (fy-year.ts). TJ, 27 October 2026: "make the facts and conclusions switch
 *  with the year". The page's own facts and conclusions, further down, compare the years and so
 *  hold whichever year is picked. Every figure is formatted by scripts/build_fy_breakdown.py. */
import { useMemo } from 'react'
import type { CustomProps } from './index'
import { useFyYear } from './fy-year'

type Fact = { v: string; label: string; estimate?: boolean }
type Con = { claim: string; so: string }
type Year = { fy: string; facts: Fact[]; conclusions: Con[] }
type Data = { years: Year[]; text: Record<'facts' | 'conclusions' | 'means' | 'estimate', string> }

const muted = { color: 'var(--text-muted)' }, secondary = { color: 'var(--text-secondary)' }

export default function FyYearFacts({ data, alt }: CustomProps) {
  const d = data as Data
  const fys = useMemo(() => d.years.map(v => v.fy), [d])
  const [fy] = useFyYear(fys)
  const y = d.years[Math.max(0, fys.indexOf(fy))]
  return (
    <div aria-label={alt} aria-live="polite" className="max-w-3xl">
      <div className="grid grid-cols-2 sm:grid-cols-4 border-t border-l" style={{ borderColor: 'var(--grid)' }}>
        {y.facts.map((f, i) => (
          <div key={i} className="p-2.5 border-r border-b" style={{ borderColor: 'var(--grid)', boxShadow: f.estimate ? 'inset 3px 0 0 var(--series-estimate, #e0a800)' : undefined }}>
            <p className="text-[19px] font-bold tabular-nums leading-tight">{f.v}</p>
            <p className="text-[12.5px] leading-snug mt-0.5" style={secondary}>{f.label}</p>
            {f.estimate ? <p className="text-[10.5px] uppercase tracking-wide mt-1" style={muted}>{d.text.estimate}</p> : null}
          </div>))}
      </div>
      <ol className="mt-5 space-y-3">
        {y.conclusions.map((c, i) => (
          <li key={i} className="grid grid-cols-[1.25rem_1fr] gap-x-1">
            <span className="text-[15px]" style={muted}>{i + 1}</span>
            <span>
              <span className="block text-[15.5px] font-semibold leading-snug">{c.claim}</span>
              <span className="block text-[14px] leading-snug mt-0.5" style={secondary}><span className="font-semibold" style={{ color: 'var(--text-primary)' }}>{d.text.means}</span> {c.so}</span>
            </span>
          </li>))}
      </ol>
    </div>)
}
