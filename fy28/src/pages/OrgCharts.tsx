import { useEffect, useMemo, useState } from 'react'
import { ReportShell, Body, Grain, H2, Stat } from '../components/report'

/* TOWN-WIDE ORG CHARTS: who held which role, in every department, board and school.
 *
 * TJ, 22 September 2026: *"I want to BUILD the org chart for every department, every
 * board, and the school, on one page... Selectable by dropdown... and we can do it for
 * each FY... THEN we have the true mapping of personnel"*, and on why it matters:
 * *"this helps the data model because the backend needs to map dept -> people in
 * various roles."*
 *
 * IT IS A TEST BEFORE IT IS A PAGE. Everything else this project reads can be counted
 * into existence. A chart of WHO IS IN WHICH ROLE cannot: it either joins a department to
 * named people with named roles, per year, or it visibly does not. Building the data
 * behind it found seven classes of defect nothing else had — a listing footnote read as a
 * post, sub-headings promoted to bodies, one post under four spellings.
 *
 * AND IT IS THE FIRST ONE THAT EXISTS. TJ: *"not every department posts one publicly
 * (<cough> schools) so this is the first ever publicly available org chart for many
 * departments outside the annual report of hundreds of pages."* Every name here has always
 * been public. None of it has ever been assembled. */

type Row = {
  fy: string; unit: string; unit_kind: string; subunit: string; section: string
  role: string; person: string; status: string; source: string; tier: string
}
type Unit = {
  unit: string; kind: string; rows: number; years: string[]; subunits: string[]
}
type Payload = { years: string[]; units: Unit[]; rows: Row[] }

// THE BANDS ARE OURS AND THE RANKS ARE THE TOWN'S. `Chief`, `Deputy Chief`, `Captain`,
// `Lieutenant`, `Sergeant` are printed beside the names; sorting them into four levels is
// our reading, and nothing published says who reports to whom — which is why these are
// called bands and drawn as indentation rather than as a tree with lines in it.
const BAND: Record<string, string> = {
  '0': 'Heads the body', '1': 'Deputy and assistant',
  '2': 'Supervisors and ranked posts', '3': 'Staff, seats and everyone else',
}
const INSET: Record<string, number> = { '0': 0, '1': 14, '2': 28, '3': 42 }

const KIND_LABEL: Record<string, string> = {
  department: 'Department', board: 'Board or committee',
  school: 'School', officer: 'Appointed post',
}

export function OrgCharts() {
  const [d, setD] = useState<Payload | null>(null)
  const [unit, setUnit] = useState('')
  const [fy, setFy] = useState('')
  // '' means every building. TJ: *"i want to see the whole thing in one place."* The
  // district is one organisation with four buildings, so ALL is the default and the
  // sub-selection narrows it rather than being something you must choose first.
  const [sub, setSub] = useState('')

  useEffect(() => {
    fetch('/data/org-charts.json').then(r => r.json()).then((j: Payload) => {
      setD(j)
      setUnit(j.units[0]?.unit ?? '')
      setFy(j.years[j.years.length - 1])
    }).catch(() => { /* no payload yet */ })
  }, [])

  const chosen = useMemo(() => d?.units.find(u => u.unit === unit) ?? null, [d, unit])

  // THE YEAR MENU IS THE UNIT'S OWN YEARS, not every year the archive holds. A department
  // that published in four years should not offer eleven empty ones.
  const years = chosen?.years ?? []
  const shownFy = years.includes(fy) ? fy : years[years.length - 1] ?? ''
  const subs = chosen?.subunits ?? []
  const rows = useMemo(
    () => (d?.rows ?? []).filter(r => r.unit === unit && r.fy === shownFy
      && (!sub || r.subunit === sub)),
    [d, unit, shownFy, sub])

  // ONE BLOCK PER BUILDING, AND BANDS INSIDE IT. TJ, 22 September 2026: *"i think the
  // org chart needs some hierarchy. flat lists are hard to read, and i know there's
  // hierarchy in here. ESP for the schools. but other depts have chiefs, captains, etc
  // so it exists there too."*
  //
  // The section stays on the row rather than becoming a heading of its own. Grouping on
  // it as well produced blocks of ONE — "Lunenburg High School · Athletic Director" with
  // a single name under it — because `grade_or_dept` is as fine as `Grade 3`.
  const blocks = useMemo(() => {
    const g = new Map<string, Map<string, Row[]>>()
    for (const r of rows) {
      const k = r.subunit || ''
      if (!g.has(k)) g.set(k, new Map())
      const bands = g.get(k)!
      const t = r.tier || '3'
      if (!bands.has(t)) bands.set(t, [])
      bands.get(t)!.push(r)
    }
    for (const bands of g.values()) {
      for (const rs of bands.values()) {
        rs.sort((a, b) => (a.role + a.section + a.person)
          .localeCompare(b.role + b.section + b.person))
      }
    }
    // The district's own offices carry no building, so their block sorts FIRST rather
    // than by size: a superintendent above four schools is the shape of the thing.
    return [...g.entries()]
      .map(([k, bands]) => [k, [...bands.entries()].sort()] as const)
      .sort((a, b) => (a[0] ? 1 : 0) - (b[0] ? 1 : 0)
        || b[1].reduce((n, x) => n + x[1].length, 0)
         - a[1].reduce((n, x) => n + x[1].length, 0))
  }, [rows])

  if (!d) return null
  // PEOPLE, NOT ROWS. Somebody who teaches two grades is one member of staff, and the
  // personnel report counts them that way -- 232 for FY2025, not 250. Two pages counting
  // the same archive differently is the defect this project catalogues.
  const filled = new Set(rows.filter(r => r.status === 'filled')
    .map(r => r.person.trim().toLowerCase())).size
  const roleRows = rows.filter(r => r.status === 'filled').length
  const vacant = rows.filter(r => r.status === 'vacant').length
  const posts = rows.filter(r => r.status === 'post').length
  const sel: React.CSSProperties = {
    background: 'var(--surface-1)', border: '1px solid var(--grid)',
    borderRadius: 8, padding: '7px 10px', fontSize: 14, color: 'var(--text-primary)',
    maxWidth: '100%',
  }

  return (
    <ReportShell title="Town-wide org charts"
      standfirst={'Every department, board, committee and school the annual reports name, '
        + 'and who held which role in each, year by year. Assembled from the town’s own '
        + 'listings and rosters — the material has always been public and has never '
        + 'been put in one place.'}>

      <div className="flex flex-wrap gap-3 mt-6 mb-2">
        <label className="flex flex-col gap-1 text-[12px]" style={{ color: 'var(--text-muted)' }}>
          Department, board or school
          <select value={unit} onChange={e => { setUnit(e.target.value); setSub('') }}
            style={sel}>
            {(['department', 'school', 'board', 'officer'] as const).map(k => (
              <optgroup key={k} label={KIND_LABEL[k]}>
                {d.units.filter(u => u.kind === k).map(u => (
                  <option key={u.unit} value={u.unit}>
                    {u.unit} ({u.years.length} yr)
                  </option>
                ))}
              </optgroup>
            ))}
          </select>
        </label>
        {subs.length > 0 ? (
          <label className="flex flex-col gap-1 text-[12px]"
            style={{ color: 'var(--text-muted)' }}>
            Building
            <select value={sub} onChange={e => setSub(e.target.value)} style={sel}>
              <option value="">All ({subs.length})</option>
              {subs.map(x => <option key={x} value={x}>{x}</option>)}
            </select>
          </label>
        ) : null}
        <label className="flex flex-col gap-1 text-[12px]" style={{ color: 'var(--text-muted)' }}>
          Fiscal year
          <select value={shownFy} onChange={e => setFy(e.target.value)} style={sel}>
            {years.map(y => <option key={y} value={y}>FY{y}</option>)}
          </select>
        </label>
      </div>

      <div className="flex flex-wrap gap-x-10 gap-y-5 mt-6">
        <Stat value={String(filled)}>people named</Stat>
        {roleRows > filled ? (
          <Stat value={String(roleRows)}>
            roles between them — some hold more than one
          </Stat>
        ) : null}
        {vacant > 0 ? <Stat value={String(vacant)} tone="var(--series-cost)">
          printed as vacant
        </Stat> : null}
        {posts > 0 ? <Stat value={String(posts)}>
          posts it states, with no name attached
        </Stat> : null}
      </div>

      <Grain>
        FOUR BANDS, and they are a reading of the ranks the town prints rather than a
        reporting line. Nobody publishes who reports to whom, so a Business Manager and a
        Principal both sit in the top band and the page does not claim one is above the
        other. PEOPLE AND POSTS, kept apart. A name is somebody the town printed in that role that
        year. A POST is an establishment position a department states and never says who
        fills — the DPW and the Assessing office publish that way. A roster is a point in
        time and undated within its year, so nobody here can be dated more precisely than
        the book they appear in.
      </Grain>

      {rows.length === 0 ? (
        <Body>Nothing is published for {unit} in FY{shownFy}.</Body>
      ) : blocks.map(([name, bands]) => (
        <section key={name || '_'} className="mt-7">
          {name ? <H2 id={`s-${name}`}>{name}</H2> : null}
          {bands.map(([tier, rs]) => (
            <div key={tier} className="mt-3"
              style={{ marginLeft: INSET[tier] ?? 42 }}>
              <div className="text-[11px] uppercase tracking-wide mb-1 flex items-center gap-2"
                style={{ color: 'var(--text-muted)' }}>
                <span style={{
                  display: 'inline-block', width: 6, height: 6, borderRadius: 6,
                  background: tier === '3' ? 'var(--grid)' : 'var(--series-1)',
                }} />
                {BAND[tier] ?? BAND['3']}
                <span style={{ opacity: 0.7 }}>{rs.length}</span>
              </div>
              <ul className="list-none p-0 m-0 grid gap-x-8 gap-y-1"
                style={{
                  gridTemplateColumns: 'repeat(auto-fill,minmax(280px,1fr))',
                  borderLeft: tier === '0' ? 'none' : '1px solid var(--grid)',
                  paddingLeft: tier === '0' ? 0 : 10,
                }}>
                {rs.map((r, i) => (
                  <li key={i} className="text-[13.5px] flex gap-2 items-baseline py-0.5"
                    style={{ borderBottom: '1px solid var(--grid)' }}>
                    <span style={{
                      color: r.person ? 'var(--text-primary)' : 'var(--text-muted)',
                      fontWeight: tier === '0' ? 600 : 400,
                    }}>
                      {r.person || (r.status === 'vacant' ? 'vacant' : '— unnamed post —')}
                    </span>
                    <span className="ml-auto text-right text-[12px] shrink-0"
                      style={{ color: 'var(--text-muted)' }}>
                      {[r.role, r.section].filter(Boolean).join(' \u00b7 ')}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </section>
      ))}

      <Body>
        <strong>What this cannot show.</strong> Whether a post was cut. A name missing from
        one year to the next can be somebody leaving a post that is still funded, or a post
        being eliminated — the Assessing office reported being “fully staffed for the first
        time in over a year” in FY2024, which is a year of posts that existed and stood
        empty. It also shows no pay, no hours and no FTE, and a person who appears under two
        roles is one person doing two jobs.
      </Body>
    </ReportShell>
  )
}
