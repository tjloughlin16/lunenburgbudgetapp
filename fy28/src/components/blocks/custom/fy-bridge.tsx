/** FROM THE PLAN TO WHAT HAPPENED (fy-breakdown). A BRIDGE: the plan, then one step per reason,
 *  landing on what happened. Its own section (TJ, 27 October 2026: "It doesnt seem like a separate
 *  section"), the page's year. Every figure is formatted by scripts/build_fy_breakdown.py
 *  (plan_data), which asserts the steps land. */
import { useMemo } from 'react'
import { useFyYear } from './fy-year'
import type { CustomProps } from './index'
import { PAYER, hatch, Row } from './fy-shared'

/** `label` is the same every year; `sub` is the year's qualifier; `means` is the hover */
type Step = { id: string; n: number; v: string; label: string; sub: string; means: string }
type Year = { fy: string; bridge: Step[]; totals: { plan: number; happened: number; t: { plan: string; happened: string } } }
type Data = { years: Year[]; text: Record<string, string> }

export default function FyBridge({ data, alt }: CustomProps) {
  const d = data as Data
  const t = d.text
  const fys = useMemo(() => d.years.map(v => v.fy), [d])
  const [fy] = useFyYear(fys)
  const y = d.years[Math.max(0, fys.indexOf(fy))]
  return (
    <figure aria-label={alt}>
      {/* THE BRIDGE (TJ, 27 October 2026, of the chart it replaced -- a waterfall per source,
          each on its own baseline -- "the hardest to understand"): from the plan to what
          happened, one reason a step, every bar on one scale from zero. */}
      {(() => {
        let run = y.totals.plan
        const rows = y.bridge.map(s => { const from = run; run += s.n; return { ...s, from, to: run } })
        const ends = [y.totals.plan, ...rows.map(r => r.to)]
        // FROM ZERO (TJ: "i dont know how $3m is longer than $26m"): a bar's length is its
        // value, so the totals start at zero and the steps are drawn to the same scale
        const lo = 0, hi = Math.max(...ends) * 1.02
        const pc = (v: number) => ((v - lo) / (hi - lo)) * 100
        const total = (label: string, v: number, text: string) => (
          <Row label={label}>
            <div className="relative h-6 w-full sm:flex-1 min-w-0 shrink-0">
              <div className="absolute top-0.5 bottom-0.5 left-0 rounded-[2px]" title={`${label}: ${text}`}
                style={{ width: `${pc(v)}%`, background: 'var(--text-secondary)' }} />
              <span className="absolute top-1/2 -translate-y-1/2 text-[12.5px] tabular-nums font-semibold whitespace-nowrap"
                style={pc(v) > 70 ? { right: `${100 - pc(v)}%`, marginRight: 4, color: 'var(--surface-1, #fff)' } : { left: `${pc(v)}%`, marginLeft: 4 }}>{text}</span>
            </div>
          </Row>)
        const FILL: Record<string, string> = { gf: PAYER.gf, cb: PAYER.cb, other: 'var(--text-secondary)', none: hatch('var(--text-secondary)') }
        return (
          <div>
            {total(t.a_plan, y.totals.plan, y.totals.t.plan)}
            {rows.map(r => (
              <Row key={r.id} label={r.label} sub={r.sub} title={r.means}>
                <div className="relative h-6 w-full sm:flex-1 min-w-0 shrink-0">
                  <div className="absolute inset-y-0 w-px" style={{ left: `${pc(r.from)}%`, background: 'var(--grid)' }} />
                  {Math.abs(r.n) > 0.5 ? <div className="absolute top-0.5 bottom-0.5 rounded-[2px]" title={`${r.label}, ${r.sub}: ${r.v}\n${r.means}`}
                    style={{ left: `${pc(Math.min(r.from, r.to))}%`, width: `max(2px, ${Math.abs(pc(r.to) - pc(r.from))}%)`,
                      ...(r.n < 0 ? { border: `1.5px dashed ${r.id === 'cb' ? PAYER.cb : PAYER.gf}` } : { background: FILL[r.id] }) }} /> : null}
                  <span className="absolute top-1/2 -translate-y-1/2 text-[12.5px] tabular-nums font-semibold whitespace-nowrap px-1"
                    style={pc(Math.max(r.from, r.to)) > 75 ? { right: `${100 - pc(Math.min(r.from, r.to))}%`, marginRight: 2 } : { left: `${pc(Math.max(r.from, r.to))}%`, marginLeft: 2 }}>{r.v}</span>
                </div>
              </Row>))}
            {total(t.a_happened, y.totals.happened, y.totals.t.happened)}
          </div>)
      })()}

    </figure>)
}
