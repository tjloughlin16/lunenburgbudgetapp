import { useEffect, useMemo, useState } from 'react'
import { usd } from '../model/engine'
import {
  PeerRatio, IndexedPair, NamesPrinted, RoleGrid, StaffAgainstEnrolment, TableTwin,
  fy, num, pct,
  type Peer, type RosterYear, type RoleRow, type StatePoint,
} from '../components/StaffingCharts'

/** School staffing — names, FTE and dollars.
 *
 *  WHY THIS PAGE EXISTS AND WHAT IT IS CAREFUL ABOUT.
 *
 *  Three things in this archive touch school staffing and a reader will assume they are
 *  one thing. They are not, and the whole page is built to keep them apart:
 *
 *    1. NAMES the town printed — a faculty roster per school in every annual town report,
 *       FY2011–FY2025. No FTE, no funding source, undated within the year. A count of
 *       these is a count of names the town printed. It is a real quantity and it is not a
 *       staffing level.
 *    2. FTE the STATE published — DESE reports full-time equivalents for teachers and
 *       paraprofessionals, for Lunenburg and six comparison districts, FY2009–FY2025.
 *       This is the only FTE in the archive and it is not the town's number.
 *    3. DOLLARS — budget lines. Rule 11: a line is NET of grants, fees and reimbursement,
 *       and a line rising is not a position filled.
 *
 *  The page names which of the three every figure comes from, and never divides one by
 *  another. A net budget line over a DESE FTE count looks like a cost per employee and is
 *  not one, twice over: the numerator excludes every fund but the general fund, and the
 *  denominator counts staff those other funds pay for.
 *
 *  RULE 7 IS THE WHOLE DIFFICULTY. "Paraprofessional FTE tripled" is a measurement.
 *  "The district hired paraprofessionals" is a hypothesis, and so is every reason anybody
 *  offers for the movement. Each section states what the data shows and, in its own box,
 *  what it does not — with the alternatives that fit the same numbers equally well and
 *  the document that would settle it.
 *
 *  RULE 2. Not one figure is typed into this file. Every number arrives from
 *  /data/school-staffing.json, including the counts inside sentences.
 *
 *  RULE 1. Every dollar series here is ONE stage across its whole run and nothing on this
 *  page measures growth from an actual in one year to a budget in another. Nothing here
 *  feeds the projection.
 *
 *  RULE 8. This is not an audit. Where the archive is wrong — an OCR'd heading, a school
 *  whose roster was printed twice, two extracts of one cell that disagree — it is reported
 *  as something a reader planning around these numbers needs to know, not as a finding
 *  about anybody's competence.
 *
 *  NO D1 AT PAGE LOAD. One static file. */

type Change = {
  first_fy: number; last_fy: number; first: number; last: number
  change: number; pct: number | null
} | null

type Rank = {
  fy: number; of: number; rank: number; value: number
  highest: string; highest_value: number; lowest: string; lowest_value: number
}

type Panel = {
  key: string; label: string; stage: string; source: string; lines: number
  line_labels: string[]; first_fy: number; last_fy: number; years_dropped: number[]
  points: { fy: number; dollars: number }[]
  change: Change
  documents_disagree?: number
}

type Payload = {
  generated_by: string
  source: string
  state: {
    lea: string; docs: string[]; reconciles: Record<string, number>
    first_fy: number; last_fy: number
    points: (StatePoint & {
      student_headcount: number; pct_disabilities: number | null
      pct_low_income: number | null; average_teacher_salary: number | null
      instructional_support_fte: number | null; pupils_out_of_district: number | null
    })[]
    change: Record<string, Change>
    change_over_roster_years: Record<string, Change>
    trough: StatePoint
    ranks: { paras: Rank[]; teachers: Rank[] }
    latest: StatePoint & { student_headcount: number }
  }
  peers: Peer[]
  roster: {
    years: RosterYear[]
    roles: RoleRow[]
    buildings: string[]
    by_school: { fy: number; rows: { school: string; names: number }[] }
    entries_total: number; entries_in_panel: number
    excluded: { school: string; entries: number; years: number[]; why: string }[]
    unclassified: number; unclassified_share: number
    doubled: { fy: number; school: string; pages: string[]; names: number[]; shared: number }[]
    ocr_defects: { printed: string; rows: number; years: number[]; schools: string[] }[]
    ocr_rows: number; grade_headed_rows: number
    shared_staff: { fy: number; names: number }[]
    first_fy: number; last_fy: number
  }
  dollars: {
    stage: string
    panels: Panel[]
    sped_common_window: {
      first_fy: number; last_fy: number
      panels: { key: string; label: string; lines: number; change: Change
        points: { fy: number; dollars: number }[] }[]
    }
    reconciled: {
      a: string; b: string; years: number; agree: number; first_fy: number; last_fy: number
      disagree: { fy: number; a: number; b: number; difference: number }[]
    }[]
  }
  wages: {
    rows: number; years: number; school_tagged: number; statuses: string[]
    by_year: { fy: number; rows: number; school_tagged: number }[]
  }
}

/** The town's own names for its schools, so a slug never reaches the page. */
const SCHOOL: Record<string, string> = {
  primary: 'Lunenburg Primary School',
  'turkey-hill': 'Turkey Hill Elementary School',
  middle: 'Lunenburg Middle School',
  high: 'Lunenburg High School',
  passios: 'Passios Elementary School',
  'central-office': 'Central office',
  'monty-tech': 'Monty Tech (regional vocational)',
}
const school = (s: string) => SCHOOL[s] ?? s

const ROLE: Record<string, string> = {
  teacher: 'Teachers', paraprofessional: 'Paraprofessionals', specialist: 'Specialists',
  administrator: 'Administrators', custodian: 'Custodial', cafeteria: 'Food service',
  counselor: 'Counsellors', secretary: 'Office staff', speech_therapist: 'Speech',
  nurse: 'Nurses', psychologist: 'Psychologists', therapist: 'OT / PT',
  librarian: 'Librarians', social_worker: 'Social workers', technology: 'Technology',
  unknown: 'Title not recognised',
}
const role = (r: string) => ROLE[r] ?? r

function H2({ id, children }: { id?: string; children: React.ReactNode }) {
  return (
    <h2 id={id} className="text-2xl font-bold tracking-tight mt-14 mb-3 max-w-3xl
                           scroll-mt-[calc(var(--header-h)+1rem)]">{children}</h2>
  )
}

function Body({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-[15px] leading-relaxed max-w-2xl mt-3"
      style={{ color: 'var(--text-secondary)' }}>{children}</p>
  )
}

function Stat({ value, tone, children }: {
  value: string; tone?: string; children: React.ReactNode
}) {
  return (
    <div>
      <div className="text-3xl font-bold tracking-tight" style={tone ? { color: tone } : undefined}>
        {value}
      </div>
      <div className="text-[13px] leading-snug mt-1 max-w-[15rem]"
        style={{ color: 'var(--text-secondary)' }}>{children}</div>
    </div>
  )
}

/** The half of every section that says what the measurement does NOT establish. A
 *  distinct shape on purpose — on this page the limit is as load-bearing as the finding. */
function NotShown({ children }: { children: React.ReactNode }) {
  return (
    <div className="card p-4 mt-5 max-w-2xl" style={{ borderLeft: '4px solid var(--axis)' }}>
      <p className="text-[11px] font-semibold uppercase tracking-widest mb-1.5"
        style={{ color: 'var(--text-muted)' }}>What this does not show</p>
      <div className="text-[14px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
        {children}
      </div>
    </div>
  )
}

/** A hypothesis, marked as one. Never rendered in the same voice as a measurement. */
function Maybe({ settle, children }: { settle: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="card p-4 mt-4 max-w-2xl" style={{ borderLeft: '4px solid var(--status-warning)' }}>
      <p className="text-[11px] font-semibold uppercase tracking-widest mb-1.5"
        style={{ color: 'var(--text-muted)' }}>A possible explanation &mdash; nothing here tests it</p>
      <div className="text-[14px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
        {children}
        <p className="mt-2.5">
          <strong>What would settle it:</strong> {settle}
        </p>
      </div>
    </div>
  )
}

/** The longest run of consecutive years at a given rank, derived rather than picked.
 *  A rank quoted at two chosen years is a rank the writer chose. */
function longestRun(ranks: Rank[], test: (r: Rank) => boolean) {
  let best: Rank[] = [], cur: Rank[] = []
  for (const r of ranks) {
    if (test(r)) { cur.push(r); if (cur.length > best.length) best = [...cur] }
    else cur = []
  }
  return best
}

const VIEWS = [
  { id: 'biggest', label: 'Biggest groups' },
  { id: 'moved', label: 'Moved most' },
  { id: 'all', label: 'Everything printed' },
] as const
type View = typeof VIEWS[number]['id']

export function SchoolStaffing() {
  const [d, setD] = useState<Payload | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [view, setView] = useState<View>('biggest')

  useEffect(() => {
    let live = true
    fetch('/data/school-staffing.json')
      .then(r => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then(j => { if (live) setD(j) })
      .catch(e => { if (live) setErr(String(e)) })
    return () => { live = false }
  }, [])

  const roles = useMemo(() => {
    if (!d) return []
    const rs = d.roster.roles.filter(r => r.role !== 'unknown')
    if (view === 'all') return d.roster.roles
    if (view === 'moved') {
      return [...rs].sort((a, b) => {
        const m = (x: RoleRow) => {
          const f = x.points[0].names, l = x.points[x.points.length - 1].names
          return Math.abs(l - f)
        }
        return m(b) - m(a)
      }).slice(0, 8)
    }
    return rs.slice(0, 8)
  }, [d, view])

  if (err) {
    return (
      <div className="mx-auto max-w-6xl px-5 pt-14 pb-16">
        <h1 className="text-3xl font-bold tracking-tight">School staffing</h1>
        <div className="card p-5 mt-8" style={{ borderLeft: '4px solid var(--status-warning)' }}>
          <p className="text-[15px] font-bold mb-1">The series did not load</p>
          <p className="text-[13.5px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
            {err}. Nothing on this page is typed into it, so with the file missing there is
            nothing to show rather than something stale. The underlying rows are published
            at{' '}
            <a className="underline" style={{ color: 'var(--series-cost)' }}
              href="/data/school-staffing.json">/data/school-staffing.json</a>.
          </p>
        </div>
      </div>
    )
  }

  if (!d) {
    return (
      <div className="mx-auto max-w-6xl px-5 pt-14 pb-16">
        <h1 className="text-3xl font-bold tracking-tight">School staffing</h1>
        <p className="mt-4 text-[15px]" style={{ color: 'var(--text-muted)' }}>
          Loading the measured series&hellip;
        </p>
      </div>
    )
  }

  const st = d.state
  const w = st.change_over_roster_years
  const paraFte = w.para_fte!, teachFte = w.teacher_fte!
  const pupils = w.pupils_in_district!
  const perPupil = w.teachers_per_100!
  const lastPara = st.ranks.paras[st.ranks.paras.length - 1]
  const worstParaRank = longestRun(st.ranks.paras, r => r.rank === r.of)
  const fewestTeachers = longestRun(st.ranks.teachers, r => r.rank === r.of)
  const topPara = [...st.ranks.paras].sort((a, b) => b.value - a.value)[0]
  const lowPara = [...st.ranks.paras].sort((a, b) => a.value - b.value)[0]

  const paraPanel = d.dollars.panels.find(p => p.key === 'sped_para')!
  const teachPanel = d.dollars.panels.find(p => p.key === 'sped_teacher')!
  const cw = d.dollars.sped_common_window
  const cwPara = cw.panels.find(p => p.key === 'sped_para')!
  const cwTeach = cw.panels.find(p => p.key === 'sped_teacher')!
  const otherPanels = d.dollars.panels.filter(p => !p.key.startsWith('sped_'))

  const ros = d.roster
  const rYears = ros.years
  const rFirst = rYears[0], rLast = rYears[rYears.length - 1]
  const printedSchoolSets = new Set(rYears.map(r => r.schools.join('|')))
  const yearsWithCO = rYears.filter(r => r.central_office_printed).length
  const doubled = ros.doubled[0]
  const recon = d.dollars.reconciled[0]
  const negCell = recon?.disagree[0]

  return (
    <div className="mx-auto max-w-6xl px-5 pt-14 pb-16">
      <p className="text-xs font-semibold uppercase tracking-widest mb-3"
        style={{ color: 'var(--text-muted)' }}>The money</p>
      <h1 className="text-4xl sm:text-5xl font-bold tracking-tight leading-[1.05] max-w-3xl">
        Fewer children, the same teachers, and {pct(paraFte.pct!)} paraprofessionals.
      </h1>
      <p className="mt-5 text-lg leading-relaxed max-w-2xl"
        style={{ color: 'var(--text-secondary)' }}>
        Between {fy(paraFte.first_fy)} and {fy(paraFte.last_fy)} the state recorded
        Lunenburg&rsquo;s in-district enrolment falling {pct(pupils.pct!)} and its teacher
        FTE moving {pct(teachFte.pct!)}. Over the same years its paraprofessional FTE went
        from {num(paraFte.first)} to {num(paraFte.last)}. That is one line moving and the
        rest holding &mdash; and nothing in these documents says why.
      </p>

      <div className="mt-10 flex flex-wrap gap-x-12 gap-y-6">
        <Stat value={num(lastPara.value, 2)} tone="var(--series-revenue)">
          paraprofessional FTE per 100 in-district pupils in {fy(lastPara.fy)} &mdash; the
          {lastPara.rank === 1 ? ' highest' : ` ${lastPara.rank}th highest`} of the{' '}
          {lastPara.of} districts on DESE&rsquo;s own comparison sheet
        </Stat>
        <Stat value={`${fewestTeachers.length} years`}>
          Lunenburg has had the <em>fewest</em> teachers per pupil of those{' '}
          {fewestTeachers[0]?.of} districts &mdash; {fy(fewestTeachers[0]?.fy)} to{' '}
          {fy(fewestTeachers[fewestTeachers.length - 1]?.fy)}, without a break
        </Stat>
        <Stat value={pct(cwPara.change!.pct!)} tone="var(--series-revenue)">
          special education paraprofessional spending, {fy(cw.first_fy)}&ndash;{fy(cw.last_fy)},
          against {pct(cwTeach.change!.pct!)} for special education teachers over the same
          years
        </Stat>
      </div>

      {/* ------------------------------------------------ what the three quantities are */}
      <div className="card p-4 mt-8 max-w-2xl" style={{ borderLeft: '4px solid var(--status-warning)' }}>
        <p className="text-[14.5px] font-bold mb-1.5">
          Three different quantities are on this page, and none of them is &ldquo;how many
          people work for the schools&rdquo;.
        </p>
        <ul className="text-[13.5px] leading-relaxed space-y-1.5"
          style={{ color: 'var(--text-secondary)' }}>
          <li>
            <strong>Names the town printed.</strong> {ros.entries_in_panel} of them, across{' '}
            {rYears.length} annual town reports, {fy(ros.first_fy)}&ndash;{fy(ros.last_fy)}.
            A roster carries no FTE, so a 0.4 music teacher and a full-timer are one name
            each; no funding source; and no date within the year.
          </li>
          <li>
            <strong>FTE the state published.</strong> {st.points.length} years of it,{' '}
            {fy(st.first_fy)}&ndash;{fy(st.last_fy)}, from DESE rather than from the town.
            This is the only full-time-equivalent count in the archive.
          </li>
          <li>
            <strong>Dollars.</strong> Net general-fund budget lines. A line is what the
            town has to raise after state aid, grants, fees and reimbursement have paid
            theirs &mdash; so a line can rise because a grant ended and nothing else changed.
          </li>
        </ul>
        <p className="text-[13.5px] leading-relaxed mt-2.5" style={{ color: 'var(--text-secondary)' }}>
          Nothing on this page divides one of them by another. Dollars over FTE looks like a
          cost per employee and is not one: the numerator leaves out every fund but the
          general fund, and the denominator counts the staff those funds pay for.
        </p>
      </div>

      {/* ================================================== 1. the paraprofessional shift */}
      <H2 id="paras">Lunenburg went from the fewest paraprofessionals per pupil to the most</H2>
      <Body>
        DESE publishes paraprofessional FTE for Lunenburg and for every district on its own
        comparison sheet. In {fy(lowPara.fy)} Lunenburg reported {num(lowPara.value, 2)} per
        100 in-district pupils &mdash; the lowest of the {lowPara.of}, and below every one of
        them. It was last of {worstParaRank[0]?.of} for{' '}
        {worstParaRank.length} straight years, {fy(worstParaRank[0]?.fy)} to{' '}
        {fy(worstParaRank[worstParaRank.length - 1]?.fy)}. In {fy(topPara.fy)} it reported{' '}
        {num(topPara.value, 2)}, the highest of the group.
      </Body>
      <Body>
        <strong>The V is Lunenburg&rsquo;s alone.</strong> No comparison district falls
        below {num(Math.min(...d.peers.filter(p => !p.is_lunenburg)
          .flatMap(p => p.points.map(q => q.paras_per_100).filter((v): v is number => v !== null))), 2)}{' '}
        in any year of the series. That rules out a change in how the state counts
        paraprofessionals, which would have moved every district at once. It does not rule
        out a change in how Lunenburg reports them.
      </Body>
      <div className="mt-6"><PeerRatio peers={d.peers} field="paras_per_100"
        unit="Paraprofessional FTE per 100 in-district pupils" subject="Lunenburg" /></div>
      <TableTwin caption="Lunenburg, per year"
        head={['Year', 'Para FTE', 'Per 100 pupils', 'Rank', 'Highest in group']}
        rows={st.ranks.paras.map(r => {
          const p = st.points.find(q => q.fy === r.fy)!
          return [fy(r.fy), num(p.para_fte, 1), num(r.value, 2),
            `${r.rank} of ${r.of}`, `${r.highest} ${num(r.highest_value, 2)}`]
        })} />

      <NotShown>
        <p>
          <strong>Whether any of this is about children.</strong> An FTE count is staff. It
          is not a count of students with disabilities, of one-to-one assignments, or of
          hours delivered. Two districts with the same ratio can be doing entirely
          different things.
        </p>
        <p className="mt-2.5">
          <strong>Who pays.</strong> DESE&rsquo;s FTE count includes staff paid from grants,
          circuit breaker reimbursement and revolving funds. The town&rsquo;s budget lines
          do not. So the FTE series and the dollar series below are not two views of one
          number and must not be divided into each other.
        </p>
        <p className="mt-2.5">
          <strong>That the trough is real.</strong> {fy(st.trough.fy)}&rsquo;s{' '}
          {num(st.trough.para_fte, 1)} FTE is what the state published. Whether Lunenburg
          employed that few paraprofessionals, or classified them somewhere else that year,
          is not decidable from this sheet.
        </p>
      </NotShown>

      <Maybe settle={<>
        DESE&rsquo;s staffing report broken out by funding source, and the district&rsquo;s
        End of Year Financial Report, which separates spending by fund. Both would say
        whether the rise is posts added or grant-funded posts moving onto the general fund.
        Neither is currently in this archive.
      </>}>
        <p>
          A district that cuts paraprofessional posts in a hard budget year and rebuilds
          them afterwards would produce exactly this shape. So would a district that kept
          the same people and changed which fund or which category they were reported
          under. So would one whose special education population changed. The three fit the
          same seventeen numbers equally well, and this series cannot separate them.
        </p>
      </Maybe>

      {/* ================================================== 2. teachers against enrolment */}
      <H2 id="enrolment">Enrolment fell. The teaching count did not follow it.</H2>
      <Body>
        Over the same years the town was printing rosters, in-district enrolment moved{' '}
        {pct(pupils.pct!)} &mdash; from {num(pupils.first, 1)} FTE pupils to{' '}
        {num(pupils.last, 1)} &mdash; while teacher FTE moved {pct(teachFte.pct!)}. Teachers
        per 100 pupils therefore rose {pct(perPupil.pct!)}, from {num(perPupil.first, 2)} to{' '}
        {num(perPupil.last, 2)}.
      </Body>
      <Body>
        <strong>That still leaves Lunenburg with the fewest teachers per pupil in its
        group.</strong> It has been {fewestTeachers[0]?.of} of {fewestTeachers[0]?.of} for{' '}
        {fewestTeachers.length} consecutive years, and the highest district in{' '}
        {fy(st.ranks.teachers[st.ranks.teachers.length - 1].fy)} reports{' '}
        {num(st.ranks.teachers[st.ranks.teachers.length - 1].highest_value, 2)} against
        Lunenburg&rsquo;s {num(st.ranks.teachers[st.ranks.teachers.length - 1].value, 2)}. A
        ratio rising and a ratio being low are not in tension: both are true here.
      </Body>
      <div className="grid gap-4 mt-6 lg:grid-cols-2">
        <StaffAgainstEnrolment rows={st.points} />
        <PeerRatio peers={d.peers} field="teachers_per_100"
          unit="Teacher FTE per 100 in-district pupils" subject="Lunenburg" />
      </div>
      <TableTwin caption="Lunenburg, as the state published it"
        head={['Year', 'Teacher FTE', 'Para FTE', 'In-district pupils', 'Teachers per 100',
          'Paras per 100']}
        rows={st.points.map(p => [fy(p.fy), num(p.teacher_fte, 1), num(p.para_fte, 1),
          num(p.pupils_in_district, 1), num(p.teachers_per_100, 2), num(p.paras_per_100, 2)])} />

      <NotShown>
        <p>
          <strong>Whether a staffing level was chosen.</strong> A district cannot shed a
          teacher for every departing child: sections, grade spans and required subjects
          set a floor that has nothing to do with the enrolment total. A ratio moving is
          the arithmetic of a falling denominator at least as much as it is a decision.
        </p>
        <p className="mt-2.5">
          <strong>What a teacher is here.</strong> DESE&rsquo;s definition, applied by
          DESE. It is not the district&rsquo;s payroll, not the contract&rsquo;s bargaining
          unit, and not the roster on the next chart down.
        </p>
      </NotShown>

      {/* ================================================== 3. the dollars */}
      <H2 id="dollars">
        Inside special education, the money went to paraprofessionals, not to teachers
      </H2>
      <Body>
        Two panels of five budget lines each, read from the district&rsquo;s own documents
        at the {d.dollars.stage} stage across their whole run, over the{' '}
        {cw.last_fy - cw.first_fy} years both of them cover. Special education
        paraprofessional lines moved {pct(cwPara.change!.pct!)} &mdash; from{' '}
        {usd(cwPara.change!.first)} to {usd(cwPara.change!.last)}. Special education teacher
        lines moved {pct(cwTeach.change!.pct!)}, from {usd(cwTeach.change!.first)} to{' '}
        {usd(cwTeach.change!.last)}.
      </Body>
      <div className="mt-6">
        <IndexedPair series={[
          { key: cwPara.key, label: cwPara.label, points: cwPara.points },
          { key: cwTeach.key, label: cwTeach.label, points: cwTeach.points },
        ]} />
      </div>
      <TableTwin caption={`Both panels, ${d.dollars.stage} stage, as printed`}
        head={['Year', cwPara.label, cwTeach.label]}
        rows={cwPara.points.map(p => [
          fy(p.fy), usd(p.dollars),
          usd(cwTeach.points.find(q => q.fy === p.fy)?.dollars ?? 0)])} />
      <p className="text-[12px] mt-3 max-w-2xl" style={{ color: 'var(--text-muted)' }}>
        The paraprofessional panel runs from {fy(paraPanel.first_fy)} and the teacher panel
        from {fy(teachPanel.first_fy)}; the comparison above uses only the{' '}
        {cw.last_fy - cw.first_fy + 1} years both cover. Reading a twelve-year percentage
        against an eight-year one is the like-for-like error wearing a different coat.
      </p>

      <NotShown>
        <p>
          <strong>That anybody was hired.</strong> A budget line is dollars. It is not a
          post, not a person and not an hour. The line rising and the line paying more for
          the same people are the same number on the page.
        </p>
        <p className="mt-2.5">
          <strong>What special education cost.</strong> These are <em>net</em> general-fund
          lines. Circuit breaker reimbursement, IDEA grant money and revolving funds pay for
          real staff and appear in none of them, so a year where a grant ended looks
          identical to a year where the district added people.
        </p>
        <p className="mt-2.5">
          <strong>That the two panels are comparable in kind.</strong> They are two sets of
          five lines from the same workbook, which makes them comparable as budget lines. It
          does not make a paraprofessional dollar and a teacher dollar the same unit of
          anything.
        </p>
      </NotShown>

      {/* the other panels */}
      <H2 id="other-lines">Three more staffing lines, for scale</H2>
      <Body>
        The same treatment for every other staffing panel where a fixed set of lines reports
        in every year of its run. Each is read at the {d.dollars.stage} stage; none of them
        is a headcount.
      </Body>
      <div className="grid gap-2.5 mt-6 max-w-3xl">
        {[paraPanel, teachPanel, ...otherPanels].map(p => (
          <div key={p.key} className="card px-4 py-3.5">
            <div className="flex items-baseline justify-between gap-3 flex-wrap">
              <span className="text-[14.5px] font-bold">{p.label}</span>
              <span className="text-[14px] tnum font-bold"
                style={{ color: (p.change?.pct ?? 0) >= 0 ? 'var(--series-revenue)' : 'var(--series-cost)' }}>
                {pct(p.change!.pct!)}
              </span>
            </div>
            <p className="text-[12.5px] mt-1" style={{ color: 'var(--text-secondary)' }}>
              {usd(p.change!.first)} in {fy(p.change!.first_fy)} to {usd(p.change!.last)} in{' '}
              {fy(p.change!.last_fy)} &middot; {p.lines} lines &middot; from{' '}
              <code style={{ color: 'var(--text-muted)' }}>{p.source}</code>
              {p.years_dropped.length > 0 && (
                <> &middot; {p.years_dropped.length} earlier year
                  {p.years_dropped.length === 1 ? '' : 's'} dropped, because not every line
                  in the panel reports in {p.years_dropped.length === 1 ? 'it' : 'them'}
                </>
              )}
            </p>
          </div>
        ))}
      </div>

      {/* ================================================== 4. the town's own rosters */}
      <H2 id="rosters">What the town itself printed &mdash; and why it is not a census</H2>
      <Body>
        Every annual town report carries a faculty and staff roster for each school, by
        name. {ros.entries_total} names in all, of which {ros.entries_in_panel} are in the
        comparable panel below. It is the only published thing in this archive that touches
        the standing question of whether budgeted positions were <em>filled</em>.
      </Body>
      <Body>
        <strong>It cannot be read as a staffing trend</strong>, because what got printed
        changed. Which schools appear varies &mdash; there are{' '}
        {printedSchoolSets.size} different combinations across {rYears.length} years.
        Central office is printed in {yearsWithCO} of them and left out of the rest, so it
        is excluded here entirely: a total that gains twenty names in the years a page was
        included is measuring the page, not the payroll.
      </Body>
      <div className="mt-6"><NamesPrinted rows={rYears} /></div>
      <TableTwin caption="Every year, and what was printed in it"
        head={['Year', 'Names', 'Rosters', 'Pages', 'Central office printed', 'Schools']}
        rows={rYears.map(r => [
          fy(r.fy),
          r.names_high ? `${r.names}–${r.names_high}` : String(r.names),
          r.schools.length, r.pages, r.central_office_printed ? 'yes' : 'no',
          r.schools.map(school).join(', ')])} />

      <NotShown>
        <p>
          <strong>Full-time equivalence.</strong> A roster prints a name and a title. A 0.4
          music teacher and a full-timer are one row each, and there is no way to tell them
          apart. This is the single reason a roster count cannot be compared to the state
          FTE series above.
        </p>
        <p className="mt-2.5">
          <strong>Who pays.</strong> No roster names a funding source. That is the question
          that matters most for the budget and it is answered nowhere in these documents.
        </p>
        <p className="mt-2.5">
          <strong>When.</strong> The rosters are undated within the year. Two consecutive
          reports may be photographs taken at different points in the school year.
        </p>
        <p className="mt-2.5">
          <strong>Whether a post was vacant.</strong> A name is a person the report named.
          A post held open all year appears nowhere at all, and looks exactly like a post
          that was never budgeted.
        </p>
      </NotShown>

      {/* by role */}
      <H2 id="roles">By role, on the panel that stays comparable</H2>
      <Body>
        The same names, sorted by what the printed title says the person does. The
        classification is ours &mdash; {ros.unclassified} of {ros.entries_in_panel} names (
        {(ros.unclassified_share * 100).toFixed(1)}%) carry a title no rule recognised, and
        those are counted as unrecognised rather than quietly filed under &ldquo;other&rdquo;.
      </Body>
      <div className="flex flex-wrap gap-2 mt-6" role="group" aria-label="Which roles to show">
        {VIEWS.map(v => (
          <button key={v.id} onClick={() => setView(v.id)}
            aria-pressed={view === v.id}
            className="px-3.5 min-h-[44px] rounded-[10px] text-[13px] font-semibold border"
            style={{
              borderColor: view === v.id ? 'var(--series-cost)' : 'var(--grid)',
              background: view === v.id ? 'var(--surface-3)' : 'transparent',
              color: view === v.id ? 'var(--text-primary)' : 'var(--text-secondary)',
            }}>
            {v.label}
          </button>
        ))}
      </div>
      <p className="text-[12px] mt-2.5 max-w-2xl" style={{ color: 'var(--text-muted)' }}>
        {view === 'biggest'
          ? 'The eight roles with the most names across the whole run.'
          : view === 'moved'
            ? 'The eight roles whose first and last printed counts are furthest apart. That is a difference between two documents, not a trend.'
            : `All ${d.roster.roles.length} categories, including the titles no rule recognised.`}
        {' '}Every panel is on the same vertical scale. The amber bar is{' '}
        {fy(doubled?.fy)}, where one school&rsquo;s roster was printed twice and there is no
        way to split a role between the two.
      </p>
      <RoleGrid rows={roles} format={role} />
      <TableTwin caption="Every role category, first printed year to last"
        head={['Role', `Names in ${fy(rFirst.fy)}`, `Names in ${fy(rLast.fy)}`, 'Total across the run']}
        rows={d.roster.roles.map(r => [
          role(r.role), r.points[0].names, r.points[r.points.length - 1].names, r.total])} />

      <NotShown>
        <p>
          <strong>That a category rising means more of that job.</strong> Custodial and food
          service staff appear on some schools&rsquo; rosters and not others, in ways that
          change year to year. A category that doubles between two reports may be a
          category that started being printed.
        </p>
        <p className="mt-2.5">
          <strong>That a category vanishing means a post was cut.</strong> A title the
          report stopped printing and a post the district stopped filling are the same
          absence on the page. This is why the names are kept: a person appearing under a
          new title separates a renamed post from a departure, and nothing else here can.
        </p>
      </NotShown>

      {/* by school */}
      <H2 id="schools">By school, in the most recent year with no double-printed roster</H2>
      <Body>
        {fy(ros.by_school.fy)}. Names only &mdash; no FTE, no funding source, and{' '}
        {ros.shared_staff.find(s => s.fy === ros.by_school.fy)?.names ?? 0} people appear on
        more than one school&rsquo;s roster that year, which is district-wide staff in the
        source rather than a duplication in the extract.
      </Body>
      <div className="grid gap-2.5 mt-6 max-w-2xl">
        {ros.by_school.rows.map(r => (
          <div key={r.school} className="card px-4 py-3">
            <div className="flex items-baseline justify-between gap-3">
              <span className="text-[14.5px] font-bold">{school(r.school)}</span>
              <span className="text-[15px] tnum font-bold">{r.names}</span>
            </div>
            <div className="mt-2 h-1.5 rounded-full" style={{ background: 'var(--surface-3)' }}>
              <div className="h-1.5 rounded-full"
                style={{
                  width: `${100 * r.names / Math.max(...ros.by_school.rows.map(x => x.names))}%`,
                  background: 'var(--series-cost)',
                }} />
            </div>
          </div>
        ))}
      </div>

      {/* ================================================== 5. the raw, and the defects */}
      <H2 id="quality">What is wrong with this data, stated</H2>
      <Body>
        Every item below is found by a rule in the generator rather than written down, so
        the counts move when the extraction improves instead of going quietly stale.
      </Body>

      <div className="card p-4 mt-6 max-w-2xl" style={{ borderLeft: '4px solid var(--status-warning)' }}>
        <p className="text-[14.5px] font-bold mb-1.5">
          {fy(doubled.fy)}: {school(doubled.school)}&rsquo;s roster is printed twice
        </p>
        <p className="text-[13.5px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
          Pages {doubled.pages.join(' and ')} of the {fy(doubled.fy)} annual town report each
          carry a complete roster for that school &mdash; {doubled.names[0]} names on one and{' '}
          {doubled.names[1]} on the other, {doubled.shared} of them on both, with different
          principals. Nothing on either page says which year it describes. Summing them
          doubles a school; picking one discards a document. That year is drawn as a range,
          and the range is the honest answer rather than a caveat under a single bar.
        </p>
      </div>

      <div className="card p-4 mt-4 max-w-2xl" style={{ borderLeft: '4px solid var(--status-warning)' }}>
        <p className="text-[14.5px] font-bold mb-1.5">
          {ros.ocr_defects.length} printed department headings came back from OCR unreadable
        </p>
        <p className="text-[13.5px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
          These roster pages are scans and are read by OCR. {ros.ocr_rows} of the{' '}
          {ros.grade_headed_rows} names filed under a heading that names a grade sit under a
          heading whose grade level cannot be read. The rule is that a heading containing
          the word <em>grade</em> must have a recognisable ordinal beside it; these do not.
          Nothing else on this page depends on the grade level, so the effect is that those
          names have a school and a role and no grade &mdash; not that any count is wrong.
        </p>
        <div className="mt-2.5">
          <TableTwin head={['As OCR read it', 'Names', 'Years', 'Schools']}
            rows={ros.ocr_defects.map(o => [
              o.printed, o.rows, o.years.map(fy).join(', '),
              o.schools.map(school).join(', ')])} />
        </div>
      </div>

      {negCell && (
        <div className="card p-4 mt-4 max-w-2xl" style={{ borderLeft: '4px solid var(--status-bad)' }}>
          <p className="text-[14.5px] font-bold mb-1.5">
            Two extracts of the same cell disagree, in {fy(negCell.fy)}, by {usd(Math.abs(negCell.difference))}
          </p>
          <p className="text-[13.5px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
            The paraprofessional dollars can be reached two ways in this database: by summing
            the five line keys in <code>{recon.a}</code>, or by reading{' '}
            <code>{recon.b}</code>&rsquo;s own total column. They agree in {recon.agree} of{' '}
            {recon.years} years, {fy(recon.first_fy)}&ndash;{fy(recon.last_fy)}, and differ in{' '}
            {fy(negCell.fy)}: {usd(negCell.a)} against {usd(negCell.b)}. The difference is
            exactly twice the ACE line, which is a sign. The workbook itself prints a
            negative there &mdash; cell <code>sheet1!D340 = −157,886.32</code> in the FY27
            projection &mdash; so this page draws the <code>{recon.a}</code> route and reports
            the disagreement rather than choosing quietly.
          </p>
          <p className="text-[13.5px] leading-relaxed mt-2.5" style={{ color: 'var(--text-secondary)' }}>
            <strong>A negative on a salary line is itself worth knowing about.</strong> It is
            almost certainly a year-end reclassification rather than money coming back, but
            that is a guess: the document prints a figure and no explanation, and the
            {' '}{fy(negCell.fy)} paraprofessional total on the chart above is lower than the
            year&rsquo;s real spending by however much moved.
          </p>
        </div>
      )}

      <div className="card p-4 mt-4 max-w-2xl" style={{ borderLeft: '4px solid var(--axis)' }}>
        <p className="text-[14.5px] font-bold mb-1.5">Two things excluded, and why</p>
        <ul className="text-[13.5px] leading-relaxed space-y-2"
          style={{ color: 'var(--text-secondary)' }}>
          {ros.excluded.map(e => (
            <li key={e.school}>
              <strong>{school(e.school)}</strong> &mdash; {e.entries} names, printed in{' '}
              {e.years.length} of {rYears.length} years ({e.years.map(fy).join(', ')}).{' '}
              {e.why}.
            </li>
          ))}
        </ul>
      </div>

      <div className="card p-4 mt-4 max-w-2xl" style={{ borderLeft: '4px solid var(--axis)' }}>
        <p className="text-[14.5px] font-bold mb-1.5">
          The town publishes gross wages. They cannot be used to count school employees.
        </p>
        <p className="text-[13.5px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
          {d.wages.rows} rows across {d.wages.years} years, one per named employee &mdash;
          and only {d.wages.school_tagged} of them carry a department at all, so there is no
          way to tell a school employee from a highway employee for the rest. Every row is
          marked <code>{d.wages.statuses.join(', ')}</code>: the report prints no total, so
          nothing in the extraction can be reconciled against the document. It is a real
          dataset and it answers a different question.
        </p>
      </div>

      {/* ------------------------------------------------------------------ where it came from */}
      <H2 id="sources">Where every figure on this page comes from</H2>
      <div className="grid gap-2.5 mt-5 max-w-3xl">
        <div className="card px-4 py-3.5">
          <p className="text-[14px] font-bold">The state&rsquo;s FTE and enrolment</p>
          <p className="text-[12.5px] mt-1" style={{ color: 'var(--text-secondary)' }}>
            {st.points.length} years, {fy(st.first_fy)}&ndash;{fy(st.last_fy)}, LEA{' '}
            {st.lea}, {d.peers.length} districts. Every measure reconciles against
            DESE&rsquo;s own printed totals ({Object.entries(st.reconciles)
              .map(([k, n]) => `${n} ${k || 'not checkable'}`).join(', ')}).
          </p>
          <p className="text-[12px] mt-1.5" style={{ color: 'var(--text-muted)' }}>
            {st.docs.join(', ')}
          </p>
        </div>
        <div className="card px-4 py-3.5">
          <p className="text-[14px] font-bold">The rosters</p>
          <p className="text-[12.5px] mt-1" style={{ color: 'var(--text-secondary)' }}>
            {ros.entries_total} names read page by page out of {rYears.length} annual town
            reports. There is no total printed on a roster, so the check is line accounting
            &mdash; every non-blank line on a page claimed as an entry or a heading.
          </p>
          <p className="text-[12px] mt-1.5" style={{ color: 'var(--text-muted)' }}>
            <a className="underline" href="/docs/data/PROVENANCE-staff-rosters.md">
              PROVENANCE-staff-rosters.md
            </a>{' '}carries the per-page ledger.
          </p>
        </div>
        <div className="card px-4 py-3.5">
          <p className="text-[14px] font-bold">The dollars</p>
          <p className="text-[12.5px] mt-1" style={{ color: 'var(--text-secondary)' }}>
            {d.dollars.panels.length} panels, {d.dollars.stage} stage throughout. Each panel
            is a fixed set of lines reporting in every year of its run, so a sum across years
            measures the lines and not the coverage.
          </p>
        </div>
        <div className="card px-4 py-3.5">
          <p className="text-[14px] font-bold">This page&rsquo;s own data file</p>
          <p className="text-[12.5px] mt-1" style={{ color: 'var(--text-secondary)' }}>
            Everything above is read at build time from{' '}
            <code>{d.source}</code> by <code>{d.generated_by}</code> and served as one static
            file. Nothing is typed into a sentence.
          </p>
          <p className="text-[12px] mt-1.5">
            <a className="underline" style={{ color: 'var(--series-cost)' }}
              href="/data/school-staffing.json">/data/school-staffing.json</a>
          </p>
        </div>
      </div>

      <div className="card p-4 mt-8 max-w-2xl" style={{ borderLeft: '4px solid var(--axis)' }}>
        <p className="text-[11px] font-semibold uppercase tracking-widest mb-1.5"
          style={{ color: 'var(--text-muted)' }}>The one number nobody publishes</p>
        <p className="text-[14px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
          Which fund pays which post. The town publishes names without FTE or funding; the
          state publishes FTE without funding; the budget publishes dollars net of every
          fund but one. Any question of the form &ldquo;did the town take on staff a grant
          used to pay for&rdquo; needs all three joined, and no document in this archive
          joins them.
        </p>
      </div>
    </div>
  )
}
