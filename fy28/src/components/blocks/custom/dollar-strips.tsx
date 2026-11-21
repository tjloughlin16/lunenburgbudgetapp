/** EVERY ORDER ON ONE DOLLAR SCALE, WITH THE CAPITAL LINE DRAWN (school facility jobs).
 *
 *  TJ, 21 November 2026: the schools have "permanent, operational funding for projects that are
 *  WELL WITHIN the purview of capital planning". So the picture is the threshold: a row per
 *  fiscal year, every purchase order on the school upkeep lines as a dot on ONE logarithmic dollar
 *  scale, coloured by what it bought, and the Schools' capital requests for the same year as a
 *  row beneath it. A vertical rule marks the Town's $20,000 capital test. Dots right of the rule
 *  on an operating row are capital-sized work that never went through ranking. Every string is
 *  formatted by scripts/build_school_facility_jobs.py; on a phone the figure scrolls sideways. */
import type { CustomProps } from './index'

type Dot = { amt: number; kind: string; tip: string }
type Row = { label: string; sub: string; dots: Dot[]; n_text: string; total_text: string; group: boolean }
type Kind = { key: string; label: string; colour: number; hollow?: boolean }

// colour 0 is muted (not yet read); 1-5 are the site's thread colours
const paint = (n: number) => (n ? `var(--thread-${n})` : 'var(--text-muted)')
type Data = {
  rows: Row[]; kinds: Kind[]; ticks: { v: number; text: string }[]
  line: { v: number; text: string }; note: string
  text: { row: string; dots: string; n: string; total: string }
}

const W = 340, H = 30, PAD = 8

export default function DollarStrips({ data, alt }: CustomProps) {
  const d = data as Data
  const all = d.rows.flatMap(r => r.dots.map(x => x.amt)).filter(v => v > 0)
  const lo = Math.log10(Math.min(d.ticks[0].v, ...all))
  const hi = Math.log10(Math.max(d.ticks[d.ticks.length - 1].v, ...all))
  const x = (v: number) => PAD + ((Math.log10(Math.max(v, 1)) - lo) / (hi - lo)) * (W - 2 * PAD)
  const kind = Object.fromEntries(d.kinds.map(k => [k.key, k]))
  const num = 'px-2 py-2 text-right tabular-nums align-middle'
  const head = 'px-2 py-1.5 font-semibold align-bottom'
  const lx = x(d.line.v)
  return (
    <figure className="my-2 w-full max-w-full min-w-0" aria-label={alt}>
      <div className="flex flex-wrap gap-x-4 gap-y-1 mb-2 text-[12px]" style={{ color: 'var(--text-secondary)' }}>
        {d.kinds.map(k => (
          <span key={k.key} className="inline-flex items-center gap-1.5">
            <svg width="10" height="10">
              {k.hollow
                ? <rect x="1.5" y="1.5" width="7" height="7" fill="none" stroke={paint(k.colour)} strokeWidth="1.5" transform="rotate(45 5 5)" />
                : <circle cx="5" cy="5" r="4" fill={paint(k.colour)} />}
            </svg>{k.label}
          </span>
        ))}
        <span className="inline-flex items-center gap-1.5">
          <svg width="10" height="12"><line x1="5" x2="5" y1="0" y2="12" stroke="var(--text-primary)" strokeDasharray="3 2" /></svg>{d.line.text}
        </span>
      </div>
      <div className="w-full max-w-full overflow-x-auto" style={{ WebkitOverflowScrolling: 'touch' }}>
        <table className="border-collapse text-[12.5px]" style={{ minWidth: 150 + W + 2 * 96 }}>
          <thead>
            <tr style={{ color: 'var(--text-secondary)' }}>
              <th scope="col" className={`${head} text-left sticky left-0 z-10`} style={{ background: 'var(--surface-1)', width: 150 }}>{d.text.row}</th>
              <th scope="col" className={`${head} text-left`} style={{ width: W }}>
                {d.text.dots}
                <svg width={W} height={14} className="block mt-1" aria-hidden="true">
                  {d.ticks.map((t, i) => (
                    <text key={t.v} x={x(t.v)} y={11} fontSize="10" fill="var(--text-muted)"
                      textAnchor={i === 0 ? 'start' : i === d.ticks.length - 1 ? 'end' : 'middle'}>{t.text}</text>
                  ))}
                </svg>
              </th>
              <th scope="col" className={`${head} text-right`}>{d.text.n}</th>
              <th scope="col" className={`${head} text-right`}>{d.text.total}</th>
            </tr>
          </thead>
          <tbody>
            {d.rows.map((r, ri) => (
              <tr key={ri} className={r.group ? 'border-t' : ''} style={{ borderColor: 'var(--grid)' }}>
                <th scope="row" className="sticky left-0 z-10 text-left px-2 py-1.5 align-middle"
                  style={{ background: 'var(--surface-1)', color: 'var(--text-primary)' }}>
                  <span className={r.group ? 'font-semibold' : 'font-normal'}>{r.label}</span>
                  <span className="block text-[11.5px] font-normal" style={{ color: 'var(--text-muted)' }}>{r.sub}</span>
                </th>
                <td className="px-2 py-1 align-middle">
                  <svg width={W} height={H} role="img" aria-label={`${r.label}, ${r.sub}: ${r.dots.length}`}>
                    {d.ticks.map(t => <line key={t.v} x1={x(t.v)} x2={x(t.v)} y1={2} y2={H - 2} stroke="var(--grid)" />)}
                    <line x1={lx} x2={lx} y1={0} y2={H} stroke="var(--text-primary)" strokeDasharray="3 2" />
                    {r.dots.map((p, i) => {
                      const k = kind[p.kind]
                      const cy = H / 2 + ((i % 3) - 1) * 6
                      return k.hollow
                        ? <rect key={i} x={x(p.amt) - 4} y={cy - 4} width={8} height={8} fill="var(--surface-1)"
                            stroke={paint(k.colour)} strokeWidth={1.5} transform={`rotate(45 ${x(p.amt)} ${cy})`}><title>{p.tip}</title></rect>
                        : <circle key={i} cx={x(p.amt)} cy={cy} r={4} fill={paint(k.colour)} fillOpacity={0.8}
                            stroke={paint(k.colour)} strokeWidth={1}><title>{p.tip}</title></circle>
                    })}
                  </svg>
                </td>
                <td className={num}>{r.n_text}</td>
                <td className={num} style={{ fontWeight: 600 }}>{r.total_text}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <figcaption className="mt-2 text-[12.5px]" style={{ color: 'var(--text-muted)' }}>{d.note}</figcaption>
    </figure>
  )
}
