/** WHAT WE HOLD, YEAR BY YEAR (near the foot of the capital-planning hub).
 *
 *  TJ, 20 November 2026: "put a table on the page, probably toward the bottom, that shows the
 *  information we have for every year." One row per fiscal year, newest first, as far back as any
 *  held source reaches; one column per kind of record (each department's requests, each body's
 *  order, the committee's ranked list as its own sheet and as others printed it, the Town Manager's
 *  plan, what was funded, the committee's minutes). A cell is a mark, one line saying what the
 *  record is, and links to the document(s) it was read from. Every string is formatted by
 *  scripts/build_capital_rankings.py from sources/data/capital-coverage.csv and the datasets it
 *  checks against. On a phone the table scrolls sideways inside itself, the year column pinned. */
import type { CustomProps } from './index'

type State = 'held' | 'part' | 'spoken' | 'none'
type Cell = { state: State; text: string; where: string; links: { label: string; href: string }[] }
type Data = {
  columns: { key: string; label: string }[]
  rows: { label: string; cells: Cell[] }[]
  gaps: { what: string; href: string }[]
  text: Record<State, string> & { year: string; gaps: string }
  note: string
}

const MARK: Record<State, { glyph: string; color: string }> = {
  held: { glyph: '●', color: 'var(--thread-1)' },
  part: { glyph: '◐', color: 'var(--status-warning)' },
  spoken: { glyph: '○', color: 'var(--status-warning)' },
  none: { glyph: '–', color: 'var(--text-muted)' },
}

function Mark({ s, label }: { s: State; label: string }) {
  return <span aria-label={label} title={label} className="text-[13px] leading-none" style={{ color: MARK[s].color }}>{MARK[s].glyph}</span>
}

export default function CapitalCoverage({ data, alt }: CustomProps) {
  const d = data as Data
  const states: State[] = ['held', 'part', 'spoken', 'none']
  return (
    <figure className="my-2 w-full max-w-full min-w-0" aria-label={alt}>
      <div className="flex flex-wrap gap-x-4 gap-y-1 mb-2 text-[12px]" style={{ color: 'var(--text-secondary)' }}>
        {states.map(s => <span key={s} className="inline-flex items-center gap-1.5"><Mark s={s} label={d.text[s]} />{d.text[s]}</span>)}
      </div>
      <div className="w-full max-w-full overflow-x-auto" style={{ WebkitOverflowScrolling: 'touch' }}>
        <table className="border-collapse text-[12px]" style={{ minWidth: 72 + d.columns.length * 150 }}>
          <thead>
            <tr>
              <th scope="col" className="sticky left-0 z-10 text-left font-semibold px-2 py-1.5 align-bottom"
                style={{ background: 'var(--surface-1)', color: 'var(--text-secondary)', width: 72 }}>{d.text.year}</th>
              {d.columns.map(c => (
                <th key={c.key} scope="col" className="text-left font-semibold px-2 py-1.5 align-bottom"
                  style={{ color: 'var(--text-secondary)', width: 150 }}>{c.label}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {d.rows.map(r => (
              <tr key={r.label} className="border-t" style={{ borderColor: 'var(--grid)' }}>
                <th scope="row" className="sticky left-0 z-10 text-left font-semibold px-2 py-1.5 align-top tabular-nums"
                  style={{ background: 'var(--surface-1)', color: 'var(--text-primary)' }}>{r.label}</th>
                {r.cells.map((c, i) => (
                  <td key={i} className="px-2 py-1.5 align-top" style={{ color: c.state === 'none' ? 'var(--text-muted)' : 'var(--text-primary)' }}>
                    <div className="flex gap-1.5 items-baseline">
                      <Mark s={c.state} label={d.text[c.state]} />
                      {c.text ? <span className="leading-snug">{c.text}</span> : null}
                    </div>
                    {c.links.length ? (
                      <div className="mt-0.5 pl-4 leading-snug break-all" style={{ color: 'var(--text-muted)', fontSize: 11 }}>
                        {c.links.map((l, j) => (
                          <span key={j}>{j ? ' · ' : ''}<a href={l.href} className="underline">{l.label}</a></span>
                        ))}
                        {c.where ? <span> · {c.where}</span> : null}
                      </div>
                    ) : null}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <figcaption className="mt-2 text-[12.5px]" style={{ color: 'var(--text-muted)' }}>
        {d.note}
        {d.gaps.length ? (
          <>
            <span className="block mt-2 font-semibold" style={{ color: 'var(--text-secondary)' }}>{d.text.gaps}</span>
            <ul className="list-disc pl-5 m-0">
              {d.gaps.map((g, i) => <li key={i}><a href={g.href} className="underline">{g.what}</a></li>)}
            </ul>
          </>
        ) : null}
      </figcaption>
    </figure>
  )
}
