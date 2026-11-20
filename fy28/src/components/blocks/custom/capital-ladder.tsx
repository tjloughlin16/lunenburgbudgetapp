/** EVERY CAPITAL REQUEST, IN RANK ORDER (the capital-fy<YEAR> pages).
 *
 *  TJ, 20 November 2026: "i want to clik into a FY and see what was asked for by department, then
 *  what was prioritized, in rank order". One row a request, in the Capital Planning Committee's
 *  order by default; one bar a row, as long as the request's cost, in its department's colour --
 *  solid where it was funded, an outline where it was not. So the place the solid bars stop is
 *  where the money ran out, and a solid bar below it was funded out of order.
 *
 *  COLOUR MEANS FUNDED, NOT DEPARTMENT, and matches the department chart under it (thread-1
 *  funded, thread-2 not). The first draft coloured bars by department, and then blue meant
 *  Facilities in one chart and "not funded" in the next one down the same page. The department
 *  is a word on each row instead.
 *
 *  Each year's documents print different rankings (Town Manager, Collins Center score, the
 *  members' average, the department's own order). The chips re-order the same rows by any of
 *  them; nothing is merged, and a request a scheme does not rank goes to the foot, marked.
 *
 *  Every figure is formatted by scripts/build_capital_rankings.py; this draws marks from the
 *  numbers and prints the given text. On a phone the rank, name and cost share a line and the
 *  bar sits under them, so nothing is wider than the card. */
import { useMemo, useState } from 'react'
import type { CustomProps } from './index'

type Scheme = { key: string; label: string; high_first: boolean }
type Row = {
  project: string; dept: number; amount: number; amount_text: string; funded: boolean
  ranks: Record<string, number>; rank_text: Record<string, string>
}
type Data = {
  schemes: Scheme[]; depts: { label: string }[]; rows: Row[]
  text: { funded: string; unfunded: string; order: string; unranked: string; rank: string; score: string; line?: string }
  note: string
}

const FUNDED = 'var(--thread-1)'
const UNFUNDED = 'var(--thread-2)'

export default function CapitalLadder({ data, alt }: CustomProps) {
  const d = data as Data
  const [by, setBy] = useState(d.schemes[0]?.key ?? 'cpc')
  const scheme = d.schemes.find(s => s.key === by) ?? d.schemes[0]
  const rows = useMemo(() => {
    const has = d.rows.filter(r => r.ranks[by] !== undefined)
    const not = d.rows.filter(r => r.ranks[by] === undefined)
    has.sort((a, b) => (scheme?.high_first ? b.ranks[by] - a.ranks[by] : a.ranks[by] - b.ranks[by])
      || a.project.localeCompare(b.project))
    return [...has, ...not]
  }, [d.rows, by, scheme])
  const max = Math.max(1, ...d.rows.map(r => r.amount))

  return (
    <figure className="my-2 w-full max-w-full min-w-0 overflow-hidden" aria-label={alt}>
      {d.schemes.length > 1 ? (
        <div className="flex flex-wrap items-center gap-1.5 mb-3 text-[12.5px]">
          <span style={{ color: 'var(--text-muted)' }}>{d.text.order}</span>
          {d.schemes.map(s => (
            <button key={s.key} type="button" onClick={() => setBy(s.key)} aria-pressed={s.key === by}
              className="px-2.5 py-1 rounded-full border leading-tight"
              style={{ borderColor: s.key === by ? 'var(--text-secondary)' : 'var(--grid)',
                color: s.key === by ? 'var(--text-primary)' : 'var(--text-muted)',
                background: s.key === by ? 'var(--surface-2)' : 'transparent', fontWeight: s.key === by ? 600 : 400 }}>
              {s.label}
            </button>))}
        </div>) : null}

      <div className="flex flex-wrap gap-x-4 gap-y-1 mb-3 text-[12.5px]" style={{ color: 'var(--text-secondary)' }}>
        <span className="inline-flex items-center gap-1.5">
          <span className="inline-block w-5 h-2.5 rounded-sm" style={{ background: FUNDED }} />{d.text.funded}</span>
        <span className="inline-flex items-center gap-1.5">
          <span className="inline-block w-5 h-2.5 rounded-sm" style={{ border: `1.5px solid ${UNFUNDED}` }} />{d.text.unfunded}</span>
      </div>

      <ol className="space-y-1.5 w-full min-w-0">
        {rows.map((r, i) => {
          const t = r.rank_text[by]
          // THE FUNDING LINE, in the committee's order only: drawn above the first request left
          // unfunded, so a solid bar under it is a request funded out of that order.
          const line = d.text.line && by === d.schemes[0]?.key && !r.funded && rows.slice(0, i).every(x => x.funded)
          return (
            <li key={r.project + i} className="min-w-0">
              {line ? (
                <p className="text-[11.5px] font-semibold uppercase tracking-wider mt-3 mb-1.5 pt-1 border-t-2 border-dashed"
                  style={{ borderColor: 'var(--status-warning)', color: 'var(--text-secondary)' }}>{d.text.line}</p>
              ) : null}
              <div className="flex items-baseline gap-2 text-[13px] leading-tight">
                <span className="tabular-nums shrink-0 w-9 text-right"
                  style={{ color: t ? 'var(--text-secondary)' : 'var(--text-muted)', fontSize: t ? undefined : '11px' }}
                  title={t ? `${scheme?.label} ${scheme?.high_first ? d.text.score : d.text.rank}` : d.text.unranked}>
                  {t ?? '—'}</span>
                <span className="min-w-0 flex-1 truncate" title={r.project}
                  style={{ color: r.funded ? 'var(--text-primary)' : 'var(--text-secondary)', fontWeight: r.funded ? 600 : 400 }}>
                  {r.project}
                  <span className="sm:hidden block text-[11px] font-normal" style={{ color: 'var(--text-muted)' }}>
                    {d.depts[r.dept].label}</span></span>
                <span className="hidden sm:inline shrink-0 text-[11.5px]" style={{ color: 'var(--text-muted)' }}>
                  {d.depts[r.dept].label}</span>
                <span className="tabular-nums shrink-0" style={{ color: 'var(--text-secondary)' }}>{r.amount_text}</span>
              </div>
              <div className="ml-11 mt-0.5 h-[10px]">
                <div className="h-full rounded-sm" title={`${d.depts[r.dept].label} · ${r.funded ? d.text.funded : d.text.unfunded}`}
                  style={{ width: `${Math.max(1.5, (100 * r.amount) / max)}%`,
                    background: r.funded ? FUNDED : 'transparent',
                    border: r.funded ? undefined : `1.5px solid ${UNFUNDED}` }} />
              </div>
            </li>)
        })}
      </ol>
      <figcaption className="mt-3 text-[12.5px]" style={{ color: 'var(--text-muted)' }}>{d.note}</figcaption>
    </figure>
  )
}
