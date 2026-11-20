/** WHO ASKED, WHO GOT: two 100% columns, the dollars requested and the dollars funded, each split
 *  by department, with each department's two bands joined (the capital-fy<YEAR> pages).
 *
 *  A band that narrows from left to right is a department whose share of the funded dollars fell
 *  below its share of the requests; one that widens, the reverse. Shares of DOLLARS, which the
 *  generator computes and formats.
 *
 *  COLOUR: grey, except the one department the page's conclusion names (`highlight`). Every other
 *  capital chart on these pages uses the first two hues for funded and not funded, so a band in
 *  those hues would mean a department here and "funded" one chart up -- the collision the ranked
 *  list was already rebuilt to avoid. Departments are told apart by their direct labels. */
import type { CustomProps } from './index'

type Dept = { label: string; req: number; fun: number; req_text: string; fun_text: string }
type Data = { depts: Dept[]; highlight?: string; text: { req: string; fun: string }; note: string }


export default function CapitalShareBands({ data, alt }: CustomProps) {
  const d = data as Data
  const W = 640, H = 300, top = 22, h = H - top - 6, bw = 70
  const xl = 150, xr = W - 150 - bw
  let ya = top, yb = top
  const bands = d.depts.map((x, i) => {
    const a0 = ya, a1 = ya + (h * x.req) / 100, b0 = yb, b1 = yb + (h * x.fun) / 100
    ya = a1; yb = b1
    const hi = x.label === d.highlight
    return { ...x, hi, a0, a1, b0, b1, c: hi ? 'var(--thread-3)' : 'var(--text-muted)', o: hi ? 1 : i % 2 ? 0.45 : 0.62 }
  })
  // A band too thin for its label goes unlabelled (its title still names it) -- except the one
  // highlighted, which the conclusion under the chart is about.
  const lab = (y0: number, y1: number, hi = false) => (y1 - y0 >= 11 || hi ? (y0 + y1) / 2 + 4 : null)
  return (
    <figure className="my-2 w-full max-w-3xl min-w-0" aria-label={alt}>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto" role="img" aria-label={alt}>
        <text x={xl + bw / 2} y={14} textAnchor="middle" fontSize="12" fontWeight="600" fill="var(--text-muted)">{d.text.req}</text>
        <text x={xr + bw / 2} y={14} textAnchor="middle" fontSize="12" fontWeight="600" fill="var(--text-muted)">{d.text.fun}</text>
        {bands.map(b => (
          <g key={b.label}>
            <title>{`${b.label}: ${b.req_text} of the requests, ${b.fun_text} of the funded`}</title>
            <path d={`M${xl + bw},${b.a0} L${xr},${b.b0} L${xr},${b.b1} L${xl + bw},${b.a1} Z`} fill={b.c} opacity={b.o * 0.3} />
            <rect x={xl} y={b.a0} width={bw} height={Math.max(0, b.a1 - b.a0)} fill={b.c} opacity={b.o} stroke="var(--bg, #fff)" strokeWidth={1} />
            <rect x={xr} y={b.b0} width={bw} height={Math.max(0, b.b1 - b.b0)} fill={b.c} opacity={b.o} stroke="var(--bg, #fff)" strokeWidth={1} />
            {lab(b.a0, b.a1, b.hi) ? <text x={xl - 6} y={lab(b.a0, b.a1, b.hi)!} textAnchor="end" fontSize="11.5" fill="var(--text-secondary)">
              {b.label} <tspan fontWeight="600" fill="var(--text-primary)">{b.req_text}</tspan></text> : null}
            {lab(b.b0, b.b1, b.hi) ? <text x={xr + bw + 6} y={lab(b.b0, b.b1, b.hi)!} fontSize="11.5" fill="var(--text-secondary)">
              <tspan fontWeight="600" fill="var(--text-primary)">{b.fun_text}</tspan> {b.label}</text> : null}
          </g>))}
      </svg>
      <figcaption className="mt-2 text-[12.5px]" style={{ color: 'var(--text-muted)' }}>{d.note}</figcaption>
    </figure>
  )
}
