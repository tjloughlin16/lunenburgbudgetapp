import type { Tab } from '../routes'
import { abs } from '../lib/abs'
import { useEffect, useMemo, useState } from 'react'
import {
  NamesPrinted, RoleGrid, TableTwin, HeadcountAgainstFte, PeerHeadcount, SchoolBoard,
  fy, num,
  type RoleRow,
} from '../components/StaffingCharts'
import {
  role, school,
  type Board, type Composition, type Headcount, type Peer, type Roster, type State,
  type Wages,
} from '../lib/staffing'
import {
  Conclusions, Coverage, Grain, NotEstablished, Provenance, Quote, MoreReports,
  Body, H2, H3, Maybe, NotShown, Stat,
  ReportShell,
} from '../components/report'
import type { Base, Conclusion } from '../components/report'

const TAB: Tab = 'schoolstaff'
const DATA = '/data/who-works-in-each-school.json'
const TITLE = 'Who works in each school'

/** Who works in each of the four schools — three instruments, kept apart.
 *
 *  WHY THIS PAGE EXISTS. A resident does not live in a district. They have a child at one
 *  building, and the question they arrive with is who is in it. Three separate records
 *  touch that and a reader will assume they are one thing:
 *
 *    1. NAMES the town printed — a faculty roster per school in every annual town report.
 *       No FTE, no funding source, undated within the year. A count of these is a count of
 *       names the town printed. It is a real quantity and it is not a staffing level.
 *    2. FTE the STATE published — full-time-equivalent TEACHING posts, at school level.
 *       DESE publishes this for teachers and for nobody else.
 *    3. HEADCOUNT the state published — PEOPLE, counted once each, by job classification,
 *       for three years only.
 *
 *  The page names which of the three every figure comes from and never divides one by
 *  another, with one exception it labels everywhere: headcount into FTE, which is two
 *  counts of staff from the same publisher and gives the average share of a post.
 *
 *  THE CAVEAT THAT IS THIS PAGE'S OWN: a roster is not a census. Sister pages carry the
 *  other two — /school-staffing for the window the sign of any staffing change depends
 *  on, and /the-paraprofessionals for rule 11 and the money.
 *
 *  RULE 2. Not one figure is typed into this file.
 *
 *  NO D1 AT PAGE LOAD. One static file. */

type Payload = Base & {
  conclusions: Conclusion[]
  generated_by: string
  source: string
  board: Board
  composition: Composition
  headcount: Headcount
  roster: Roster
  state: State
  peers: Peer[]
  wages: Wages
}

const VIEWS = [
  { id: 'biggest', label: 'Biggest groups' },
  { id: 'moved', label: 'Moved most' },
  { id: 'all', label: 'Everything printed' },
] as const
type View = typeof VIEWS[number]['id']

export function WhoWorksInEachSchool() {
  const [d, setD] = useState<Payload | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [view, setView] = useState<View>('biggest')

  useEffect(() => {
    let live = true
    fetch(DATA)
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

  if (err) return <ReportShell tab={TAB} title={TITLE} dataUrl={DATA} err={err} />

  if (!d) return <ReportShell tab={TAB} title={TITLE} dataUrl={DATA} loading />

  const st = d.state
  const ros = d.roster
  const rYears = ros.years
  const rFirst = rYears[0], rLast = rYears[rYears.length - 1]
  const printedSchoolSets = new Set(rYears.map(r => r.schools.join('|')))
  const yearsWithCO = rYears.filter(r => r.central_office_printed).length
  const doubled = ros.doubled[0]

  const comp = d.composition
  const support = comp.not_counted.roster.roles
  const prog = comp.programme.rows
  const hc = d.headcount
  const hcLast = hc.vs_fte[hc.vs_fte.length - 1]
  const paraChurn = hc.churn.filter(c => c.job_class === 'Paraprofessional'
    && c.retained_pct !== null)
  const lastParaChurn = paraChurn[paraChurn.length - 1]
  const otherLicensed = hc.churn.filter(c => c.job_class === 'Other - Licensed'
    && c.retained_pct !== null).slice(-1)[0]
  const teacherRetained = otherLicensed
    ? hc.churn.find(c => c.job_class === 'Teacher' && c.fy === otherLicensed.fy)
    : undefined
  // The interstitial era, READ rather than named: the last year Lunenburg High held a
  // grade the enrolment file no longer puts there, taken off the panels themselves.
  const oldEra = (() => {
    const fyy = d.board.breaks[0]?.last_fy ?? d.board.first_fy
    const ps = d.board.by_fy[String(fyy)] || []
    return {
      fy: fyy,
      primary: ps.find(x => x.school === 'primary')?.grade_span || '—',
      high: ps.find(x => x.school === 'high')?.grade_span || '—',
    }
  })()
  const board = d.board
  const xc = d.board.cross_check
  const highBand = d.board.band_era_evidence.schools.find(
    r => r.school === 'high' && r.band === 'grade_6_8_fte' && r.taught.length > 0)

  return (
    <ReportShell tab={TAB} dataUrl={DATA}
      title={<>
        Who works in each of the four schools, {fy(ros.first_fy)} to {fy(ros.last_fy)}.
      </>}
      standfirst={<>
        {ros.entries_total.toLocaleString()} names, beside the children and the teaching
        posts the state
        counts in the same buildings &mdash; three instruments, never added together.
      </>}
    >

      <Grain>{d.grain}</Grain>

      <div className="mt-10 flex flex-wrap gap-x-12 gap-y-6">
        <Stat value={ros.entries_total.toLocaleString()}>
          names the town printed on a school staff roster, across {rYears.length} annual
          town reports, {fy(ros.first_fy)}&ndash;{fy(ros.last_fy)}
        </Stat>
        <Stat value={`${num(hcLast.teacher_headcount, 0)} people`}>
          teaching in Lunenburg in {fy(hcLast.fy)}, holding{' '}
          {num(hcLast.teacher_fte, 1)} full-time equivalent posts between them
        </Stat>
        <Stat value={`${num(hcLast.teacher_share, 2)} FTE each`} tone="var(--series-cost)">
          posts per teaching person, averaged across the whole job class &mdash; two
          people at three quarters and one full-timer beside one half-timer give the same
          figure. It was {num(hc.vs_fte[0].teacher_share, 2)} in {fy(hc.vs_fte[0].fy)}
        </Stat>
        <Stat value={`${xc.flagged} of ${xc.compared}`} tone="var(--series-cost)">
          school-years, of those with both records, in which the town printed{' '}
          <em>fewer teaching names</em> than the
          state counts teaching posts &mdash; which document is short is not established
        </Stat>
        <Stat value={`${ros.unclassified.toLocaleString()} of ${ros.entries_in_panel.toLocaleString()}`}>
          printed titles no classification rule recognised &mdash;{' '}
          {(ros.unclassified_share * 100).toFixed(1)}%, counted as unrecognised rather
          than filed under &ldquo;other&rdquo;
        </Stat>
      </div>

      <H2 id="conclusions">If you read nothing else</H2>
      <Conclusions rows={d.conclusions} />

      {/* ================================================== THE FOUR SCHOOLS
          Rule 7a: the most concrete thing this page holds, immediately under the
          conclusions. A resident does not live in a district — they have a child at one
          building, and this is that building. Not a chart: absolute counts, grouped the
          way a parent thinks about a school, four panels side by side so the comparison
          is the layout. */}
      <H2 id="board">The four schools, as the town printed them</H2>
      <Body>
        Every name the town printed on that school&rsquo;s staff roster in its annual
        report, grouped, beside the children the state counted in the same building and
        the teaching posts the state counts there. Three separate instruments, kept apart:
        nothing here is added to anything else, and the arrows are the change over{' '}
        {d.board.window} years and nothing more &mdash; not a hire and not a cut.
      </Body>
      <SchoolBoard board={d.board} />

      <div className="card p-4 mt-6 max-w-3xl"
        style={{ borderLeft: '4px solid var(--status-warning)' }}>
        <p className="text-[14.5px] font-bold mb-1.5">
          Two things to know before quoting a panel.
        </p>
        <ul className="text-[13.5px] leading-relaxed space-y-1.5"
          style={{ color: 'var(--text-secondary)' }}>
          <li>
            <strong>A roster is not a staffing level.</strong> It carries no full-time
            equivalent, so a 0.4 music teacher and a full-timer are one name each; no
            funding source, which is the question that decides whether the town pays for
            a post; and no date within the year.
          </li>
          <li>
            <strong>The adults and the children may be a year apart.</strong> Nothing on a
            roster page states its date. {d.board.year_basis.sentences.length} sentences
            across the {d.board.year_basis.reports} reports name a fall and a student
            count; matched against the state&rsquo;s October enrolment for the same
            school,{' '}
            {d.board.year_basis.tally['the year after'] ?? 0} of them are closer to the
            year <em>after</em> the report&rsquo;s own fiscal year and{' '}
            {d.board.year_basis.tally['same as the cover'] ?? 0} to the year on the cover.
            So the panels pair each roster with the fiscal year it is labelled with, and
            that pairing is not established.
          </li>
        </ul>
        <p className="text-[13.5px] leading-relaxed mt-2.5"
          style={{ color: 'var(--text-secondary)' }}>
          <strong>One thing that would close most of this.</strong> A date on the roster,
          and the word the town already uses for it &mdash; the district files a staff
          return to the state every 1 October, so the roster it prints in the annual
          report could say which return it is. That is a line of text in a document the
          town already publishes, and it would turn every panel here from a bound into a
          count.
        </p>
      </div>

      <H3>Two of the state&rsquo;s files agree about teaching posts, and about when the
        buildings changed</H3>
      <Body>
        The teaching FTE on each panel is reached twice. DESE splits a school&rsquo;s
        teaching posts by <em>programme</em> in one file and by <em>grade band</em> in
        another, collected separately &mdash; and the two totals agree in{' '}
        {d.board.band_check.agree} of the {d.board.band_check.compared} school-years both
        publish. The build refuses to write if that stops being true.
      </Body>
      <Body>
        The same two files also settle the reorganisation without either knowing about the
        other. Lunenburg High carries teaching posts in the grades 6&ndash;8 band in{' '}
        {highBand
          ? `${fy(highBand.taught[0])}–${fy(highBand.taught[highBand.taught.length - 1])}`
          : '—'}{' '}
        and in no other year &mdash; exactly the years the enrolment file says grade 8 was
        in that building. Across every school, band and year, the teacher file and the
        enrolment file agree about which grades a building held in{' '}
        {d.board.band_era_evidence.agree} of {d.board.band_era_evidence.compared} cases.
        That is why scrubbing the selector back to {fy(oldEra.fy)} shows the primary
        school holding grades {oldEra.primary} and the high school holding{' '}
        {oldEra.high}: the buildings really did change, and both instruments say so.
      </Body>

      <H3>Two organisations counting the same teachers, and where they disagree</H3>
      <Body>
        The town prints names; the state publishes full-time-equivalent teaching posts.
        They come from different records kept for different purposes and they overlap on
        one quantity, so they can be set against each other &mdash; and this is the only
        independent check the archive has on either of them at school level.{' '}
        <strong>A headcount above an FTE is ordinary</strong>: the state counts{' '}
        {num(hcLast.teacher_headcount, 0)} teachers in Lunenburg holding{' '}
        {num(hcLast.teacher_fte, 1)} posts between them, so the average teacher holds{' '}
        {num(hcLast.teacher_share, 2)} of one. What is worth marking is the other
        direction.
      </Body>
      <Body>
        In {xc.flagged} of the {xc.compared} school-years with both, the town printed{' '}
        <em>fewer names than the state counts posts</em> &mdash; which says the two
        documents cannot both be complete counts of the same people. It is not spread
        evenly:{' '}
        {xc.by_school.filter(r => r.short > 0)
          .sort((a, b) => b.short / b.years - a.short / a.years)
          .map(r => `${r.school.replace('-', ' ')} in ${r.short} of ${r.years}`)
          .join(', ')}
        . The middle school and the high school are the two that share a building.
        <strong> Which document is short is not established.</strong> Our reading of a
        scanned page, what the town chose to print, and an assignment the state counts at
        one of two co-located schools whose holder the town printed under the other all
        fit, and nothing here separates them.
      </Body>
      {xc.doubled.map(x => (
        <Body key={`${x.fy}-${x.school}`}>
          The same instrument, pointed at the year the town printed two rosters. DESE&rsquo;s
          teaching FTE for {x.school.replace('-', ' ')} is{' '}
          {x.fte_either_side.map(y => `${num(y.fte ?? 0, 1)} in ${fy(y.fy)}`).join(', ')}{' '}
          &mdash; flat across it. The two printed rosters hold {x.heads.join(' and ')}{' '}
          teaching names, which is {x.each_ratio.map(r => num(r, 2)).join(' and ')} names
          per post; added together they would be {num(x.summed_ratio, 2)}, against a
          highest of {num(xc.highest.ratio, 2)} in every other school-year this archive
          holds. That is why the two rosters are shown apart and never summed.
        </Body>
      ))}
      <TableTwin caption={`Both counts, every school-year that has both`}
        head={['Year', 'School', 'Teaching names printed', 'Teaching FTE (state)',
               'Names per post', 'Fewer names than posts']}
        rows={board.years.flatMap(y => (board.by_fy[String(y)] || [])
          .filter(p => p.cross_check)
          .map(p => [fy(y), p.name || p.school, p.cross_check!.heads,
            num(p.cross_check!.fte, 1), num(p.cross_check!.ratio, 2),
            p.cross_check!.flag ? 'yes' : '']))} />

      {/* ------------------------------------------------ what the three quantities are */}
      <div className="card p-4 mt-8 max-w-2xl" style={{ borderLeft: '4px solid var(--status-warning)' }}>
        <p className="text-[14.5px] font-bold mb-1.5">
          Three different quantities are on this page, and only one of them is a count of
          people. A fourth &mdash; dollars &mdash; is deliberately on another page.
        </p>
        <ul className="text-[13.5px] leading-relaxed space-y-1.5"
          style={{ color: 'var(--text-secondary)' }}>
          <li>
            <strong>Names the town printed.</strong> {ros.entries_total} of them, across{' '}
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
            <strong>Headcount the state published.</strong> {hc.years} years of it,{' '}
            {fy(hc.first_fy)}&ndash;{fy(hc.last_fy)} &mdash; people, counted once each, by
            job classification. It is the only count of PEOPLE here, it is short, and it
            still carries no funding source.
          </li>
          <li>
            <strong>Dollars, which are not here.</strong> Net general-fund budget lines: a
            line is what the town has to raise after state aid, grants, fees and
            reimbursement have paid theirs, so a line can rise because a grant ended and
            nothing else changed. They are drawn on{' '}
            <a className="underline" style={{ color: 'var(--series-cost)' }}
              href={abs('/the-paraprofessionals')}>the paraprofessionals</a>, apart from
            everything on this page, for exactly the reason in the paragraph below.
          </li>
        </ul>
        <p className="text-[13.5px] leading-relaxed mt-2.5" style={{ color: 'var(--text-secondary)' }}>
          Nothing on this page divides a dollar by a person. Dollars over FTE looks like a
          cost per employee and is not one: the numerator leaves out every fund but the
          general fund, and the denominator counts the staff those funds pay for. The one
          division the page does make is headcount into FTE, which is two counts of staff
          from the same publisher and gives the average share of a post &mdash; and it is
          labelled as that everywhere it appears.
        </p>
      </div>




      <H3>The programme-area split, drawn because refusing to draw it is how it stayed
        unexamined</H3>
      <TableTwin caption={comp.programme.registered_gap}
        head={['Year', 'General education', 'Special education', 'Career and technical',
          'English learner', 'Total']}
        rows={prog.map(r => [fy(r.fy), num(r.gen_ed_fte ?? 0, 1), num(r.sped_fte ?? 0, 1),
          num(r.career_tech_fte ?? 0, 1), num(r.el_fte ?? 0, 1),
          num(r.total_fte ?? 0, 1)])} />

      {/* ================================================== headcount */}
      <H2 id="headcount">People, not posts &mdash; the one count that is a headcount</H2>
      <Body>
        Everything above counts full-time equivalents. The state publishes a{' '}
        <em>headcount</em> too &mdash; people, counted once each, by job classification
        &mdash; for {hc.years} years, {fy(hc.first_fy)}&ndash;{fy(hc.last_fy)}. That is
        short, and it is the only place in this archive where the difference between a
        person and a post has a number attached to it.
      </Body>
      <Body>
        In {fy(hcLast.fy)} the state counted {num(hcLast.teacher_headcount, 0)} people
        teaching in Lunenburg, holding {num(hcLast.teacher_fte, 1)} full-time equivalent
        posts between them: the average teacher holds{' '}
        {num(hcLast.teacher_share, 2)} of a post, down from{' '}
        {num(hc.vs_fte[0].teacher_share, 2)} in {fy(hc.vs_fte[0].fy)}. Paraprofessionals
        are the other way about &mdash; {num(hcLast.para_headcount, 0)} people and{' '}
        {num(hcLast.para_fte, 1)} FTE, so almost every one of them is counted whole.
      </Body>
      <div className="mt-6"><HeadcountAgainstFte rows={hc.vs_fte} /></div>
      <TableTwin caption="People and posts, side by side"
        head={['Year', 'Teachers (people)', 'Teacher FTE', 'Share of a post each',
          'Paraprofessionals (people)', 'Paraprofessional FTE', 'Share of a post each']}
        rows={hc.vs_fte.map(r => [fy(r.fy), num(r.teacher_headcount, 0),
          num(r.teacher_fte, 1), num(r.teacher_share, 2), num(r.para_headcount, 0),
          num(r.para_fte, 1), num(r.para_share, 2)])} />

      <H3>Everyone the state counted, by job classification</H3>
      <TableTwin caption={`Headcount, ${fy(hc.first_fy)}–${fy(hc.last_fy)}`}
        head={['Job classification', ...hc.vs_fte.map(r => fy(r.fy)), 'New hires, latest',
          'Retained, latest']}
        rows={hc.job_classes.map(jc => {
          const mine = hc.rows.filter(r => r.job_class === jc)
          const last = mine[mine.length - 1]
          return [jc, ...mine.map(r => num(r.educators_headcount, 0)),
            last.hires_headcount === null ? 'not published' : num(last.hires_headcount, 0),
            last.retained_pct === null ? 'not published'
              : `${(last.retained_pct * 100).toFixed(1)}%`]
        })} />

      {lastParaChurn && <>
      <Body>
        <strong>A headcount can say one more thing an FTE count cannot: who stayed.</strong>{' '}
        Of the paraprofessionals the state counted in {fy(lastParaChurn.fy)},{' '}
        {(lastParaChurn.retained_pct! * 100).toFixed(1)}% were retained from the year
        before, and {lastParaChurn.hires === null ? 'the hires figure is suppressed'
          : `${num(lastParaChurn.hires, 0)} of the ${num(lastParaChurn.headcount, 0)} were new`}
        . The School Committee voted a budget transfer for exactly this in the same period.
      </Body>
      {d.said.filter(q => q.key === 'para-transfers').map(q => (
        <div key={q.key} className="mt-4 max-w-2xl"><Quote q={q} /></div>
      ))}
      </>}

      <H3>Against the districts in the same file</H3>
      <Body>
        Headcount for each hundred pupils, {fy(hc.peers.fy)}. This is a{' '}
        <strong>different comparison group</strong> from the one the rest of this page uses
        &mdash; {hc.peers.districts} districts here against {d.peers.length} on DESE&rsquo;s
        radar sheet &mdash; so the two rankings are not interchangeable and the count of
        districts travels with every one of them.
      </Body>
      <div className="grid gap-3 mt-5 lg:grid-cols-2">
        <PeerHeadcount rows={hc.peers.rows} jobClass="Teacher" fyOf={hc.peers.fy} />
        <PeerHeadcount rows={hc.peers.rows} jobClass="Paraprofessional" fyOf={hc.peers.fy} />
      </div>
      <TableTwin caption={`Lunenburg's standing in ${fy(hc.peers.fy)}, by job classification`}
        head={['Job classification', 'Lunenburg per 100 pupils', 'Rank', 'Highest',
          'Lowest']}
        rows={hc.job_classes.map(jc => {
          const r = hc.peers.ranks[jc]
          return [jc, num(r.value, 2), `${r.rank} of ${r.of}`,
            `${r.highest} ${num(r.highest_value, 2)}`,
            `${r.lowest} ${num(r.lowest_value, 2)}`]
        })} />

      <div className="card p-4 mt-5 max-w-2xl"
        style={{ borderLeft: '4px solid var(--status-warning)' }}>
        <p className="text-[14.5px] font-bold mb-1.5">
          A correction this file caused, kept here because the shape repeats
        </p>
        <p className="text-[13.5px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
          {hc.rollup_trap} The build now refuses to write unless the naive sum is{' '}
          <em>exactly</em> twice the published figure, so if the state changes the shape of
          this file the page stops rather than quietly doubling or halving. Any column that
          prints a group total beside its own parts is the same trap.
        </p>
      </div>

      <NotShown>
        <p>
          <strong>Who is part-time.</strong> A share is an average over a whole job class.
          One full-timer beside one half-timer, and two people at three quarters, give the
          same figure. Nothing published gives the distribution.
        </p>
        <p className="mt-2.5">
          <strong>Whether a post was filled all year.</strong> A headcount is a return for
          one point in the school year, exactly like the town&rsquo;s printed rosters. A
          post held open for six months and filled for six is not distinguishable from
          either.
        </p>
        <p className="mt-2.5">
          <strong>Who pays.</strong> Not one of these {hc.years} years carries a funding
          source. That remains the question this whole archive cannot answer.
        </p>
      </NotShown>

      {/* ================================================== counsellors and social workers */}
      <H2 id="support">
        Counsellors, social workers, psychologists and nurses &mdash; and why they are the
        hardest group here to see
      </H2>
      <Body>
        None of these people is a teacher on the state&rsquo;s teacher returns, so the
        state&rsquo;s FTE series contains none of them &mdash; not the school panels
        above, and not the district series on{' '}
        <a className="underline" style={{ color: 'var(--series-cost)' }}
          href={abs('/school-staffing')}>did staffing go up</a>. The state&rsquo;s workforce
        file reaches them for {hc.years} years only and folds them into two residual
        buckets. What is left is the town&rsquo;s own printed rosters &mdash; names, by
        school, {fy(comp.not_counted.roster.first_fy)}&ndash;
        {fy(comp.not_counted.roster.last_fy)} &mdash; which carry no FTE, no funding source
        and no date within the year.
      </Body>
      <RoleGrid rows={support} format={role} />
      <TableTwin caption={`Names printed, ${fy(comp.not_counted.roster.first_fy)}–${fy(comp.not_counted.roster.last_fy)}`}
        head={['Role', `Names in ${fy(comp.not_counted.roster.first_fy)}`,
          `Names in ${fy(comp.not_counted.roster.last_fy)}`, 'Lowest', 'Highest',
          'Years that rose']}
        rows={support.map(r => [role(r.role), r.first, r.last, r.trough, r.peak,
          `${r.up} of ${r.steps}`])} />
      <p className="text-[12px] mt-3 max-w-2xl" style={{ color: 'var(--text-muted)' }}>
        A count of names the town printed is a real quantity and it is not a staffing
        level. Two consecutive reports may be photographs taken at different points in the
        school year, and a change between them is a difference between two documents.
      </p>

      {otherLicensed && (
        <Body>
          <strong>The one thing the state&rsquo;s file does say about this group is who
          stayed, and it is the lowest figure in it.</strong> The bucket these people sit
          in &mdash; <em>{otherLicensed.job_class}</em>, {otherLicensed.headcount} people
          in {fy(otherLicensed.fy)} &mdash; retained{' '}
          {(otherLicensed.retained_pct! * 100).toFixed(1)}% of the previous year&rsquo;s
          staff, against{' '}
          {teacherRetained?.retained_pct == null ? '—'
            : `${(teacherRetained.retained_pct * 100).toFixed(1)}%`}{' '}
          for teachers. <strong>That is not a statement about counsellors.</strong> The
          bucket is a residual: it holds counsellors, social workers and psychologists and
          it also holds everyone else licensed who is not a teacher or an administrator,
          and DESE publishes no split of it. What can be said is that the group containing
          them turned over faster than any other group in the file.
        </Body>
      )}

      <div className="grid gap-3 mt-6 lg:grid-cols-2">
        {d.said.filter(q => ['social-worker-caseloads', 'social-workers-billed-elsewhere',
          'esser-hired-13', 'esser-unwound'].includes(q.key))
          .map(q => <Quote key={q.key} q={q} />)}
      </div>

      <Maybe settle={<>
        The per-building social worker and adjustment counsellor caseload the district
        prepared for its own budget decisions &mdash; it told the School Committee it had
        one, in the quote above &mdash; with FTE and funding source beside each post. That is a records request rather than a download, and it is a row
        in <a className="underline" style={{ color: 'var(--series-cost)' }}
          href={abs('/what-we-cannot-answer')}>what we cannot answer</a>.
      </>}>
        <p>
          The ESSER grant paid for social workers, guidance counsellors, subject
          specialists, tutors and technicians &mdash; thirteen positions by the Finance
          Committee&rsquo;s own account &mdash; and then ended. A roster that gains names in
          those years and loses them afterwards would look exactly like a district hiring
          and then cutting. So would a district doing neither while a grant arrived and
          left. Nothing in the rosters distinguishes the two.
        </p>
      </Maybe>

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
        is excluded here entirely: a total that gains a whole page of names in some years
        and not others is measuring the page, not the payroll.
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
          apart. This is the single reason a roster count cannot be compared to the
          state&rsquo;s FTE, here or anywhere else on this site.
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


      {/* ------------------------------------------------ the other two staffing pages */}
      <H2 id="next">The same staff, counted two other ways</H2>
      <div className="grid gap-3 mt-5 lg:grid-cols-2">
        <a className="card px-4 py-3.5 block" href={abs('/school-staffing')}>
          <p className="text-[14.5px] font-bold">Did staffing go up?</p>
          <p className="text-[13px] mt-1" style={{ color: 'var(--text-secondary)' }}>
            The state&rsquo;s FTE series over a window you move yourself &mdash; and the
            count of how many spans of published years give each answer.
          </p>
        </a>
        <a className="card px-4 py-3.5 block" href={abs('/the-paraprofessionals')}>
          <p className="text-[14.5px] font-bold">The paraprofessionals</p>
          <p className="text-[13px] mt-1" style={{ color: 'var(--text-secondary)' }}>
            The biggest single change in who Lunenburg&rsquo;s schools employ, and the
            budget lines underneath it.
          </p>
        </a>
      </div>

      {/* ------------------------------------------------------ rule 15a, with its denominator */}
      <H2 id="said">What the town said about this, and how much of the archive could be read</H2>
      <Body>
        Every quote on this page is re-read out of the archive on each build and the build
        refuses to write if one is no longer verbatim there. These are the terms searched
        &mdash; in the town&rsquo;s vocabulary rather than ours, which is why{' '}
        <em>adjustment counselor</em> and <em>reduction in force</em> are on the list
        despite returning nothing.
      </Body>
      <Coverage m={d.minutes} searched={d.searched} />

      <H2 id="cannot">What this page cannot say</H2>
      <NotEstablished rows={d.not_established} closes={d.closes} />

      <H2 id="documents">The documents behind this</H2>
      <Provenance sources={d.sources} />

      <H2 id="sources">Where every figure on this page comes from</H2>
      <div className="grid gap-2.5 mt-5 max-w-3xl">
        <div className="card px-4 py-3.5">
          <p className="text-[14px] font-bold">The rosters</p>
          <p className="text-[12.5px] mt-1" style={{ color: 'var(--text-secondary)' }}>
            {ros.entries_total} names read page by page out of {rYears.length} annual town
            reports. There is no total printed on a roster, so the check is line accounting
            &mdash; every non-blank line on a page claimed as an entry or a heading.
          </p>
          <p className="text-[12px] mt-1.5" style={{ color: 'var(--text-muted)' }}>
            <a className="underline" href={abs('/docs/data/PROVENANCE-staff-rosters.md')}>
              PROVENANCE-staff-rosters.md
            </a>{' '}carries the per-page ledger.
          </p>
        </div>
        <div className="card px-4 py-3.5">
          <p className="text-[14px] font-bold">The state&rsquo;s FTE, headcount and enrollment</p>
          <p className="text-[12.5px] mt-1" style={{ color: 'var(--text-secondary)' }}>
            {st.points.length} years of FTE, {fy(st.first_fy)}&ndash;{fy(st.last_fy)}, LEA{' '}
            {st.lea}; {hc.years} years of headcount, {fy(hc.first_fy)}&ndash;{fy(hc.last_fy)}.
            Every measure reconciles against DESE&rsquo;s own printed totals ({Object.entries(st.reconciles)
              .map(([k, n]) => `${n} ${k || 'not checkable'}`).join(', ')}).
          </p>
          <p className="text-[12px] mt-1.5" style={{ color: 'var(--text-muted)' }}>
            {st.docs.join(', ')}
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
              href={abs('/data/who-works-in-each-school.json')}>/data/who-works-in-each-school.json</a>
          </p>
        </div>
      </div>

      <MoreReports here={TAB} />
    </ReportShell>
  )
}
