/** EVERY LINE OF A SCHOOL BUDGET DRAFT, by cost centre (school-budget-fy<NN>-version-<N>).
 *
 *  TJ, 20 November 2026: the district's drafts are printed line by line and "we need to ingest it
 *  to put it in the DB" and give each its own page. A draft runs to three hundred lines, ten times
 *  what a table view may hold, so this draws them grouped: one row per cost centre with its total
 *  and change, folded, and every line beneath it when opened. Filters keep only the lines that
 *  went up, went down, are new this year, or went to zero; a group opens itself when a filter
 *  leaves lines in it. Groups are ordered as the district prints them.
 *
 *  Every string is formatted by scripts/build_school_drafts.py; `n` is the signed change as a
 *  number, used only to choose a colour and to filter. The prior-year actual is printed muted,
 *  for reference: nothing on the page is measured from it (rule 1). */
import { useMemo, useState } from 'react'
import type { CustomProps } from './index'

type Line = { line: string; actual: string; prior: string; proposed: string; change: string; n: number; tag: '' | 'new' | 'zero'; page: number }
type Group = { section: string; code: string; name: string; prior: string; proposed: string; change: string; n: number; lines: Line[] }
type Filter = 'all' | 'up' | 'down' | 'new' | 'zero'
type Data = {
  groups: Group[]
  counts: { new: number; zero: number }
  text: Record<'line' | 'actual' | 'prior' | 'proposed' | 'change' | 'all' | 'up' | 'down' | 'new' | 'zero' | 'expand' | 'collapse' | 'actual_note' | 'page', string>
}

const UP = 'var(--status-bad, var(--thread-1))', DOWN = 'var(--status-good, var(--thread-5))'
const tone = (n: number) => (n > 0.5 ? UP : n < -0.5 ? DOWN : 'var(--text-muted)')
const keep = (f: Filter, l: Line) =>
  f === 'all' || (f === 'up' && l.n > 0.5) || (f === 'down' && l.n < -0.5) || (f === 'new' && l.tag === 'new') || (f === 'zero' && l.tag === 'zero')

export default function SchoolDraftLines({ data, alt }: CustomProps) {
  const d = data as Data
  const [filter, setFilter] = useState<Filter>('all')
  const [open, setOpen] = useState<Record<string, boolean>>({})
  const [all, setAll] = useState(false)
  const shown = useMemo(() => d.groups.map(g => ({ g, lines: g.lines.filter(l => keep(filter, l)) }))
    .filter(x => x.lines.length), [d.groups, filter])
  const id = (g: Group) => `${g.section}|${g.code}|${g.name}`
  const isOpen = (g: Group) => all || filter !== 'all' || !!open[id(g)]
  const filters: Filter[] = ['all', 'up', 'down', 'new', 'zero']
  let section = ''
  return (
    <figure className="my-2 w-full max-w-full min-w-0" aria-label={alt}>
      <div className="flex flex-wrap items-center gap-1.5 mb-2 text-[12px]">
        {filters.map(f => (
          <button key={f} type="button" onClick={() => setFilter(f)}
            className="rounded-full border px-2.5 py-0.5"
            aria-pressed={filter === f}
            style={{ borderColor: filter === f ? 'var(--text-primary)' : 'var(--grid)',
              color: filter === f ? 'var(--text-primary)' : 'var(--text-secondary)',
              background: filter === f ? 'var(--surface-2, transparent)' : 'transparent' }}>
            {d.text[f]}
          </button>
        ))}
        {filter === 'all' ? (
          <button type="button" onClick={() => setAll(!all)} className="ml-auto underline" style={{ color: 'var(--text-secondary)' }}>
            {all ? d.text.collapse : d.text.expand}
          </button>
        ) : null}
      </div>
      <div className="w-full max-w-full overflow-x-auto" style={{ WebkitOverflowScrolling: 'touch' }}>
        <table className="w-full border-collapse text-[12.5px]" style={{ minWidth: 520 }}>
          <thead>
            <tr style={{ color: 'var(--text-secondary)' }}>
              <th scope="col" className="text-left font-semibold px-2 py-1.5">{d.text.line}</th>
              <th scope="col" className="text-right font-semibold px-2 py-1.5 hidden sm:table-cell" style={{ color: 'var(--text-muted)' }}>{d.text.actual}</th>
              <th scope="col" className="text-right font-semibold px-2 py-1.5">{d.text.prior}</th>
              <th scope="col" className="text-right font-semibold px-2 py-1.5">{d.text.proposed}</th>
              <th scope="col" className="text-right font-semibold px-2 py-1.5">{d.text.change}</th>
            </tr>
          </thead>
          <tbody>
            {shown.map(({ g, lines }) => {
              const head = g.section !== section
              section = g.section
              const o = isOpen(g)
              return [
                head ? (
                  <tr key={`s-${g.section}`}>
                    <th colSpan={5} scope="rowgroup" className="text-left font-semibold px-2 pt-4 pb-1 text-[11px] uppercase tracking-wide"
                      style={{ color: 'var(--text-muted)' }}>{g.section}</th>
                  </tr>
                ) : null,
                <tr key={id(g)} className="border-t cursor-pointer" style={{ borderColor: 'var(--grid)' }}
                  onClick={() => setOpen({ ...open, [id(g)]: !open[id(g)] })}>
                  <th scope="row" className="text-left font-semibold px-2 py-1.5" style={{ color: 'var(--text-primary)' }}>
                    <button type="button" aria-expanded={o} className="text-left">
                      <span aria-hidden className="inline-block w-3" style={{ color: 'var(--text-muted)' }}>{o ? '▾' : '▸'}</span>
                      {g.code ? <span className="tabular-nums mr-1.5" style={{ color: 'var(--text-muted)' }}>{g.code}</span> : null}
                      {g.name}
                    </button>
                  </th>
                  <td className="hidden sm:table-cell" />
                  <td className="text-right px-2 py-1.5 tabular-nums font-semibold">{g.prior}</td>
                  <td className="text-right px-2 py-1.5 tabular-nums font-semibold">{g.proposed}</td>
                  <td className="text-right px-2 py-1.5 tabular-nums font-semibold" style={{ color: tone(g.n) }}>{g.change}</td>
                </tr>,
                ...(o ? lines.map((l, i) => (
                  <tr key={`${id(g)}-${i}`} style={{ color: 'var(--text-primary)' }}>
                    <td className="pl-7 pr-2 py-1 leading-snug">
                      {l.line}
                      {l.tag ? (
                        <span className="ml-1.5 rounded px-1 text-[10.5px]" style={{ border: '1px solid var(--grid)', color: 'var(--text-secondary)' }}>
                          {d.text[l.tag]}
                        </span>
                      ) : null}
                    </td>
                    <td className="text-right px-2 py-1 tabular-nums hidden sm:table-cell" style={{ color: 'var(--text-muted)' }}>{l.actual}</td>
                    <td className="text-right px-2 py-1 tabular-nums">{l.prior}</td>
                    <td className="text-right px-2 py-1 tabular-nums">{l.proposed}</td>
                    <td className="text-right px-2 py-1 tabular-nums" style={{ color: tone(l.n) }}>{l.change}</td>
                  </tr>
                )) : []),
              ]
            })}
          </tbody>
        </table>
      </div>
      <figcaption className="mt-2 text-[12.5px]" style={{ color: 'var(--text-muted)' }}>{d.text.actual_note}</figcaption>
    </figure>
  )
}
