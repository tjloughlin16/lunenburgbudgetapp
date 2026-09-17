import type { ReactNode } from 'react'
import { Go } from '../lib/nav'
import type { Tab } from '../routes'

/** THE FRAME EVERY LEVER REPORT SHARES. TJ, 17 September 2026, on the first shelf of
 *  /reports, "What the town can do": one report per thing the town can actually decide,
 *  each answering the same four questions in the same order --
 *
 *    what pulling it is worth        in the gap's own units: dollars a year, years covered
 *    who pays                        because every lever lands on somebody
 *    what it does not do             usually: it does not change the rate
 *    what would settle it            the document or vote nobody has yet
 *
 *  and each one linking to the MEASUREMENT report it draws on rather than restating it
 *  (the cost of health insurance, whether free cash is hoarded, what a family pays).
 *  TJ: "if the main conclusions are the same with varying levels of context, we
 *  probably need to restructure" -- so a lever page's conclusions are about the LEVER
 *  and a measurement page's about the THING, and the two share figures, not claims. */

export function WhoPays({ children }: { children: ReactNode }) {
  return (
    <div className="card p-4 mt-6 max-w-3xl" style={{ borderLeft: '3px solid var(--status-warning)' }}>
      <p className="text-[11px] font-semibold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>Who pays</p>
      <div className="text-[14px] leading-relaxed mt-1.5" style={{ color: 'var(--text-secondary)' }}>{children}</div>
    </div>
  )
}

export function DoesNot({ children }: { children: ReactNode }) {
  return (
    <div className="card p-4 mt-4 max-w-3xl">
      <p className="text-[11px] font-semibold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>What it does not do</p>
      <div className="text-[14px] leading-relaxed mt-1.5" style={{ color: 'var(--text-secondary)' }}>{children}</div>
    </div>
  )
}

export function Settles({ children }: { children: ReactNode }) {
  return (
    <p className="text-[13px] leading-relaxed mt-4 max-w-3xl" style={{ color: 'var(--text-muted)' }}>
      <strong style={{ color: 'var(--text-secondary)' }}>What would settle it:</strong> {children}
    </p>
  )
}

/** The way out: the measurement report this lever draws on, the options page, the crisis page. */
export function LeverLinks({ measures, label }: { measures: Tab; label: string }) {
  return (
    <div className="grid gap-2.5 sm:grid-cols-3 mt-8 max-w-4xl">
      <Go to={measures} className="card px-4 py-3 block">
        <span className="block text-[13.5px] font-bold" style={{ color: 'var(--series-cost)' }}>{label} &rarr;</span>
        <span className="block text-[12px] mt-0.5" style={{ color: 'var(--text-secondary)' }}>The measurement this page draws on.</span>
      </Go>
      <Go to="solutions" className="card px-4 py-3 block">
        <span className="block text-[13.5px] font-bold" style={{ color: 'var(--series-cost)' }}>Every option, side by side &rarr;</span>
        <span className="block text-[12px] mt-0.5" style={{ color: 'var(--text-secondary)' }}>Priced the same way, to five years and ten.</span>
      </Go>
      <Go to="walk" className="card px-4 py-3 block">
        <span className="block text-[13.5px] font-bold" style={{ color: 'var(--series-cost)' }}>The crisis page &rarr;</span>
        <span className="block text-[12px] mt-0.5" style={{ color: 'var(--text-secondary)' }}>Why it is a rate problem, in five numbers.</span>
      </Go>
    </div>
  )
}

export const pct = (x: number, d = 1) => `${(x * 100).toFixed(d)}%`
export const n0 = (n: number) => Math.round(n).toLocaleString('en-US')
