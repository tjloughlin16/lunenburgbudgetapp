import type { Tab } from '../routes'
import { abs } from '../lib/abs'
import {
  Caption, Churn, GradeProfile, GroupBars, Legend, OverTime, SchoolArtefact, TableTwin,
  KIDS, OTHER, RATE, fyLong, n0, n1, pct1, pts, syLong,
  type Band, type GradeStat, type GroupRow, type YearPoint,
} from '../components/AttritionCharts'
import {
  Body, Conclusions, Coverage, Grain, H2, H3, Maybe, MoreReports, NotEstablished,
  NotShown, Provenance, Quote, ReportShell, Stat, useReport,
} from '../components/report'
import type { Conclusion, Said, Source, Minutes } from '../components/report'

const TAB: Tab = 'attrition'
const DATA = '/data/attrition.json'

/** WHICH GRADES LUNENBURG CHILDREN LEAVE IN.
 *
 *  WHY THIS PAGE EXISTS. Residents ask this directly and every answer this project could
 *  give was about DESTINATIONS — how many go to Monty Tech, how many under school
 *  choice — because the file the archive held has no grade in it. DESE's attrition
 *  collection is a rate per grade, seventeen years of it, and it is the only published
 *  thing that answers the question that was actually asked.
 *
 *  RULE 7 IS THE WHOLE PAGE. That one grade does all the leaving is a measurement. WHY is
 *  not, and every reader supplies an answer for themselves before they reach the second
 *  screen. So the alternatives are on the first: a vocational admission at grade 9, a
 *  private or charter school, a school choice transfer, an out-of-district placement and
 *  a family moving are one number in this file.
 *
 *  RULE 13, STRUCTURALLY, AND IT DECIDES EVERY SERIES. The year on a row is the year the
 *  children were GONE, not the year they were counted — so every join is to the
 *  PREVIOUS year's enrolment. The generator establishes that three independent ways and
 *  refuses to write if any of them stops holding, because if it were wrong every grade on
 *  this page would be off by one and every figure would still be internally consistent.
 *
 *  RULE 7a. The thing first: which grade, and how much. The reason a school-level version
 *  of it does not exist comes later, beside the school-level chart.
 *
 *  RULE 7b. Conclusions, then the organised categorical data, then the raw and the
 *  caveats.
 *
 *  RULE 8. Not an audit. The largest number on the page is the one that most argues
 *  AGAINST the reading a resident arrives with.
 *
 *  RULE 2. Not one figure is typed into this file. Everything arrives from
 *  /data/attrition.json, written by scripts/build_attrition.py and recomputed from the
 *  CSVs by a second route in scripts/verify_attrition.py.
 *
 *  NO D1 AT PAGE LOAD. Static files. */

type Payload = {
  about: string
  grain: string
  generated_by: string
  first_sy: number
  last_sy: number
  years: number
  levels: { district_rows: number; school_rows: number; groups: string[]; rows: number }
  offset: {
    prior_year_max_error: number; same_year_max_error: number; ratio: number
    tolerance: number; years_tested: number
  }
  grade8_lag: {
    school: string; enrolment_years: number[]; attrition_years: number[]
    lag: number; years: number
  }
  group_definition_lag: {
    economically_disadvantaged: number[]; low_income: number[]; dese_says: string
  }
  terminal_grade: { school_years_checked: number; exceptions: number; dese_says: string }
  dese: { definition: string; blanks: string; groups: string; url: string }
  district: {
    sy: number; cohort_fy: number; all: number
    grades: { grade: string; rate: number | null }[]
    cohort?: number; implied?: number; grade8_cohort?: number; grade8_implied?: number
  }[]
  enrolment: { fy: number; total: number }[]
  grade_profile: GradeStat[]
  outlier: {
    grade: string; mean: number; median: number
    min: number; min_sy: number; max: number; max_sy: number
    runner_up: string; runner_up_mean: number; multiple: number
    others_low: number; others_high: number
    series: YearPoint[]; latest: YearPoint; rank_of_latest: number; years: number
    rising_run: number; longest_prior_rising_run: number
    implied_total: number; implied_years: number; implied_per_year: number
  }
  churn: {
    first_fy: number; last_fy: number; transitions: number; implied_total: number
    per_year: number; per_year_whole: number
    enrol_first: number; enrol_last: number; enrol_change: number
    ratio: number
    years: { sy: number; cohort_fy: number; cohort: number; rate: number
             implied: number }[]
  }
  grade9: {
    years: { cohort_fy: number; sy: number; grade8: number; rate: number
             stayed: number; grade9: number; residual: number }[]
    steps: number; larger: number; mean_residual: number; mean_leaving: number
  }
  eras: { bands: Band[]; low: Band; high: Band; spread: number }
  school_artefact: {
    school: string; grade: string
    series: { sy: number; cohort_fy: number; all: number; held_outlier_grade: boolean
              span: string }[]
    with_mean: number; with_years: number; without_mean: number; without_years: number
    points: number; ratio: number
  }
  groups: GroupRow[]
  group_gap: {
    grp: string
    grades: { grade: string; group_mean: number; all_mean: number; gap_points: number
              years: number }[]
    widest: { grade: string; gap_points: number; group_mean: number; all_mean: number }
    next_widest: { grade: string; gap_points: number }
  }
  destinations: {
    fy: number; columns: string[]; elsewhere: number
    by_reason: { reason: string; students: number }[]
    by_where: { reason: string; district: string; students: number }[]
    monty_tech: number; monty_grades: number; monty_per_grade: number
    outlier_grade: string
    series: { fy: number; students: number }[]
  }
  sources: Source[]
  said: (Said & { who: string })[]
  searched: { term: string; documents: number }[]
  minutes: Minutes
  not_established: string[]
  closes: string
  differently: string
  gaps: { side: string; what: string; why: string; closes: string | null }[]
  conclusions: Conclusion[]
}

export function WhichGradesStudentsLeave() {
  const { d, err } = useReport<Payload>('attrition.json')
  return (
    <ReportShell
      tab={TAB}
      title={d ? `Grade ${d.outlier.grade} is where Lunenburg loses students`
        : 'Which grades students leave in'}
      standfirst={d ? (
        <>
          Of every Lunenburg eighth grade, {pct1(d.outlier.mean)} does not come back for
          grade 9 &mdash; the highest grade in all {d.outlier.years} years the state has
          measured. Where they go is not published: Monty Tech, which the town belongs to
          and pays for either way, a private school, and a family moving away are one
          number here.
        </>
      ) : undefined}
      err={err} loading={!d && !err} dataUrl={DATA}>
      {d && <Report d={d} />}
    </ReportShell>
  )
}

function Report({ d }: { d: Payload }) {
  const o = d.outlier
  const swd = d.groups.find(g => g.grp === 'Students with Disabilities')
  const ref = d.groups.find(g => g.grp === 'All Students')
  const others = d.grade_profile.filter(p => p.grade !== o.grade)
    .map(p => p.mean).sort((a, b) => a - b)
  const said = (key: string) => d.said.find(s => s.key === key)
  const choicing = said('choicing-out')
  const hemorrhage = said('hemorrhage')
  const band = said('band-transition')
  const sizer = said('sizer-parker')
  return (
    <>
      {/* ---- rule 7b, first movement: what this page establishes ---------- */}
      <section data-section="conclusions">
        <div className="flex flex-wrap gap-x-10 gap-y-5 mt-8">
          <Stat value={pct1(o.mean)} tone={RATE}>
            of every eighth grade does not return for grade 9, averaged over{' '}
            {o.years} years
          </Stat>
          <Stat value={pct1(others[others.length - 1])}>
            the worst any OTHER grade averages &mdash; grade {
              d.grade_profile.filter(p => p.grade !== o.grade)
                .reduce((a, b) => (a.mean > b.mean ? a : b)).grade}
          </Stat>
          <Stat value={swd?.mean === undefined ? '' : pct1(swd.mean)}>
            of eighth graders on an IEP, against {ref?.mean === undefined ? ''
              : pct1(ref.mean)} of all students
          </Stat>
          <Stat value={n0(d.churn.implied_total)} tone={KIDS}>
            children left in {n0(d.churn.transitions)} years, implied &mdash; against an
            enrolment change of {n0(Math.abs(d.churn.enrol_change))}
          </Stat>
        </div>

        <Grain>{d.grain}</Grain>

        <Conclusions rows={d.conclusions} />
      </section>

      {/* ---- rule 7b, second movement: the organised categorical data ----- */}
      <section data-section="categorical">
        {/* THE QUESTION A SCHOOL COMMITTEE MEMBER ARRIVES WITH, ANSWERED BEFORE THE
            CHARTS. It was answerable only from the eras table near the bottom, and
            "read to the end and work it out" is how a page gets quoted as saying the
            opposite. Every figure in it comes out of the payload. */}
        <div className="card p-5 mt-10 max-w-2xl avoid-break"
          style={{ borderLeft: '4px solid var(--fund-school)' }}>
          <p className="text-[11px] font-semibold uppercase tracking-widest mb-1.5"
            style={{ color: 'var(--text-muted)' }}>
            Did the budget cuts do this?
          </p>
          <p className="text-[15px] leading-relaxed">
            Nothing here can say, and the shape of the series argues against it. Grade{' '}
            {o.grade} was already losing {pct1(d.eras.bands[0].outlier_mean)} of each
            cohort in {syLong(d.eras.bands[0].first_sy)}&ndash;
            {syLong(d.eras.bands[0].last_sy)}, years before any of the reductions the
            town is currently arguing about, and the five eras since sit between{' '}
            {pct1(d.eras.low.outlier_mean)} and {pct1(d.eras.high.outlier_mean)}.
          </p>
          <p className="text-[14px] leading-relaxed mt-2.5"
            style={{ color: 'var(--text-secondary)' }}>
            The most recent era, {syLong(d.eras.bands[d.eras.bands.length - 1].first_sy)}
            &ndash;{syLong(d.eras.bands[d.eras.bands.length - 1].last_sy)}, is the
            highest of the five at{' '}
            {pct1(d.eras.bands[d.eras.bands.length - 1].outlier_mean)} &mdash; and it is{' '}
            {pts(d.eras.spread * 100)} above the lowest, which is inside the range this
            town has been in for {n0(o.years)} years. A rate that was this high before the
            cuts cannot be evidence that the cuts caused it, and a rate that is at its
            second-highest now is not evidence that they did not. This file records one
            outcome and no causes.
          </p>
        </div>

        <H2 id="by-grade">Every grade, averaged over {n0(o.years)} years</H2>
        <Body>
          One bar is about {n1(o.multiple)} times the rest of the chart. Grade {o.grade}{' '}
          averages {pct1(o.mean)}; the other eleven grades sit between{' '}
          {pct1(others[0])} and {pct1(others[others.length - 1])}, and on a shared axis
          they flatten into a rule. The flattening is the finding, and the table under it
          carries the eleven numbers the bars cannot show.
        </Body>
        <GradeProfile rows={d.grade_profile} outlier={o.grade} />
        <Legend items={[
          { colour: RATE, label: `grade ${o.grade}` },
          { colour: OTHER, label: 'every other grade' },
        ]} />
        <Caption>
          Lunenburg district, All Students, {syLong(d.first_sy)} to {syLong(d.last_sy)}{' '}
          &mdash; {n0(o.years)} years. There is no grade 12 column: a twelfth grader who
          does not come back has graduated, and DESE does not call that attrition.
        </Caption>
        <TableTwin
          caption="the mean, the median and the range, per grade"
          head={['grade', 'mean', 'median', 'lowest year', 'highest year',
            'years it was the worst grade']}
          rows={d.grade_profile.map(p => [
            p.grade, pct1(p.mean), pct1(p.median),
            `${pct1(p.min)} (${syLong(p.min_sy)})`,
            `${pct1(p.max)} (${syLong(p.max_sy)})`,
            n0(p.times_highest),
          ])}
          note={<>The last column is counted, not asserted. If the file ever stops having
            one grade that is worst in every year, the generator stops publishing one and
            nothing on this page is highlighted.</>} />

        <H2 id="over-time">Grade {o.grade}, year by year</H2>
        <Body>
          The rate runs from {pct1(o.min)} in {syLong(o.min_sy)} to {pct1(o.max)} in{' '}
          {syLong(o.max_sy)}, and the most recent year is the{' '}
          {o.rank_of_latest === 2 ? 'second' : `${o.rank_of_latest}th`}-highest of{' '}
          {n0(o.years)}. The bands behind it are the five eras &mdash; built from
          DESE&rsquo;s own enrolment-by-grade counts, so a school closing and a new
          building opening are boundaries rather than noise. Averaged inside them the rate
          stays between {pct1(d.eras.low.outlier_mean)} and{' '}
          {pct1(d.eras.high.outlier_mean)}, a spread of {pts(d.eras.spread * 100)}.
        </Body>
        <OverTime points={o.series} bands={d.eras.bands} mean={o.mean} />
        <Legend items={[
          { colour: RATE, label: `grade ${o.grade} attrition` },
          { colour: 'var(--status-warning)', label: 'the pandemic years — OUR boundary, not the data’s' },
        ]} />
        <Caption>
          {n0(o.years)} school years, {syLong(d.first_sy)} to {syLong(d.last_sy)}. The
          dashed rule is the {n0(o.years)}-year mean. The shaded pandemic band is an
          assertion of ours and is drawn in a different ink from the era boundaries, which
          are read off the state&rsquo;s grade counts.
        </Caption>
        <TableTwin
          caption="the eras, and the rate inside each"
          head={['era', 'high school grades', 'years', `grade ${o.grade}`, 'all grades']}
          rows={d.eras.bands.map(b => [
            `${syLong(b.first_sy)}–${syLong(b.last_sy)}${b.covid ? ' · the pandemic' : ''}`,
            b.span, n0(b.years_in_file), pct1(b.outlier_mean), pct1(b.all_mean),
          ])} />
        <NotShown>
          A run of increases. The rate has risen for the last {n0(o.rising_run)} years,
          which is what a reader notices first &mdash; and the longest earlier run in the
          same series is {n0(o.longest_prior_rising_run)}. A single Lunenburg grade is
          around a hundred and twenty children, so one family moving is close to a
          point. Three points are three points; the eras are drawn so a reader can see
          what the same three points looked like the last four times.
        </NotShown>

        <H2 id="who">Who leaves, at the grade that moves</H2>
        <Body>
          The same grade, split by student group. Every group here OVERLAPS every other
          one and overlaps All Students &mdash; the same child can be in four of these
          bars &mdash; so nothing is added and no total is drawn. The dashed rule is All
          Students, which is what each bar is being compared with.
        </Body>
        <GroupBars rows={d.groups} reference={ref?.mean ?? 0} />
        <Legend items={[
          { colour: RATE, label: 'one definition throughout' },
          { colour: OTHER, label: 'the definition changed inside the series' },
        ]} />
        <Caption>
          Lunenburg district, grade {o.grade}, {syLong(d.first_sy)} to{' '}
          {syLong(d.last_sy)} where published. Two of these bars cover part of the span
          only: DESE says so itself &mdash; &ldquo;{d.group_definition_lag.dese_says}
          &rdquo; &mdash; and they are drawn in the recessive ink for that reason rather
          than joined into one line.
        </Caption>
        <TableTwin
          caption="each group at grade 8, and against all students"
          head={['group', 'mean', 'published years', 'lowest', 'highest',
            'against all students']}
          rows={d.groups.map(g => [
            g.grp,
            g.mean === undefined ? 'suppressed' : pct1(g.mean),
            n0(g.published_years),
            g.min === undefined ? '—' : pct1(g.min),
            g.max === undefined ? '—' : pct1(g.max),
            g.gap_points === undefined ? '—' : pts(g.gap_points),
          ])}
          note={<>English Learners has no published grade {o.grade} rate in any year.
            DESE suppresses a cell whose enrolment is under six, and this one always
            is.</>} />

        <H3>The gap is at one step, not everywhere</H3>
        <Body>
          A group that leaves more in every grade is a different fact from one that leaves
          more at a single step, and this is the second. Children on an IEP leave at{' '}
          {pct1(d.group_gap.widest.group_mean)} at grade {d.group_gap.widest.grade}{' '}
          against {pct1(d.group_gap.widest.all_mean)} for all students &mdash;{' '}
          {pts(d.group_gap.widest.gap_points)} &mdash; and at no other grade is the
          difference more than {pts(d.group_gap.next_widest.gap_points)}.
        </Body>
        <TableTwin
          caption="students with disabilities against all students, grade by grade"
          head={['grade', 'on an IEP', 'all students', 'difference']}
          rows={d.group_gap.grades.map(g => [
            g.grade, pct1(g.group_mean), pct1(g.all_mean), pts(g.gap_points),
          ])} />
        <NotShown>
          How many children this is. DESE publishes no count of a student group inside a
          grade, so the cohort behind each of these rates is on the order of twenty
          children and one family moving is several points. The year-by-year swing for
          this group is {swd?.min === undefined ? '' : pct1(swd.min)} to{' '}
          {swd?.max === undefined ? '' : pct1(swd.max)}, which is why no figure on this
          page comes off a single year of it. And a special education placement is not
          attrition: nothing here says which of these departures was a placement, a
          vocational admission, a private school or a move.
        </NotShown>

        <H2 id="churn">Does this explain the enrolment fall?</H2>
        <Body>
          No, and it is not close. Applying DESE&rsquo;s own all-grades rate to
          DESE&rsquo;s own enrolment implies about {n0(d.churn.per_year_whole)} children leave
          every year, {n0(d.churn.implied_total)} over {n0(d.churn.transitions)}{' '}
          transitions &mdash; while district enrolment went from{' '}
          {n0(d.churn.enrol_first)} in {fyLong(d.churn.first_fy)} to{' '}
          {n0(d.churn.enrol_last)} in {fyLong(d.churn.last_fy)}. The churn is{' '}
          {n1(d.churn.ratio)} times the net change. A town losing children and a town
          losing them and gaining most of them back are the same line on an enrolment
          chart and are not the same town.
        </Body>
        <Churn years={d.churn.years} enrolment={d.enrolment.map(
          e => ({ fy: e.fy, total: e.total }))} />
        <Legend items={[
          { colour: KIDS, label: 'children who left that year — implied, left axis' },
          { colour: RATE, label: 'district enrolment that October — right axis' },
        ]} />
        <Caption>
          {n0(d.churn.transitions)} year-to-year transitions. The bars are an annual FLOW
          and the line is a STOCK, on two axes that are deliberately not comparable:
          drawing them on one scale is what makes the flow invisible, which is the
          reading this section exists to correct.
        </Caption>
        <TableTwin
          caption="the rate, the cohort it applies to, and the children it implies"
          head={['school year', 'cohort counted', 'children in K–11',
            'all-grades rate', 'children who left, implied']}
          rows={d.churn.years.map(y => [
            syLong(y.sy), fyLong(y.cohort_fy), n0(y.cohort), pct1(y.rate),
            n1(y.implied),
          ])} />
        <NotShown>
          A headcount. Every number of children on this page is a published rate
          multiplied by a published enrolment, and DESE publishes no count. It is also not
          a count of distinct children &mdash; a child who leaves and comes back is two
          events here &mdash; and it measures one direction only. Who ARRIVES is a
          residual: births, families moving in, children returning from a private school
          and anybody repeating a year are one number.
        </NotShown>

        <H3>The other half, at the same step</H3>
        <Body>
          Of every eighth grade, about {n0(d.outlier.implied_per_year)} children do not
          come back. And in {n0(d.grade9.larger)} of {n0(d.grade9.steps)} years the
          following autumn&rsquo;s grade 9 was still LARGER than the eighth graders who
          stayed &mdash; by about {n1(d.grade9.mean_residual)} on average. That residual
          is arithmetic across two files, not a measurement: arrivals from anywhere and
          anybody repeating the year are the same number in it.
        </Body>
        <TableTwin
          caption="grade 8 to grade 9, cohort by cohort"
          head={['eighth grade of', 'children', 'left', 'stayed', 'grade 9 that autumn',
            'difference']}
          rows={d.grade9.years.map(r => [
            fyLong(r.cohort_fy), n0(r.grade8), pct1(r.rate), n1(r.stayed),
            n0(r.grade9), n1(r.residual),
          ])} />
      </section>

      {/* ---- rule 7b, third movement: the raw, the method, the limits ----- */}
      <section data-section="raw">
        <H2 id="where">Where they went, which nobody publishes</H2>
        <Body>
          This is the next question every reader has, and the record refuses it. DESE
          publishes an attrition rate with no destination, and publishes where every
          resident child is educated with no grade. In {fyLong(d.destinations.fy)},{' '}
          {n0(d.destinations.elsewhere)} Lunenburg children were educated somewhere other
          than a Lunenburg school &mdash; and not one of them can be attached to the grade
          they left in.
        </Body>
        <TableTwin
          caption={`where lunenburg's resident children were educated, ${fyLong(d.destinations.fy)}`}
          head={['receiving district', 'why they are there', 'children']}
          rows={d.destinations.by_where.map(r => [r.district, r.reason,
            n0(r.students)])}
          note={<>&ldquo;Resident/Member&rdquo; against Monty Tech is not a child leaving
            the town&rsquo;s system: Lunenburg is a member town of that district and is
            assessed for them either way. Every row here is a headcount at a point in
            time, across all grades. The file has no grade column, which is the whole of
            why this section exists.</>} />
        <Maybe settle={<>One column. DESE&rsquo;s residents-sending file with a grade on
          each row, or the district&rsquo;s own October submission broken out by exit
          grade and exit reason &mdash; which the district files to the state every year
          and does not report to its own School Committee.</>}>
          <p>
            Monty Tech admits at grade 9. It holds {n0(d.destinations.monty_tech)}{' '}
            Lunenburg children across {n0(d.destinations.monty_grades)} grade years,
            about {n1(d.destinations.monty_per_grade)} a year &mdash; which is the same
            order of magnitude as the {n0(d.outlier.implied_per_year)} eighth graders a
            year this page implies are leaving.
          </p>
          <p className="mt-2.5">
            Being the same size is not being the same children, and this page does not
            say it is. The same rate is equally consistent with private and parochial
            admission at grade 9, with charter admission, with a school choice transfer,
            with an out-of-district special education placement made at the transition,
            and with families moving out of town. And Lunenburg is a MEMBER town of Monty
            Tech: a child going there is not choosing out of the town&rsquo;s system in
            the way that phrase usually means, and the town is assessed for them either
            way.
          </p>
        </Maybe>

        <H2 id="what-the-year-means">What the year on a row means</H2>
        <Body>
          A row labelled {syLong(d.last_sy)} measures children who were enrolled in{' '}
          {syLong(d.last_sy - 1)} and were not enrolled in {syLong(d.last_sy)}. DESE says
          so: &ldquo;{d.dese.definition}&rdquo; Get it backwards and every grade on this
          page shifts by one &mdash; the finding would land in grade 7 &mdash; and every
          figure would still be internally consistent. So the generator establishes it
          three ways that do not depend on each other, and refuses to write if any of them
          stops holding.
        </Body>
        <TableTwin
          caption="three independent routes to the same answer"
          head={['route', 'what it compares', 'result']}
          rows={[
            ["DESE's own all-grades rate",
              'the twelve grade rates weighted by enrolment, against grd_all',
              `${n1(d.offset.prior_year_max_error * 1000)} in a thousand worst case on the previous year, against ${n1(d.offset.same_year_max_error * 1000)} on the same year — ${n1(d.offset.ratio)} times closer`],
            [`grade ${d.school_artefact.grade} at ${d.grade8_lag.school}`,
              'the years the enrolment file says the school held it, against the years the attrition file reports it',
              `${n0(d.grade8_lag.years)} years, every one displaced by exactly ${n0(d.grade8_lag.lag)}`],
            ['DESE’s own group definitions',
              'the years DESE says each low-income definition was used, against the rows carrying it',
              `Economically Disadvantaged lands on ${syLong(d.group_definition_lag.economically_disadvantaged[0])}–${syLong(d.group_definition_lag.economically_disadvantaged[d.group_definition_lag.economically_disadvantaged.length - 1])}, which is DESE’s stated span moved by one`],
          ]}
          note={<>The second and third routes touch nothing the first one touches. Two
            files that must agree is worth more than one file read carefully.</>} />

        <H2 id="no-school">Why there is no school-level version of this</H2>
        <Body>
          DESE blanks a grade where the school has &ldquo;no grade in the given year for
          students from the previous year to advance&rdquo;. A school&rsquo;s top grade is
          exactly that &mdash; everybody in it advances out of the building &mdash; so
          Lunenburg Middle School, which ends at grade {o.grade}, publishes no grade{' '}
          {o.grade} rate at all. The largest departure in this town is structurally
          invisible in every school row, and the district row is the only place it exists.
          The rule was checked on {n0(d.terminal_grade.school_years_checked)} school-years
          here, against the state&rsquo;s own grade counts.
        </Body>
        <Body>
          And a school-level series is not safe to read even where it exists.{' '}
          {d.school_artefact.school} has its own published rate for every year, and it is{' '}
          {pct1(d.school_artefact.with_mean)} in the{' '}
          {n0(d.school_artefact.with_years)} years the building held grade{' '}
          {d.school_artefact.grade} against {pct1(d.school_artefact.without_mean)} in the
          other {n0(d.school_artefact.without_years)}. That is{' '}
          {pts(d.school_artefact.points)}, and not one child&rsquo;s behaviour changed:
          the school was given an extra grade, and it happened to be the grade that
          leaves.
        </Body>
        <SchoolArtefact rows={d.school_artefact.series} grade={d.school_artefact.grade} />
        <Legend items={[
          { colour: RATE, label: `the years grade ${d.school_artefact.grade} was in the building` },
          { colour: OTHER, label: 'every other year' },
        ]} />
        <Caption>
          {d.school_artefact.school}, all grades in the building, {syLong(d.first_sy)} to{' '}
          {syLong(d.last_sy)}. This chart is here to be misread and then corrected: it
          looks like a school that got worse and recovered, and it is a building
          programme.
        </Caption>

        <H2 id="said">What people said about this, in the town&rsquo;s own words</H2>
        <Body>
          Searching this archive for the words a report would use finds nothing about
          children at all. &ldquo;Attrition&rdquo; in Lunenburg means STAFF attrition, and
          &ldquo;declining enrollment&rdquo;, &ldquo;enrollment decline&rdquo;,
          &ldquo;families leaving&rdquo; and &ldquo;losing students&rdquo; return no
          documents between them. The town argues about this in different words.
        </Body>
        <div className="grid gap-4 mt-5 sm:grid-cols-2">
          {[choicing, hemorrhage, band, sizer].map(s => s ? (
            <div key={s.key}>
              <p className="text-[11px] font-semibold uppercase tracking-widest mb-1.5"
                style={{ color: 'var(--text-muted)' }}>{s.who}</p>
              <Quote q={s} />
            </div>
          ) : null)}
        </div>
        <NotShown>
          What any of it establishes. A principal describing one student&rsquo;s decision
          is evidence that the decision is discussed in public and evidence of nothing
          about how many children make it. A prediction is evidence of what somebody
          expected. Neither is a measurement, and the series that would test the
          prediction does not yet reach the years after it was made.
        </NotShown>
        <Coverage m={d.minutes} searched={d.searched} />

        <H2 id="every-grade">Every grade, every year</H2>
        <Body>
          The whole district series, as DESE publishes it. Each figure is the share of
          that grade&rsquo;s children, counted the previous October, who were not in a
          Lunenburg school the following one.
        </Body>
        <TableTwin
          caption="lunenburg district, all students"
          head={['school year', 'cohort counted',
            ...d.grade_profile.map(p => p.grade), 'all grades']}
          rows={d.district.map(r => [
            syLong(r.sy), fyLong(r.cohort_fy),
            ...r.grades.map(g => (g.rate === null ? '—' : pct1(g.rate))),
            pct1(r.all),
          ])}
          note={<>{d.levels.rows} rows are in the table behind this page &mdash;{' '}
            {d.levels.district_rows} district and {d.levels.school_rows} school, across{' '}
            {d.levels.groups.length} student groups that overlap one another. Nothing on
            this page adds across either split.</>} />

        <H2 id="different">One thing that could be done differently next year</H2>
        <Body>{d.differently}</Body>

        <H2 id="not-established">What this page does not establish</H2>
        <NotEstablished rows={d.not_established} closes={d.closes} />
        <div className="grid gap-3 mt-5 sm:grid-cols-2">
          {d.gaps.map(g => (
            <div key={g.what} className="card p-4 avoid-break">
              <p className="text-[14px] font-bold leading-snug">{g.what}</p>
              <p className="text-[13px] leading-relaxed mt-2"
                style={{ color: 'var(--text-secondary)' }}>{g.why}</p>
              {g.closes ? (
                <p className="text-[12.5px] leading-relaxed mt-2.5"
                  style={{ color: 'var(--text-muted)' }}>
                  <span className="font-semibold uppercase tracking-widest text-[10.5px]">
                    What would close it
                  </span>{' '}{g.closes}
                </p>
              ) : null}
            </div>
          ))}
        </div>

        <H2 id="sources">Where these figures come from</H2>
        <Provenance sources={d.sources} />
        <p className="text-[13px] leading-relaxed max-w-2xl mt-5"
          style={{ color: 'var(--text-muted)' }}>
          Computed by <code>{d.generated_by}</code> and published at{' '}
          <a className="underline" style={{ color: 'var(--series-cost)' }}
            href={abs(DATA)}>{DATA}</a>. Every figure on this page is recomputed from the
          CSVs by a second route in <code>scripts/verify_attrition.py</code>.
        </p>

        <MoreReports here={TAB} />
      </section>
    </>
  )
}
