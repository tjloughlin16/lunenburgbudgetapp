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

/** The numbers each column sorts on, by index: 0 FY26 actual, 1 FY27 budget, 2 Version N, 3 change,
 *  4 % change, 5 % of FY27, 6 FY26 budget, 7 FY26 spent - budget, 8 its %, 9 Version N - FY26 spent. */
type Vals = (number | null)[]
type Cells = { actual: string; prior: string; proposed: string; change: string; pct: string; share: string
  orig26: string; spent26: string; over26: string; overpct26: string; vs26: string }
type Line = Cells & { line: string; n: number; v: Vals; tag: '' | 'new' | 'zero'; below: boolean; page: number }
type Group = Cells & { section: string; code: string; name: string; n: number; v: Vals; lines: Line[] }
type Filter = 'all' | 'up' | 'down' | 'new' | 'zero' | 'below'
/** 'order' is the district's; 'line' sorts by name; a number sorts by that index of `v`. */
type SortKey = 'order' | 'line' | number
/** TWO WAYS TO READ A LINE (TJ, 21 November 2026). Against last year's BUDGET: how the draft moves
 *  it. Against FY26 SPENDING: "is this budget matching what they REALLY spend for these lines". The
 *  second compares a budget with an actual in dollars only (rule 1): no rate is drawn between them. */
type View = 'budget' | 'spent'
type Col = { k: number; f: keyof Cells; tone?: (v: Vals) => string; muted?: boolean; phone?: false }
const VIEWS: Record<View, Col[]> = {
  budget: [
    { k: 0, f: 'actual', muted: true, phone: false }, { k: 1, f: 'prior' }, { k: 2, f: 'proposed' },
    { k: 3, f: 'change', tone: v => tone(v[3] ?? 0) }, { k: 4, f: 'pct', tone: v => (v[4] == null ? 'var(--text-secondary)' : tone(v[3] ?? 0)) },
    { k: 5, f: 'share', tone: () => 'var(--text-secondary)' }],
  spent: [
    { k: 6, f: 'orig26', muted: true, phone: false }, { k: 0, f: 'spent26' },
    { k: 7, f: 'over26', tone: v => tone(v[7] ?? 0) }, { k: 8, f: 'overpct26', tone: v => tone(v[7] ?? 0) },
    { k: 2, f: 'proposed' }, { k: 9, f: 'vs26', tone: v => ((v[9] ?? 0) < -0.5 ? 'var(--status-warning)' : 'var(--text-secondary)') }],
}
const SORT0: Record<View, { key: SortKey; desc: boolean }> = { budget: { key: 3, desc: true }, spent: { key: 9, desc: false } }
type Data = {
  groups: Group[]
  counts: { new: number; zero: number }
  text: Record<keyof Cells | 'view' | 'view_budget' | 'view_spent' | 'below' | 'spent_summary' | 'spent_note' | 'share' | 'pct' | 'line' | 'actual' | 'prior' | 'proposed' | 'change' | 'all' | 'up' | 'down' | 'new' | 'zero' | 'expand' | 'collapse'
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
  f === 'all' || (f === 'below' && l.below) || (f === 'up' && l.n > 0.5) || (f === 'down' && l.n < -0.5) || (f === 'new' && l.tag === 'new') || (f === 'zero' && l.tag === 'zero')

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
  // `?view=spent` opens the spending comparison, so a link can point straight at it.
  const start: View = typeof window !== 'undefined' && new URLSearchParams(window.location.search).get('view') === 'spent' ? 'spent' : 'budget'
  const [view, setView] = useState<View>(start)
  const [sort, setSort] = useState<{ key: SortKey; desc: boolean }>(SORT0[start])
  const pick = (w: View) => { setView(w); setSort(SORT0[w]); if (w === 'budget' && filter === 'below') setFilter('all') }
  const cols = VIEWS[view]
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
  const filters: Filter[] = view === 'spent' ? ['all', 'below', 'up', 'down'] : ['all', 'up', 'down', 'new', 'zero']
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
      {cols.map(c => (
        <td key={c.f} className={`text-right px-2 py-1 tabular-nums${c.phone === false ? ' hidden sm:table-cell' : ''}`}
          style={{ color: c.muted ? 'var(--text-muted)' : c.tone ? c.tone(l.v) : undefined }}>{l[c.f]}</td>
      ))}
    </tr>
  )
  let section = ''
  return (
    <figure className="my-2 w-full max-w-full min-w-0" aria-label={alt}>
      <div role="tablist" aria-label={d.text.view} className="inline-flex items-center gap-1 mb-2 text-[13px]">
        <span className="mr-1" style={{ color: 'var(--text-secondary)' }}>{d.text.view}</span>
        {(['budget', 'spent'] as View[]).map(w => (
          <button key={w} role="tab" type="button" aria-selected={view === w} onClick={() => pick(w)}
            className="rounded-md border px-3 py-1 font-semibold"
            style={{ borderColor: view === w ? 'var(--brand)' : 'var(--grid)', color: view === w ? 'var(--brand)' : 'var(--text-secondary)',
              background: view === w ? 'var(--surface-2, transparent)' : 'transparent' }}>
            {w === 'budget' ? d.text.view_budget : d.text.view_spent}
          </button>
        ))}
      </div>
      {view === 'spent' ? <p className="mb-2 text-[14px] font-semibold leading-snug">{d.text.spent_summary}</p> : null}
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
        <table className="w-full border-collapse text-[12.5px]" style={{ minWidth: 680 }}>
          <thead>
            <tr>
              <Head k="line" label={d.text.line} cls="text-left" />
              {cols.map(c => <Head key={c.f} k={c.k} label={d.text[c.f]} cls={`text-right${c.phone === false ? ' hidden sm:table-cell' : ''}`} muted={c.muted} />)}
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
                    <th colSpan={cols.length + 1} scope="rowgroup" className="text-left font-semibold px-2 pt-4 pb-1 text-[11px] uppercase tracking-wide"
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
                  {cols.map(c => (
                    <td key={c.f} className={`text-right px-2 py-1.5 tabular-nums font-semibold${c.phone === false ? ' hidden sm:table-cell' : ''}`}
                      style={{ color: c.muted ? 'var(--text-muted)' : c.tone ? c.tone(g.v) : undefined }}>{g[c.f]}</td>
                  ))}
                </tr>,
                ...(o ? lines.map((l, i) => lineRow(l, `${id(g)}-${i}`)) : []),
              ]
            })}
            {!shown.length ? <tr><td colSpan={cols.length + 1} className="px-2 py-3" style={{ color: 'var(--text-muted)' }}>{d.text.none}</td></tr> : null}
          </tbody>
        </table>
      </div>
      {!grouped && !query && flat.length > FIRST ? (
        <button type="button" onClick={() => setMore(!more)} className="mt-2 rounded-md border px-3 py-1.5 text-[13px] font-semibold"
          style={{ borderColor: 'var(--brand)', color: 'var(--brand)' }}>
          {more ? d.text.fewer : `${d.text.show_all} (${flat.length})`}
        </button>
      ) : null}
      <figcaption className="mt-2 text-[12.5px]" style={{ color: 'var(--text-muted)' }}>{view === 'spent' ? d.text.spent_note : d.text.actual_note}</figcaption>
    </figure>
  )
}
