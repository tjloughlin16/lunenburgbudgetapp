/** YEARS AND WHAT THEY NEED (fy-breakdown). TJ, 27 October 2026: "as soon as we ingest the same
 *  data from munis.. the FY should auto-unlock ... maybe at the bottom of the page we put the
 *  Records Request to fetch the next FY". Not switched by the picker: it is about which years
 *  there are. scripts/build_fy_breakdown.py (readiness) decides, from what the archive holds. */
import type { CustomProps } from './index'

type Input = { label: string; held: boolean; required: boolean; ask: string | null }
type Data = { years: { fy: string; ready: boolean; inputs: Input[] }[]; text: Record<string, string> }

const muted = { color: 'var(--text-muted)' }, secondary = { color: 'var(--text-secondary)' }

export default function FyReadiness({ data, alt }: CustomProps) {
  const d = data as Data
  const t = d.text
  return (
    <figure aria-label={alt} className="space-y-3">
      {d.years.map(y => (
        <section key={y.fy} className="rounded-md px-3 py-2" style={{ border: '1px solid var(--grid)' }}>
          <p className="text-[14px] font-semibold">{y.fy}
            <span className="ml-2 text-[12px] font-normal" style={muted}>{y.ready ? t.ready : t.waiting}</span></p>
          <ul className="mt-1.5 space-y-1.5">
            {y.inputs.map((i, k) => (
              <li key={k} className="text-[13px] flex gap-2">
                <span aria-hidden className="w-4 shrink-0 text-center" style={{ color: i.held ? 'var(--thread-2)' : 'var(--text-muted)' }}>{i.held ? '✓' : '○'}</span>
                <span className="min-w-0">{i.label}
                  <span className="ml-1.5 text-[11.5px]" style={muted}>{i.held ? t.held : t.missing}{i.required ? '' : ` · ${t.optional}`}</span>
                  {i.ask ? <span className="block text-[12px] mt-0.5" style={secondary}><span className="font-semibold">{t.ask}:</span> {i.ask}</span> : null}</span>
              </li>))}
          </ul>
        </section>))}
      <p className="text-[12px]" style={muted}>{t.how}</p>
    </figure>)
}
