/** EACH DEPARTMENT, EACH YEAR (the capital-rankings hub): the department-by-year table drawn.
 *
 *  TJ, 20 November 2026: "another chart AND table that shows the same info as 'Each department,
 *  year by year'". Small multiples: a row per department, a column per fiscal year, in each cell a
 *  bar as long as the dollars requested with the funded part filled. ONE scale for every cell, so a
 *  long bar is a big year against every department and every year, not just its own row. Every
 *  string is formatted by scripts/build_capital_rankings.py; on a phone the grid scrolls sideways
 *  inside itself with the department column pinned. */
import type { CustomProps } from './index'

type Cell = { req: number; fun: number; text: string } | null
type Data = {
  years: string[]; rows: { label: string; cells: Cell[] }[]
  text: { funded: string; unfunded: string; none: string }; note: string
}

const FUNDED = 'var(--thread-1)'
const UNFUNDED = 'var(--thread-2)'

export default function CapitalDeptYears({ data, alt }: CustomProps) {
  const d = data as Data
  const max = Math.max(...d.rows.flatMap(r => r.cells.map(c => (c ? c.req : 0))))
  return (
    <figure className="my-2 w-full max-w-full min-w-0" aria-label={alt}>
      <div className="flex flex-wrap gap-x-4 gap-y-1 mb-2 text-[12px]" style={{ color: 'var(--text-secondary)' }}>
        <span className="inline-flex items-center gap-1.5"><span className="inline-block w-3 h-3 rounded-sm" style={{ background: FUNDED }} />{d.text.funded}</span>
        <span className="inline-flex items-center gap-1.5"><span className="inline-block w-3 h-3 rounded-sm" style={{ border: `1.5px solid ${UNFUNDED}` }} />{d.text.unfunded}</span>
      </div>
      <div className="w-full max-w-full overflow-x-auto" style={{ WebkitOverflowScrolling: 'touch' }}>
        <table className="border-collapse text-[12px]" style={{ minWidth: 130 + d.years.length * 140 }}>
          <thead>
            <tr>
              <th className="sticky left-0 z-10" style={{ background: 'var(--surface-1)', width: 130 }} />
              {d.years.map(y => <th key={y} scope="col" className="text-left font-semibold px-2 py-1.5"
                style={{ color: 'var(--text-secondary)', width: 140 }}>{y}</th>)}
            </tr>
          </thead>
          <tbody>
            {d.rows.map(r => (
              <tr key={r.label} className="border-t" style={{ borderColor: 'var(--grid)' }}>
                <th scope="row" className="sticky left-0 z-10 text-left font-semibold px-2 py-2 align-top"
                  style={{ background: 'var(--surface-1)', color: 'var(--text-primary)' }}>{r.label}</th>
                {r.cells.map((c, i) => (
                  <td key={i} className="px-2 py-2 align-top">
                    {c ? (
                      <>
                        <div className="relative h-3.5 rounded-sm" title={c.text}
                          style={{ width: `max(6px, ${(100 * c.req) / max}%)`, border: `1.5px solid ${c.fun >= c.req ? FUNDED : UNFUNDED}` }}>
                          <div className="absolute left-0 top-0 bottom-0"
                            style={{ width: `${c.req ? (100 * c.fun) / c.req : 0}%`, background: FUNDED }} />
                        </div>
                        <div className="mt-1 tabular-nums leading-snug" style={{ color: 'var(--text-secondary)' }}>{c.text}</div>
                      </>
                    ) : <span style={{ color: 'var(--text-muted)' }}>{d.text.none}</span>}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <figcaption className="mt-2 text-[12.5px]" style={{ color: 'var(--text-muted)' }}>{d.note}</figcaption>
    </figure>
  )
}
