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
  section_group: string
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
  '2': 'Supervisors, ranked posts and the clerk',
  '3': 'Members, seats and staff',
  '4': 'Associate, honorary, ex officio and non-voting',
}
const INSET: Record<string, number> = { '0': 0, '1': 14, '2': 28, '3': 42, '4': 56 }

// INSIDE A BAND, THE TOWN'S OWN LADDER, NOT THE ALPHABET. Sorting by role put
// `Captain/AEMT` above `Deputy Chief` and `Assistant Principal` above `Deputy
// Superintendent`. These are the printed ranks in the order the departments use them;
// anything not listed keeps its place after them, alphabetically.
const LADDER = [
  /deputy\s+(chief|superintendent)/i, /\bdeputy\b/i,
  /assistant\s+principal/i, /\bcapt/i, /vice[- ]?chair/i,
  /\blieutenant\b|\blt\b/i, /\bsergeant\b|\bsgt\b/i, /\bdetective\b|\bdet\./i,
]
const ladder = (role: string) => {
  const i = LADDER.findIndex(re => re.test(role))
  return i === -1 ? LADDER.length : i
}

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
    const g = new Map<string, Map<string, Map<string, Row[]>>>()
    for (const r of rows) {
      const k = r.subunit || ''
      if (!g.has(k)) g.set(k, new Map())
      const bands = g.get(k)!
      const t = r.tier || '3'
      if (!bands.has(t)) bands.set(t, new Map())
      const groups = bands.get(t)!
      // THE GRADE AND THE DEPARTMENT. TJ: *"so for the school, dont we hav grade and
      // department info?! ... we should group by those."* We do, on every roster row —
      // the block heading the name was printed under. `section_group` is that heading
      // normalised; `section` is what the page actually said and stays on the row.
      // GROUPED WHERE THE GROUPING DIVIDES THE BAND, and the builder has already
      // blanked a heading that would stand alone over a whole band — so the Police
      // Chief's printed `Administration` does not become a heading of one, while the
      // Fire Department keeps `Career` and `Call` beside each other at every rank. TJ: *"For the police depatment,
      // you are putting the police chief under open shift roles and admins. thats just
      // awkward. You should recognize how this hierarchy works right? I think it's
      // pretty clear in their titles."* It is: the Chief's printed section is
      // `Administration`, which is where the roster sets his desk, not a rank. Above the
      // staff band the title IS the structure, so those bands render as a plain list.
      const sg = r.section_group || ''
      if (!groups.has(sg)) groups.set(sg, [])
      groups.get(sg)!.push(r)
    }
    const order = (x: string) => (x ? 1 : 0)   // the unlabelled rows lead each band
    return [...g.entries()]
      .map(([k, bands]) => [k, [...bands.entries()].sort()
        .map(([t, groups]) => [t, [...groups.entries()]
          .sort((p, q) => order(p[0]) - order(q[0]) || p[0].localeCompare(q[0]))
          .map(([sg, rs]) => [sg, rs.sort((x, y) => ladder(x.role) - ladder(y.role)
            || (x.role + x.person).localeCompare(y.role + y.person))] as const)] as const)] as const)
      // The district's own offices carry no building, so their block sorts FIRST rather
      // than by size: a superintendent above four schools is the shape of the thing.
      .sort((x, y) => order(x[0]) - order(y[0])
        || y[1].reduce((n, t) => n + t[1].reduce((m, s) => m + s[1].length, 0), 0)
         - x[1].reduce((n, t) => n + t[1].reduce((m, s) => m + s[1].length, 0), 0))
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

      {rows.length === 0 ? (
        <Body>Nothing is published for {unit} in FY{shownFy}.</Body>
      ) : blocks.map(([name, bands]) => (
        <section key={name || '_'} className="mt-7">
          {name ? <H2 id={`s-${name}`}>{name}</H2> : null}
          {bands.map(([tier, groups]) => {
            const n = groups.reduce((m, x) => m + x[1].length, 0)
            return (
            <div key={tier} className="mt-3" style={{ marginLeft: INSET[tier] ?? 42 }}>
              {/* A ONE-PERSON BODY HAS NO BANDS. `Heads the body — 1` over the Dam
                  Keeper is a label explaining a hierarchy of one. */}
              <div className="text-[11px] uppercase tracking-wide mb-1 flex items-center gap-2"
                style={{ color: 'var(--text-muted)' }}
                hidden={rows.length <= 1}>
                <span style={{
                  display: 'inline-block', width: 6, height: 6, borderRadius: 6,
                  background: tier === '3' ? 'var(--grid)' : 'var(--series-1)',
                }} />
                {BAND[tier] ?? BAND['3']}
                <span style={{ opacity: 0.7 }}>{n}</span>
              </div>
              <div style={{
                borderLeft: tier === '0' ? 'none' : '1px solid var(--grid)',
                paddingLeft: tier === '0' ? 0 : 10,
              }}>
                {groups.map(([sg, rs]) => (
                  <div key={sg || '_'} className={sg ? 'mt-2' : ''}>
                    {/* A SHIFT IS NOT A PERSON. TJ: *"the 'shifts' for police need to be
                        organized more clearly. hard to read those vs the people names."*
                        They were set in the same size and weight as the names directly
                        under them, so `Day Shift` read as somebody called Day Shift.
                        Small, spaced capitals with a rule: the eye sorts it before it
                        reads it. */}
                    {sg ? (
                      <div className="flex items-center gap-2 mt-3 mb-1">
                        <span className="text-[10.5px] uppercase shrink-0"
                          style={{
                            color: 'var(--text-muted)', letterSpacing: '0.09em',
                            fontWeight: 600,
                          }}>
                          {sg}
                        </span>
                        <span className="text-[10.5px] shrink-0"
                          style={{ color: 'var(--text-muted)', opacity: 0.75 }}>
                          {rs.length}
                        </span>
                        <span className="grow" style={{ borderTop: '1px solid var(--grid)' }} />
                      </div>
                    ) : null}
                    <ul className="list-none p-0 m-0 grid gap-x-8 gap-y-1"
                      style={{ gridTemplateColumns: 'repeat(auto-fill,minmax(280px,1fr))' }}>
                      {rs.map((r, i) => (
                        <li key={i} className="text-[13.5px] flex gap-2 items-baseline py-0.5"
                          style={{ borderBottom: '1px solid var(--grid)' }}>
                          <span style={{
                            color: r.person ? 'var(--text-primary)' : 'var(--text-muted)',
                            fontWeight: tier === '0' ? 600 : 400,
                          }}>
                            {r.person || (r.status === 'vacant' ? 'vacant' : '\u2014 unnamed post \u2014')}
                          </span>
                          <span className="ml-auto text-right text-[12px] shrink-0"
                            style={{ color: 'var(--text-muted)' }}>
                            {/* `board seat` and `officer` are what the listing calls a
                                row when it prints no title. Repeating it beside every
                                name is a column of one word. */}
                            {r.role === 'board seat' || r.role === 'officer' ? '' : r.role}
                          </span>
                        </li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
            </div>
          )})}
        </section>
      ))}

      {/* THE KEY COMES AFTER THE THING IT IS A KEY TO. TJ: *"can you put 'What this
          report counts' as context at the bottom, not the first big block of text."*
          Rule 7a, and this page was breaking it — a reader arrives for a department's
          chart and met nine lines explaining how to read one first. */}
      <Grain>
        A NAME is somebody the town printed in that role that year. A POST is an
        establishment position a department states and never says who fills — the DPW and
        the Assessing office publish that way. A roster is a point in time and undated
        within its year, so nobody here can be dated more precisely than the book they
        appear in.
      </Grain>

      <Body>
        <strong>The bands are ours; the ranks are the town’s.</strong> Chief, Deputy
        Chief, Captain, Lieutenant, Sergeant are printed beside the names. Sorting them
        into levels is our reading, and nothing published says who reports to whom — so a
        Business Manager and a Principal both sit in the top band and this page does not
        claim one is above the other. A board is ranked only by the officers it elects:
        chair, vice-chair, clerk. A member who is a director somewhere else is not that
        board’s deputy.
      </Body>

      <Body>
        <strong>Why so many boards have nobody at the top.</strong> The town’s officials
        listing marked its chairs with asterisks under a footnote reading “** denotes
        chairperson”, and stopped printing it after FY2016. 46 bodies name a chair
        somewhere in their own report and the rest never do, so a board can appear here
        as a list of members with no chair — which is what the record shows, not what the
        board looked like.
      </Body>

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
