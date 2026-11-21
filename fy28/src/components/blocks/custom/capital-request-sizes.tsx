/** WHO GOT THE MOST, AND HOW BIG THEY ASKED (the capital-rankings hub).
 *
 *  TJ, 20 November 2026: "which dept got the most funding ... esp including somehow based on their
 *  requests (do they not make a lot of big requests?!)". A row per department, most funded first.
 *  Left: every request the committee ranked in five years as a dot on ONE dollar scale, filled if
 *  funded. The scale is logarithmic, so a $20,000 request and a $900,000 one are both readable;
 *  the note says so. Right: the five-year totals, as a table. Every string is formatted by
 *  scripts/build_capital_rankings.py; on a phone the figure scrolls sideways inside itself. */
import type { CustomProps } from './index'

type Dot = { amt: number; ok: boolean; tip: string }
type Row = {
  label: string; dots: Dot[]
  n_text: string; med_text: string; req_text: string; fun_text: string; own_text: string; share_text: string
}
type Data = {
  rows: Row[]; ticks: { v: number; text: string }[]; note: string
  text: { funded: string; unfunded: string; dept: string; dots: string; n: string; med: string; req: string; fun: string; own: string; share: string }
}

const FUNDED = 'var(--thread-1)'
const UNFUNDED = 'var(--thread-2)'
const W = 300, H = 30, PAD = 8

export default function CapitalRequestSizes({ data, alt }: CustomProps) {
  const d = data as Data
  const all = d.rows.flatMap(r => r.dots.map(x => x.amt))
  const lo = Math.log10(Math.min(d.ticks[0].v, ...all)), hi = Math.log10(Math.max(d.ticks[d.ticks.length - 1].v, ...all))
  const x = (v: number) => PAD + ((Math.log10(v) - lo) / (hi - lo)) * (W - 2 * PAD)
  const num = 'px-2 py-2 text-right tabular-nums align-middle'
  const head = 'px-2 py-1.5 font-semibold align-bottom'
  return (
    <figure className="my-2 w-full max-w-full min-w-0" aria-label={alt}>
      <div className="flex flex-wrap gap-x-4 gap-y-1 mb-2 text-[12px]" style={{ color: 'var(--text-secondary)' }}>
        <span className="inline-flex items-center gap-1.5"><svg width="10" height="10"><circle cx="5" cy="5" r="4" fill={FUNDED} /></svg>{d.text.funded}</span>
        <span className="inline-flex items-center gap-1.5"><svg width="10" height="10"><circle cx="5" cy="5" r="3.5" fill="none" stroke={UNFUNDED} strokeWidth="1.5" /></svg>{d.text.unfunded}</span>
      </div>
      <div className="w-full max-w-full overflow-x-auto" style={{ WebkitOverflowScrolling: 'touch' }}>
        <table className="border-collapse text-[12.5px]" style={{ minWidth: 130 + W + 6 * 92 }}>
          <thead>
            <tr style={{ color: 'var(--text-secondary)' }}>
              <th scope="col" className={`${head} text-left sticky left-0 z-10`} style={{ background: 'var(--surface-1)', width: 130 }}>{d.text.dept}</th>
              <th scope="col" className={`${head} text-left`} style={{ width: W }}>
                {d.text.dots}
                <svg width={W} height={14} className="block mt-1" aria-hidden="true">
                  {d.ticks.map((t, i) => (
                    <text key={t.v} x={x(t.v)} y={11} fontSize="10" fill="var(--text-muted)" fontWeight="400"
                      textAnchor={i === 0 ? 'start' : i === d.ticks.length - 1 ? 'end' : 'middle'}>{t.text}</text>
                  ))}
                </svg>
              </th>
              <th scope="col" className={`${head} text-right`}>{d.text.n}</th>
              <th scope="col" className={`${head} text-right`}>{d.text.med}</th>
              <th scope="col" className={`${head} text-right`}>{d.text.req}</th>
              <th scope="col" className={`${head} text-right`}>{d.text.fun}</th>
              <th scope="col" className={`${head} text-right`}>{d.text.own}</th>
              <th scope="col" className={`${head} text-right`}>{d.text.share}</th>
            </tr>
          </thead>
          <tbody>
            {d.rows.map(r => (
              <tr key={r.label} className="border-t" style={{ borderColor: 'var(--grid)' }}>
                <th scope="row" className="sticky left-0 z-10 text-left font-semibold px-2 py-2 align-middle"
                  style={{ background: 'var(--surface-1)', color: 'var(--text-primary)' }}>{r.label}</th>
                <td className="px-2 py-1 align-middle">
                  <svg width={W} height={H} role="img" aria-label={`${r.label}: ${r.dots.length}`}>
                    {d.ticks.map(t => <line key={t.v} x1={x(t.v)} x2={x(t.v)} y1={2} y2={H - 2} stroke="var(--grid)" />)}
                    {r.dots.map((p, i) => (
                      <circle key={i} cx={x(p.amt)} cy={H / 2 + ((i % 3) - 1) * 6} r={4.5}
                        fill={p.ok ? FUNDED : 'var(--surface-1)'} fillOpacity={p.ok ? 0.85 : 1}
                        stroke={p.ok ? FUNDED : UNFUNDED} strokeWidth={1.5}>
                        <title>{p.tip}</title>
                      </circle>
                    ))}
                  </svg>
                </td>
                <td className={num}>{r.n_text}</td>
                <td className={num}>{r.med_text}</td>
                <td className={num}>{r.req_text}</td>
                <td className={num} style={{ fontWeight: 600 }}>{r.fun_text}</td>
                <td className={num}>{r.own_text}</td>
                <td className={num}>{r.share_text}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <figcaption className="mt-2 text-[12.5px]" style={{ color: 'var(--text-muted)' }}>{d.note}</figcaption>
    </figure>
  )
}
