/** WHO PAID EACH KIND OF SCHOOL, YEAR BY YEAR (special-education/out-of-district-tuition).
 *
 *  TJ, 26 November 2026: "i want another chart that shows the composition of each as well in 1
 *  chart, over time, split by private/collab". A GROUPED STACKED column chart: one group per
 *  fiscal year, a private bar and a collaborative bar side by side in it, each stacked by the
 *  fund that paid, all on one dollar scale so size and make-up read together. The stock series
 *  chart could not do it: eight categorical labels collide, and on a phone it thins the axis to
 *  every other label, which would have dropped every collaborative bar's name. Every string and
 *  tick is formatted by scripts/build_special_education_topics.py; the component formats nothing. */
import type { CustomProps } from './index'

type Part = { payer: string; amt: number; text: string }
type Bar = { kind: string; short: string; total: number; total_text: string; parts: Part[] }
type Group = { fy: string; bars: Bar[] }
type Payer = { key: string; label: string; colour: number }
type Data = { groups: Group[]; payers: Payer[]; ticks: { v: number; text: string }[]; note: string }

const paint = (n: number) => (n ? `var(--thread-${n})` : 'var(--text-muted)')
const W = 640, H = 300, L = 56, R = 8, T = 22, B = 44

export default function OodComposition({ data, alt }: CustomProps) {
  const d = data as Data
  const payer = Object.fromEntries(d.payers.map(p => [p.key, p]))
  const top = d.ticks[d.ticks.length - 1].v
  const y = (v: number) => T + (H - T - B) * (1 - v / top)
  const gw = (W - L - R) / d.groups.length
  const bw = Math.min(46, gw * 0.34)
  return (
    <figure className="my-2 w-full max-w-full min-w-0" aria-label={alt}>
      <div className="flex flex-wrap gap-x-4 gap-y-1 mb-2 text-[12px]" style={{ color: 'var(--text-secondary)' }}>
        {d.payers.map(p => (
          <span key={p.key} className="inline-flex items-center gap-1.5">
            <span className="inline-block w-3 h-3 rounded-sm" style={{ background: paint(p.colour) }} />{p.label}
          </span>
        ))}
      </div>
      <div className="w-full max-w-full overflow-x-auto" style={{ WebkitOverflowScrolling: 'touch' }}>
        <svg viewBox={`0 0 ${W} ${H}`} className="block w-full" style={{ minWidth: 480, maxWidth: 768 }} role="img" aria-label={alt}>
          {d.ticks.map(t => (
            <g key={t.v}>
              <line x1={L} x2={W - R} y1={y(t.v)} y2={y(t.v)} stroke="var(--grid)" />
              <text x={L - 6} y={y(t.v) + 3.5} fontSize="10.5" textAnchor="end" fill="var(--text-muted)">{t.text}</text>
            </g>
          ))}
          {d.groups.map((g, gi) => {
            const cx = L + gw * gi + gw / 2
            return (
              <g key={g.fy}>
                {g.bars.map((b, bi) => {
                  const x = cx + (bi === 0 ? -bw - 6 : 6)
                  let acc = 0
                  return (
                    <g key={b.kind}>
                      {b.parts.map(p => {
                        const y0 = y(acc), y1 = y(acc + p.amt)
                        acc += p.amt
                        return (
                          <rect key={p.payer} x={x} y={y1} width={bw} height={Math.max(0, y0 - y1)}
                            fill={paint(payer[p.payer].colour)}>
                            <title>{`${g.fy}, ${b.kind}: ${payer[p.payer].label} ${p.text}`}</title>
                          </rect>
                        )
                      })}
                      <text x={x + bw / 2} y={y(b.total) - 5} fontSize="10" fontWeight={600} textAnchor="middle"
                        fill="var(--text-primary)">{b.total_text}</text>
                      <text x={x + bw / 2} y={H - B + 14} fontSize="10.5" textAnchor="middle"
                        fill="var(--text-secondary)">{b.short}</text>
                    </g>
                  )
                })}
                <text x={cx} y={H - B + 32} fontSize="11.5" fontWeight={600} textAnchor="middle"
                  fill="var(--text-primary)">{g.fy}</text>
              </g>
            )
          })}
          <line x1={L} x2={W - R} y1={y(0)} y2={y(0)} stroke="var(--axis, var(--text-muted))" />
        </svg>
      </div>
      <figcaption className="mt-2 text-[12.5px]" style={{ color: 'var(--text-muted)' }}>{d.note}</figcaption>
    </figure>
  )
}
