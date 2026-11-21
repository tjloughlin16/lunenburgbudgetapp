/** EVERY LINE OF A SCHOOL BUDGET DRAFT, by cost center (school-budget-fy<NN>-version-<N>).
 *
 *  TJ, 20 November 2026: the district's drafts are printed line by line and "we need to ingest it
 *  to put it in the DB" and give each its own page. A draft runs to three hundred lines, ten times
 *  what a table view may hold, so this draws them grouped: one row per cost center with its total
 *  and change, folded, and every line beneath it when opened. Filters keep only the lines that
 *  went up, went down, are new this year, or went to zero; a group opens itself when a filter
 *  leaves lines in it.
 *
 *  SORTABLE, 21 November 2026 (TJ: "needs to have sortable columns"). Every header sorts; a second
 *  click reverses. Grouped, the cost centers sort by their totals within each section and the lines
 *  within each cost center; ungrouped, every line is one list and names its cost center. Unsorted,
 *  everything is in the order the district prints it. Blank values sort last either way.
 *
 *  Every string is formatted by scripts/build_school_drafts.py. `v` holds the numbers each column
 *  sorts on and `n` the signed change, which also picks the colour. The prior-year actual is printed
 *  muted, for reference: nothing on the page is measured from it (rule 1). */
import { useMemo, useState } from 'react'
import type { CustomProps } from './index'

type Vals = [number | null, number | null, number | null, number]
type Line = { line: string; actual: string; prior: string; proposed: string; change: string; n: number; v: Vals; tag: '' | 'new' | 'zero'; page: number }
type Group = { section: string; code: string; name: string; prior: string; proposed: string; change: string; n: number; v: Vals; lines: Line[] }
type Filter = 'all' | 'up' | 'down' | 'new' | 'zero'
/** 'order' is the district's; 'line' sorts by name; 0-3 by a figure column. */
type SortKey = 'order' | 'line' | 0 | 1 | 2 | 3
type Data = {
  groups: Group[]
  counts: { new: number; zero: number }
  text: Record<'line' | 'actual' | 'prior' | 'proposed' | 'change' | 'all' | 'up' | 'down' | 'new' | 'zero' | 'expand' | 'collapse'
    | 'actual_note' | 'page' | 'grouped' | 'sort_hint' | 'cost_center' | 'search' | 'none' | 'show_all' | 'fewer', string>
}

const UP = 'var(--status-bad, var(--thread-1))', DOWN = 'var(--status-good, var(--thread-5))'
const tone = (n: number) => (n > 0.5 ? UP : n < -0.5 ? DOWN : 'var(--text-muted)')
/** SEARCH, 21 November 2026. TJ: "why doesnt health insurance show up" -- it was there, folded
 *  under 5200 Insurance Programs, a heading only the district uses. A query matches a line's name or
 *  its cost center's, and opens every group it leaves lines in. */
const FIRST = 25
const norm = (s: string) => s.toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim()
const keep = (f: Filter, l: Line) =>
  f === 'all' || (f === 'up' && l.n > 0.5) || (f === 'down' && l.n < -0.5) || (f === 'new' && l.tag === 'new') || (f === 'zero' && l.tag === 'zero')

function compare<T extends { v: Vals }>(key: SortKey, desc: boolean, name: (x: T) => string) {
  return (a: T, b: T) => {
    if (key === 'line') return (desc ? -1 : 1) * name(a).localeCompare(name(b))
    const x = a.v[key as number], y = b.v[key as number]
    if (x == null && y == null) return 0
    if (x == null) return 1                       // blank last, whichever way
    if (y == null) return -1
    return desc ? y - x : x - y
  }
}

export default function SchoolDraftLines({ data, alt }: CustomProps) {
  const d = data as Data
  const [filter, setFilter] = useState<Filter>('all')
  const [open, setOpen] = useState<Record<string, boolean>>({})
  const [all, setAll] = useState(false)
  // OPENS THE WAY THE BRIDGE ABOVE READS. TJ, 21 November 2026: "NONE of the items in From last
  // year's budget to this draft show up in the 'every line' chart" -- they were there, folded, in
  // print order. So it opens flat, largest change first: the bridge's lines are the first rows.
  const [grouped, setGrouped] = useState(false)
  const [sort, setSort] = useState<{ key: SortKey; desc: boolean }>({ key: 3, desc: true })
  const [more, setMore] = useState(false)
  const [q, setQ] = useState('')
  const query = norm(q)
  const id = (g: Group) => `${g.section}|${g.code}|${g.name}`

  const shown = useMemo(() => {
    const hit = (g: Group, l: Line) => !query || norm(l.line).includes(query) || norm(`${g.code} ${g.name}`).includes(query)
    const gs = d.groups.map(g => ({ g, lines: g.lines.filter(l => keep(filter, l) && hit(g, l)) })).filter(x => x.lines.length)
    if (sort.key === 'order') return gs
    const byLine = compare<Line>(sort.key, sort.desc, l => l.line)
    const byGroup = compare<Group>(sort.key, sort.desc, g => g.name)
    const sections = [...new Set(gs.map(x => x.g.section))]
    return sections.flatMap(s => gs.filter(x => x.g.section === s)
      .map(x => ({ g: x.g, lines: [...x.lines].sort(byLine) }))
      .sort((a, b) => byGroup(a.g, b.g)))
  }, [d.groups, filter, sort, query])

  const flat = useMemo(() => {
    const ls = shown.flatMap(x => x.lines.map(l => ({ l, g: x.g })))
    if (sort.key === 'order') return ls
    const c = compare<Line>(sort.key, sort.desc, l => l.line)
    return ls.sort((a, b) => c(a.l, b.l))
  }, [shown, sort])

  const isOpen = (g: Group) => all || filter !== 'all' || !!query || !!open[id(g)]
  const filters: Filter[] = ['all', 'up', 'down', 'new', 'zero']
  // A figure column opens largest first; a name opens A to Z; a third click returns to print order.
  const click = (key: SortKey) => setSort(s => s.key !== key ? { key, desc: key !== 'line' }
    : s.desc === (key !== 'line') ? { key, desc: !s.desc } : { key: 'order', desc: true })
  const Head = ({ k, label, cls, muted }: { k: SortKey; label: string; cls: string; muted?: boolean }) => {
    const on = sort.key === k
    return (
      <th scope="col" className={`font-semibold px-2 py-1.5 ${cls}`} aria-sort={on ? (sort.desc ? 'descending' : 'ascending') : 'none'}>
        <button type="button" onClick={() => click(k)} className="inline-flex items-center gap-1 underline decoration-dotted underline-offset-2"
          style={{ color: on ? 'var(--text-primary)' : muted ? 'var(--text-muted)' : 'var(--text-secondary)' }}>
          {label}<span aria-hidden className="text-[10px]">{on ? (sort.desc ? '▼' : '▲') : '↕'}</span>
        </button>
      </th>
    )
  }
  const lineRow = (l: Line, key: string, g?: Group) => (
    <tr key={key} style={{ color: 'var(--text-primary)' }} className={g ? 'border-t' : ''}>
      <td className={`${g ? 'pl-2' : 'pl-7'} pr-2 py-1 leading-snug`} style={g ? { borderColor: 'var(--grid)' } : undefined}>
        {l.line}
        {l.tag ? (
          <span className="ml-1.5 rounded px-1 text-[10.5px]" style={{ border: '1px solid var(--grid)', color: 'var(--text-secondary)' }}>{d.text[l.tag]}</span>
        ) : null}
        {g ? <span className="block text-[11px]" style={{ color: 'var(--text-muted)' }}>{g.code ? `${g.code} ` : ''}{g.name}</span> : null}
      </td>
      <td className="text-right px-2 py-1 tabular-nums hidden sm:table-cell" style={{ color: 'var(--text-muted)' }}>{l.actual}</td>
      <td className="text-right px-2 py-1 tabular-nums">{l.prior}</td>
      <td className="text-right px-2 py-1 tabular-nums">{l.proposed}</td>
      <td className="text-right px-2 py-1 tabular-nums" style={{ color: tone(l.n) }}>{l.change}</td>
    </tr>
  )
  let section = ''
  return (
    <figure className="my-2 w-full max-w-full min-w-0" aria-label={alt}>
      <div className="flex flex-wrap items-center gap-1.5 mb-1 text-[12px]">
        {filters.map(f => (
          <button key={f} type="button" onClick={() => setFilter(f)} className="rounded-full border px-2.5 py-0.5" aria-pressed={filter === f}
            style={{ borderColor: filter === f ? 'var(--text-primary)' : 'var(--grid)', color: filter === f ? 'var(--text-primary)' : 'var(--text-secondary)',
              background: filter === f ? 'var(--surface-2, transparent)' : 'transparent' }}>
            {d.text[f]}
          </button>
        ))}
        <label className="ml-auto inline-flex items-center gap-1.5 cursor-pointer" style={{ color: 'var(--text-secondary)' }}>
          <input type="checkbox" checked={grouped} onChange={e => setGrouped(e.target.checked)} />{d.text.grouped}
        </label>
        {grouped && filter === 'all' ? (
          <button type="button" onClick={() => setAll(!all)} className="underline" style={{ color: 'var(--text-secondary)' }}>
            {all ? d.text.collapse : d.text.expand}
          </button>
        ) : null}
      </div>
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mb-2">
        <input type="search" value={q} onChange={e => setQ(e.target.value)} placeholder={d.text.search} aria-label={d.text.search}
          className="w-full sm:w-72 rounded-md border px-2.5 py-1.5 text-[13px]"
          style={{ borderColor: 'var(--grid)', background: 'var(--surface-1)', color: 'var(--text-primary)' }} />
        <span className="text-[11.5px]" style={{ color: 'var(--text-muted)' }}>{d.text.sort_hint}</span>
      </div>
      <div className="w-full max-w-full overflow-x-auto" style={{ WebkitOverflowScrolling: 'touch' }}>
        <table className="w-full border-collapse text-[12.5px]" style={{ minWidth: 520 }}>
          <thead>
            <tr>
              <Head k="line" label={d.text.line} cls="text-left" />
              <Head k={0} label={d.text.actual} cls="text-right hidden sm:table-cell" muted />
              <Head k={1} label={d.text.prior} cls="text-right" />
              <Head k={2} label={d.text.proposed} cls="text-right" />
              <Head k={3} label={d.text.change} cls="text-right" />
            </tr>
          </thead>
          <tbody>
            {!grouped ? (more || query ? flat : flat.slice(0, FIRST)).map(({ l, g }, i) => lineRow(l, `f-${i}`, g)) : shown.map(({ g, lines }) => {
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
                ...(o ? lines.map((l, i) => lineRow(l, `${id(g)}-${i}`)) : []),
              ]
            })}
            {!shown.length ? <tr><td colSpan={5} className="px-2 py-3" style={{ color: 'var(--text-muted)' }}>{d.text.none}</td></tr> : null}
          </tbody>
        </table>
      </div>
      {!grouped && !query && flat.length > FIRST ? (
        <button type="button" onClick={() => setMore(!more)} className="mt-2 rounded-md border px-3 py-1.5 text-[13px] font-semibold"
          style={{ borderColor: 'var(--brand)', color: 'var(--brand)' }}>
          {more ? d.text.fewer : `${d.text.show_all} (${flat.length})`}
        </button>
      ) : null}
      <figcaption className="mt-2 text-[12.5px]" style={{ color: 'var(--text-muted)' }}>{d.text.actual_note}</figcaption>
    </figure>
  )
}
