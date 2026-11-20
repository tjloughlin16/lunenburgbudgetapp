/** TWO ORDERS OF THE SAME LIST, a slope chart (the capital-fy<YEAR> pages).
 *
 *  Left: each request at its Capital Planning Committee rank. Right: the same request at its place
 *  in a second order the year's documents print -- the Town Manager's rank, or the order of the
 *  members' average rank. A flat line is agreement; a steep line is a request the two orders place
 *  far apart, and those (a move of `far` places or more) are drawn strong and named, the rest faint.
 *  Colour is funded or not, as on every capital chart. The generator computes each position from
 *  the printed values; ties share a place. Drawn as SVG on a viewBox, so it narrows with the
 *  screen. */
import type { CustomProps } from './index'

type Row = { project: string; a: number; b: number; funded: boolean }
type Data = {
  left: string; right: string; n: number; far: number; rows: Row[]
  text: { funded: string; unfunded: string }; note: string
}

export default function CapitalTwoOrders({ data, alt }: CustomProps) {
  const d = data as Data
  const W = 640, top = 26, step = 15, H = top + d.n * step + 8
  const xl = 250, xr = 390
  const y = (k: number) => top + (k - 1) * step + step / 2
  const strong = (r: Row) => Math.abs(r.a - r.b) >= d.far
  const rows = [...d.rows].sort((p, q) => Number(strong(p)) - Number(strong(q)))
  const short = (s: string) => (s.length > 36 ? s.slice(0, 35) + '…' : s)
  return (
    <figure className="my-2 w-full max-w-3xl min-w-0" aria-label={alt}>
      <div className="flex flex-wrap gap-x-4 gap-y-1 mb-2 text-[12.5px]" style={{ color: 'var(--text-secondary)' }}>
        <span className="inline-flex items-center gap-1.5"><span className="inline-block w-5 h-[3px]" style={{ background: 'var(--thread-1)' }} />{d.text.funded}</span>
        <span className="inline-flex items-center gap-1.5"><span className="inline-block w-5 h-[3px]" style={{ background: 'var(--thread-2)' }} />{d.text.unfunded}</span>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto" role="img" aria-label={alt}>
        <text x={xl} y={14} textAnchor="end" fontSize="12" fontWeight="600" fill="var(--text-muted)">{d.left}</text>
        <text x={xr} y={14} textAnchor="start" fontSize="12" fontWeight="600" fill="var(--text-muted)">{d.right}</text>
        {rows.map(r => {
          const s = strong(r)
          const c = r.funded ? 'var(--thread-1)' : 'var(--thread-2)'
          return (
            <g key={r.project + r.a} opacity={s ? 1 : 0.35}>
              <title>{`${r.project}: ${d.left} ${r.a}, ${d.right} ${r.b}`}</title>
              <line x1={xl + 6} y1={y(r.a)} x2={xr - 6} y2={y(r.b)} stroke={c} strokeWidth={s ? 2.2 : 1.2} />
              <circle cx={xl + 6} cy={y(r.a)} r={2.6} fill={c} />
              <circle cx={xr - 6} cy={y(r.b)} r={2.6} fill={c} />
              <text x={xl} y={y(r.a) + 4} textAnchor="end" fontSize="11" fill="var(--text-secondary)"
                fontWeight={s ? 600 : 400}>{short(r.project)} {r.a}</text>
              {s ? <text x={xr} y={y(r.b) + 4} fontSize="11" fill="var(--text-primary)" fontWeight="600">{r.b} {short(r.project)}</text>
                : <text x={xr} y={y(r.b) + 4} fontSize="11" fill="var(--text-muted)">{r.b}</text>}
            </g>)
        })}
      </svg>
      <figcaption className="mt-2 text-[12.5px]" style={{ color: 'var(--text-muted)' }}>{d.note}</figcaption>
    </figure>
  )
}
