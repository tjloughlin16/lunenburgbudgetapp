/** OUT-OF-DISTRICT TUITION, BY WHO WAS PAID AND WHO PAID IT (special-education/out-of-district-tuition).
 *
 *  TJ, 26 November 2026: "Id like to see the funding sources over time, as well as the budget vs
 *  actual for this, and to see if theres a shift between private/collab. all the data that
 *  muddies the water gets very confusing". So one row per fiscal year, two bars in it: tuition
 *  paid to private schools and tuition paid to collaboratives, every fund, sorted by the PAYEE
 *  (the account a payment was charged to is not always the kind of school it paid). Each bar is
 *  split by the fund that paid it; next year's invoices paid early are drawn hollow, outside the
 *  year's cost. The children counted on 1 March sit beside each bar as their own number, never
 *  divided into the dollars (rule 7). Every string is formatted by
 *  scripts/build_special_education_topics.py; the component formats nothing. */
import type { CustomProps } from './index'

type Part = { payer: string; amt: number; text: string }
type Line = { name: string; total_text: string; kids_text: string; parts: Part[]; early: Part | null }
type Year = { fy: string; lines: Line[] }
type Payer = { key: string; label: string; colour: number; hollow?: boolean }
type Data = { years: Year[]; payers: Payer[]; max: number; note: string }

// 0 is muted: the minor items (a one-off revolving fund, next year's invoices)
const paint = (n: number) => (n ? `var(--thread-${n})` : 'var(--text-muted)')

export default function OodWhoPaid({ data, alt }: CustomProps) {
  const d = data as Data
  const payer = Object.fromEntries(d.payers.map(p => [p.key, p]))
  const pct = (v: number) => `${(100 * v) / d.max}%`
  return (
    <figure className="my-2 w-full max-w-full min-w-0" aria-label={alt}>
      <div className="flex flex-wrap gap-x-4 gap-y-1 mb-3 text-[12px]" style={{ color: 'var(--text-secondary)' }}>
        {d.payers.map(p => (
          <span key={p.key} className="inline-flex items-center gap-1.5">
            <span className="inline-block w-3 h-3 rounded-sm"
              style={p.hollow
                ? { border: `1.5px dashed ${paint(p.colour)}` }
                : { background: paint(p.colour) }} />
            {p.label}
          </span>
        ))}
      </div>
      <div className="flex flex-col gap-4">
        {d.years.map(y => (
          <div key={y.fy}>
            <div className="text-[13px] font-semibold mb-1" style={{ color: 'var(--text-primary)' }}>{y.fy}</div>
            {y.lines.map(l => (
              <div key={l.name} className="mb-1.5">
                <div className="flex justify-between gap-2 text-[12.5px]" style={{ color: 'var(--text-secondary)' }}>
                  <span>{l.name}</span>
                  <span className="tabular-nums" style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{l.total_text}</span>
                </div>
                <div className="flex w-full h-4 rounded-sm overflow-hidden" style={{ background: 'var(--grid)' }}
                  role="img" aria-label={`${y.fy}, ${l.name}: ${l.total_text}; ${l.parts.map(p => `${payer[p.payer].label} ${p.text}`).join(', ')}`}>
                  {l.parts.map(p => (
                    <span key={p.payer} title={`${payer[p.payer].label}: ${p.text}`}
                      style={{ width: pct(p.amt), background: paint(payer[p.payer].colour) }} />
                  ))}
                  {l.early && (
                    <span title={`${payer[l.early.payer].label}: ${l.early.text}`}
                      style={{ width: pct(l.early.amt), border: `1.5px dashed ${paint(payer[l.early.payer].colour)}`,
                        background: 'var(--surface-1)', boxSizing: 'border-box' }} />
                  )}
                </div>
                <div className="flex flex-wrap justify-between gap-x-3 text-[11.5px] mt-0.5" style={{ color: 'var(--text-muted)' }}>
                  <span className="tabular-nums">
                    {l.parts.map(p => `${payer[p.payer].label} ${p.text}`).join(' · ')}
                    {l.early ? ` · ${payer[l.early.payer].label} ${l.early.text}` : ''}
                  </span>
                  <span>{l.kids_text}</span>
                </div>
              </div>
            ))}
          </div>
        ))}
      </div>
      <figcaption className="mt-3 text-[12.5px]" style={{ color: 'var(--text-muted)' }}>{d.note}</figcaption>
    </figure>
  )
}
