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
  fy: string; unit: string; unit_kind: string; section: string
  role: string; person: string; status: string; source: string
}
type Unit = { unit: string; kind: string; rows: number; years: string[] }
type Payload = { years: string[]; units: Unit[]; rows: Row[] }

const KIND_LABEL: Record<string, string> = {
  department: 'Department', board: 'Board or committee',
  school: 'School', officer: 'Appointed post',
}

export function OrgCharts() {
  const [d, setD] = useState<Payload | null>(null)
  const [unit, setUnit] = useState('')
  const [fy, setFy] = useState('')

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
  const rows = useMemo(
    () => (d?.rows ?? []).filter(r => r.unit === unit && r.fy === shownFy),
    [d, unit, shownFy])

  const sections = useMemo(() => {
    const g = new Map<string, Row[]>()
    for (const r of rows) {
      const k = r.section || ''
      if (!g.has(k)) g.set(k, [])
      g.get(k)!.push(r)
    }
    return [...g.entries()].sort((a, b) => b[1].length - a[1].length)
  }, [rows])

  if (!d) return null
  const filled = rows.filter(r => r.status === 'filled').length
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
          <select value={unit} onChange={e => setUnit(e.target.value)} style={sel}>
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
        <label className="flex flex-col gap-1 text-[12px]" style={{ color: 'var(--text-muted)' }}>
          Fiscal year
          <select value={shownFy} onChange={e => setFy(e.target.value)} style={sel}>
            {years.map(y => <option key={y} value={y}>FY{y}</option>)}
          </select>
        </label>
      </div>

      <div className="flex flex-wrap gap-x-10 gap-y-5 mt-6">
        <Stat value={String(filled)}>named in post</Stat>
        {vacant > 0 ? <Stat value={String(vacant)} tone="var(--series-cost)">
          printed as vacant
        </Stat> : null}
        {posts > 0 ? <Stat value={String(posts)}>
          posts it states, with no name attached
        </Stat> : null}
      </div>

      <Grain>
        PEOPLE AND POSTS, kept apart. A name is somebody the town printed in that role that
        year. A POST is an establishment position a department states and never says who
        fills — the DPW and the Assessing office publish that way. A roster is a point in
        time and undated within its year, so nobody here can be dated more precisely than
        the book they appear in.
      </Grain>

      {rows.length === 0 ? (
        <Body>Nothing is published for {unit} in FY{shownFy}.</Body>
      ) : sections.map(([name, rs]) => (
        <section key={name || '_'} className="mt-6">
          {name ? <H2 id={`s-${name}`}>{name}</H2> : null}
          <ul className="list-none p-0 m-0 grid gap-x-8 gap-y-1"
            style={{ gridTemplateColumns: 'repeat(auto-fill,minmax(280px,1fr))' }}>
            {rs.map((r, i) => (
              <li key={i} className="text-[13.5px] flex gap-2 items-baseline py-0.5"
                style={{ borderBottom: '1px solid var(--grid)' }}>
                <span style={{ color: r.person ? 'var(--text-primary)' : 'var(--text-muted)' }}>
                  {r.person || (r.status === 'vacant' ? 'vacant' : '— unnamed post —')}
                </span>
                {r.role ? (
                  <span className="ml-auto text-right text-[12px]"
                    style={{ color: 'var(--text-muted)' }}>{r.role}</span>
                ) : null}
              </li>
            ))}
          </ul>
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
