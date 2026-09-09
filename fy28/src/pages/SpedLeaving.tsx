import type { Tab } from '../routes'
import { abs } from '../lib/abs'
import type { Base } from '../components/report'
import {
  Body, Coverage, Grain, H2, Insight, NotEstablished, NotShown, OtherReports,
  Provenance, Quote, Shell, Stat, useReport,
} from '../components/report'
import type { Dest, NetPoint, RoutePoint } from '../components/SpedCharts'
import {
  ChoiceBothWays, Destinations, Span, TableTwin, ThreeRoutes, fy,
} from '../components/SpedCharts'

const TAB: Tab = 'outflow'

/** WHO LEAVES, AND WHERE THEY GO. A GENERAL report, and NOT one of the four special
 *  education reports -- see PARENT in routes.ts, where it hangs off /reports.
 *
 *  IT WAS BUILT AS ONE, and the reason it is not is the reason it exists. `notes/QUEUE.md`
 *  item 10 filed this under special education, and the file that answers it CARRIES NO
 *  DISABILITY FLAG. DESE publishes where each town's resident
 *  children are enrolled, by district and by programme, and does not publish IEP status
 *  with it. So a special education student who leaves under school choice and a student
 *  with no plan who leaves are the same row.
 *
 *  Merged into a special education narrative, "58 children left" becomes "58 special
 *  education children left" in one retelling. That is rule 7's exact failure mode — a
 *  proxy used as the thing — and keeping the report at its own address, with its own
 *  grain stated at the top, is the structural answer to it rather than a warning in a
 *  footnote.
 *
 *  A SECOND TRAP, FOUND WHILE BUILDING THIS. "Educated elsewhere" was first computed as
 *  everything that is not the Resident/Member programme, which reads as the obvious
 *  definition and is wrong: the 97 Lunenburg children at Montachusett Regional Vocational
 *  Technical are Resident/Member rows — of Monty Tech, a district Lunenburg belongs to and
 *  does not run. That definition published 80 where the measured figure is 177, and hid
 *  the single largest destination in the file. The generator now subtracts the Lunenburg
 *  LEA rather than a programme name.
 *
 *  NOT THE SAME PAGE AS /if-students-leave. That page is a SCENARIO with dials, priced on
 *  an assumption because no document in this archive states the tuition. This one is a
 *  MEASUREMENT with no dials and no dollars at all.
 *
 *  RULE 2. Not one figure is typed into this file.
 *
 *  ONE PAGE, NOT TWO. A second generator -- build_where_students_go.py -- computed the
 *  same outflow from the same table on the same day, and its route decomposition is now
 *  folded in here rather than published beside this page as a rival answer to the same
 *  question. It was also WRONG in a way this definition is not: it treated "not the
 *  Montachusett rows, under the Resident/Member reason" as in-district, which counted two
 *  children at a state-run school as being in Lunenburg's schools and published 184 where
 *  the measured figure is 186. Deleted, with its payload and its check_generated entry. */

type Row = {
  fy: number; total: number; in_lunenburg: number; elsewhere: number
  elsewhere_pct: number
} & Record<string, number>

type Payload = Base & {
  fy_first: number; fy_last: number
  reasons: string[]
  series: Row[]
  first: Row; last: Row
  peak_choice_year: number; peak_choice: number
  latest_year: number
  destinations: Dest[]
  destination_count: number
  persistent: { district: string; years: number; of: number }[]
  elsewhere_latest: Dest[]
  inbound: { fy: number; students: number }[]
  net: NetPoint[]
  routes: RoutePoint[]
  route_change: Record<Change, { first: number; last: number; pct: number }>
  three_routes: { route: string; key: Change; what: string }[]
}

type Change = 'monty_tech' | 'school_choice' | 'charter' | 'elsewhere' | 'in_lunenburg'

/** A signed percentage, never typed. `+38.6%`, `-15.9%`. */
const pc = (n: number) => `${n > 0 ? '+' : ''}${n.toFixed(1)}%`

const CHOICE = 'School Choice Program'
const L = (href: string, t: string) => (
  <a className="underline" style={{ color: 'var(--series-cost)' }} href={abs(href)}>{t}</a>
)

export function SpedLeaving() {
  const { d, err } = useReport<Payload>('sped-leaving.json')
  const title = 'Who leaves Lunenburg schools, and where they go'
  if (!d) return <Shell tab={TAB} title={title} err={err} loading={!err} />

  const last = d.last
  const first = d.first
  const netLast = d.net[d.net.length - 1]
  const biggest = d.elsewhere_latest[0]
  const choiceLast = last[CHOICE] ?? 0
  const charterLast = last['Charter School'] ?? 0
  const peakShare = d.series.reduce((a, b) => (b.elsewhere_pct > a.elsewhere_pct ? b : a))
  const lowShare = d.series.reduce((a, b) => (b.elsewhere_pct < a.elsewhere_pct ? b : a))
  const inLow = d.inbound.reduce((a, b) => (b.students < a.students ? b : a))
  const always = d.persistent.filter(p => p.years === p.of)
  const rc = d.route_change
  const routeOf = (k: Change) => d.three_routes.find(r => r.key === k)!

  return (
    <Shell tab={TAB} title={title}
      standfirst={`${last.elsewhere} of ${last.total.toLocaleString()} resident children — ${last.elsewhere_pct.toFixed(1)}% — are educated by a district other than Lunenburg. This is a count of children and it says nothing about disability.`}>

      <div className="flex flex-wrap gap-x-12 gap-y-6 mt-8">
        <Stat value={String(last.elsewhere)}>
          resident children educated somewhere other than Lunenburg, {fy(last.fy)}
        </Stat>
        <Stat value={String(biggest.students)} tone="var(--fund-school)">
          of them at {biggest.district} &mdash; a district Lunenburg BELONGS to and is
          assessed for, not one any family chose over it
        </Stat>
        <Stat value={String(choiceLast)}>under school choice</Stat>
        <Stat value={String(charterLast)}>at a charter school</Stat>
      </div>

      <Grain>
        <strong>Children, by town and district pair &mdash; and DESE publishes no
        disability status with it.</strong> Nothing on this page is a special education
        figure. A child with an individual education programme who transfers out and a
        child with no plan who transfers out are one row in this file, and the archive holds
        nothing that separates them. It is also not a dollar: not one document here states
        what the town is assessed for these children, which is{' '}
        {L('/what-we-cannot-answer', 'registered as a gap')} on both the money side and the
        people side.
      </Grain>

      <H2 id="findings">What this establishes</H2>
      <div className="grid gap-4 mt-5 md:grid-cols-2">
        <Insight n={1} headline={`The total barely moved in ${d.series.length} years — ${rc.elsewhere.first} to ${rc.elsewhere.last}, ${pc(rc.elsewhere.pct)} — while what it is made of changed completely`}>
          Monty Tech {rc.monty_tech.first} to {rc.monty_tech.last} ({pc(rc.monty_tech.pct)}).
          School choice {rc.school_choice.first} to {rc.school_choice.last} (
          {pc(rc.school_choice.pct)}). Charter schools {rc.charter.first} to{' '}
          {rc.charter.last} ({pc(rc.charter.pct)}). Anybody watching only the total would
          report that nothing is happening here, and the three things underneath it are
          moving in different directions at once &mdash; one of them by half. Over the same
          span the children in Lunenburg&rsquo;s own schools went {rc.in_lunenburg.first
          .toLocaleString()} to {rc.in_lunenburg.last.toLocaleString()} (
          {pc(rc.in_lunenburg.pct)}), which is the half of this that rarely gets said.
        </Insight>
        <Insight n={2} headline={`About one resident child in ten has been educated outside Lunenburg for the whole of this record`}>
          {first.elsewhere} of {first.total.toLocaleString()} in {fy(first.fy)} (
          {first.elsewhere_pct.toFixed(1)}%); {last.elsewhere} of{' '}
          {last.total.toLocaleString()} in {fy(last.fy)} ({last.elsewhere_pct.toFixed(1)}%).
          The high is {peakShare.elsewhere_pct.toFixed(1)}% in {fy(peakShare.fy)} and the low{' '}
          {lowShare.elsewhere_pct.toFixed(1)}% in {fy(lowShare.fy)}. Whatever else has
          happened in this town&rsquo;s schools, this share has not moved much.
        </Insight>
        <Insight n={3} headline={`The largest single destination is not school choice — it is ${biggest.district}`}>
          {biggest.students} children in {fy(last.fy)}, more than school choice and charter
          schools put together. They are counted as resident MEMBERS, because Lunenburg
          belongs to that district and helps fund it. Reading &ldquo;children who leave&rdquo;
          as school choice alone understates the count by more than half.
        </Insight>
        <Insight n={4} headline={`School choice out is ${choiceLast}, down from ${d.peak_choice} at its peak in ${fy(d.peak_choice_year)}`}>
          Across {d.destination_count} different districts in {fy(d.latest_year)}. In the
          other direction {netLast.in} children arrived in Lunenburg under school choice,
          the {inLow.fy === netLast.fy ? 'lowest' : 'near-lowest'} figure in the record, so
          the net position is {netLast.net}.
        </Insight>
        <Insight n={5} headline="None of these numbers is a special education number">
          This is the finding that keeps this report separate from the other three. DESE
          publishes the count by town, district and programme; disability status is not in
          the file. Anybody quoting this alongside a special education figure is joining two
          things the state does not join.
        </Insight>
      </div>

      <H2 id="routes">Three routes, and they are three different things</H2>
      <Body>
        The three lines below are usually added together and called &ldquo;students
        leaving&rdquo;. They should not be, and the reason is legal rather than
        presentational: each one is a different mechanism, decided by different people,
        paid for in a different way. Drawn as three lines rather than one stacked band,
        because a stacked band draws the sum &mdash; and the sum is the one quantity on
        this page that does not mean anything on its own.
      </Body>
      <div className="grid gap-4 mt-5 md:grid-cols-3">
        {d.three_routes.map(r => (
          <div key={r.key} className="card p-4">
            <div className="text-[11px] font-semibold uppercase tracking-widest"
              style={{ color: 'var(--text-muted)' }}>{r.route}</div>
            <div className="text-2xl font-bold tracking-tight tnum mt-2">
              {rc[r.key].first} &rarr; {rc[r.key].last}{' '}
              <span className="text-[15px] font-semibold"
                style={{ color: 'var(--text-secondary)' }}>{pc(rc[r.key].pct)}</span>
            </div>
            <p className="text-[13px] leading-relaxed mt-2"
              style={{ color: 'var(--text-secondary)' }}>{r.what}</p>
          </div>
        ))}
      </div>
      <ThreeRoutes rows={d.routes} />
      <Span from={d.routes[0].fy} to={d.routes[d.routes.length - 1].fy}
        what="the three routes, each on its own line" />
      <TableTwin
        caption="the three routes, and the children still in Lunenburg's own schools"
        head={['year', 'Monty Tech', 'school choice', 'charter', 'other', 'total elsewhere',
               'in Lunenburg']}
        rows={d.routes.map(r => [
          fy(r.fy), r.monty_tech, r.school_choice, r.charter, r.other, r.elsewhere,
          r.in_lunenburg.toLocaleString()])} />
      <Body>
        The <strong>other</strong> column is the residual &mdash; a handful of children a
        year at a state-run school or tuitioned in under a local agreement. It is
        reported rather than folded into one of the three, because a route with no
        mechanism named is not a route.
      </Body>
      <NotShown>
        What any of this movement does to what the town PAYS. This page counts children and
        prices nothing; a rising count at {routeOf('monty_tech').route} is a rising count,
        and reading a rising assessment off it is the step this page will not take for you.
        The assessment itself is measured at{' '}
        <a className="underline" style={{ color: 'var(--series-cost)' }}
          href="/monty-tech">Monty Tech &mdash; the assessment, and what sets it</a>, and
        the short version is that the count is not what moves it: nearly all of the bill
        is the state&rsquo;s minimum required local contribution, computed from the
        town&rsquo;s property value and resident income. What school choice costs is a
        different question again, and the statutory tuition that would answer it is not in
        this archive.
      </NotShown>
      <NotShown>
        That {routeOf('monty_tech').route} belongs on a list of departures at all. Those
        children are counted as resident MEMBERS, of a district Lunenburg belongs to. The
        town is assessed for them under the regional agreement whether the figure rises or
        falls, and no Lunenburg vote admits or refuses any of them &mdash; which is the
        opposite of {routeOf('school_choice').route.toLowerCase()}, where the receiving
        district opens the seats and a family applies for one.
      </NotShown>
      <NotShown>
        <strong>Which grades they leave in.</strong> DESE publishes this by receiving
        district and by year and never by grade, and the grade counts that do exist are
        headcounts INSIDE a district rather than an outflow from a town, so they cannot be
        differenced to recover it. The plausible story &mdash; that choice-outs cluster at
        grade 9, when families pick a high school &mdash; is a hypothesis nothing here
        tests, and it is the difference between a problem the district could act on at one
        transition and one spread across thirteen grades. Registered as{' '}
        {L('/what-we-cannot-answer', '“Which grades Lunenburg children leave the district in”')}.
      </NotShown>

      <H2 id="where">Where they actually are, {fy(d.latest_year)}</H2>
      <Body>
        Every district educating a Lunenburg resident, whatever the reason &mdash; member
        town, school choice, charter, tuitioned or foster placement. This is the answer to
        the question a resident actually asks, which school choice on its own does not give.
      </Body>
      <Destinations rows={d.elsewhere_latest} />
      <Span from={d.latest_year} to={d.latest_year} what="one year — every district, every reason" />
      <TableTwin
        caption={`the same list, as numbers, FY${d.latest_year}`}
        head={['district', 'resident children']}
        rows={d.elsewhere_latest.map(r => [r.district, r.students])} />
      <NotShown>
        Why any family chose any of these. A count of enrolments is not a reason for them.
        Nothing in this file, and nothing in the meeting record, surveys the households.
      </NotShown>
      <NotShown>
        That a child here is a child Lunenburg stopped spending on. An out-of-district
        special education placement is NOT in this file at all &mdash; a placed child stays
        enrolled in Lunenburg and is counted as a resident member. Those placements are{' '}
        {L('/who-ends-up-out-of-district', 'the fourth report')}.
      </NotShown>

      <H2 id="choice">School choice, both directions</H2>
      <Body>
        The district votes each year on how many seats to open, so the inbound figure is a
        decision and the outbound figure is many families&rsquo; decisions. Drawn as two
        bars rather than one net line, because the net hides that both arms moved.
      </Body>
      <ChoiceBothWays rows={d.net} />
      <Span from={d.net[0].fy} to={netLast.fy} what="school choice, both directions" />
      <TableTwin
        caption="out, in, and the net"
        head={['year', 'leaving', 'arriving', 'net']}
        rows={d.net.map(n => [fy(n.fy), n.out, n.in, n.net])} />
      <TableTwin
        caption={`where the school choice children go — every year, every district`}
        head={['district', 'years it appears', 'of']}
        rows={d.persistent.map(p => [p.district, p.years, p.of])} />
      <Body>
        {always.length
          ? `${always.length} district${always.length === 1 ? '' : 's'} appears in every one of the ${d.persistent[0].of} years: ${always.map(a => a.district).join(', ')}. The rest come and go.`
          : 'No district appears in every year of the record.'}
      </Body>
      <NotShown>
        What any of it costs. The statutory school choice base rate is set in law and is
        higher for special education; no document in this archive states either figure for
        Lunenburg. That is exactly why{' '}
        {L('/if-students-leave', 'the scenario page')} prices transfers on an assumption and
        says so on its face, and why this page carries no dollars at all.
      </NotShown>

      <H2 id="all">Every reason, every year</H2>
      <Body>
        DESE&rsquo;s own programme categories, unmerged. The Resident/Member column holds
        both the children in Lunenburg&rsquo;s own schools and the ones at the regional
        vocational district, which is why the count that matters is the one drawn from the
        district code rather than from this column.
      </Body>
      <TableTwin
        caption="resident children by programme"
        head={['year', 'total', 'in Lunenburg', 'elsewhere', 'share', ...d.reasons]}
        rows={d.series.map(r => [
          fy(r.fy), r.total.toLocaleString(), r.in_lunenburg.toLocaleString(),
          r.elsewhere, `${r.elsewhere_pct.toFixed(1)}%`,
          ...d.reasons.map(k => r[k] ?? 0)])} />

      <H2 id="said">What the town said about this</H2>
      <Body>
        Rule 15a: for every route this page says moved, what the town was saying about
        that route in the same year. Some are about the seats Lunenburg OPENS, which is
        the direction this page counts least well &mdash; and the nearest the meeting
        record comes to a rate. One is the School Committee on the route that actually
        rose. None of them is a measurement, and none of them explains a count.
      </Body>
      <div className="grid gap-4 mt-5 md:grid-cols-2">
        {d.said.map(q => <Quote key={q.key} q={q} />)}
      </div>
      <Coverage m={d.minutes} searched={d.searched} />

      <H2 id="sources">The documents</H2>
      <Provenance sources={d.sources} />

      <H2 id="limits">What this report cannot answer</H2>
      <NotEstablished rows={d.not_established} closes={d.closes} />

      <H2 id="next">Where this leads</H2>
      <Body>
        {L('/if-students-leave', 'If students leave')} is the SCENARIO beside this
        measurement: what school choice would cost the town if more children transferred
        out, with every input a dial and the tuition rate an assumption, because no
        document in this archive states it. This page has no dials and no dollars. A
        scenario and a measurement answer different questions and the difference is worth
        holding on to &mdash; one is what happened, the other is what might.
      </Body>
      <Body>
        The special education question this page cannot answer &mdash; whether children
        with an IEP leave at a different rate &mdash; is stated in its own terms on{' '}
        {L('/special-education', 'the special education hub')}, alongside the three
        reports that ARE special education figures.
      </Body>
      <OtherReports here="where-students-go-instead" />
    </Shell>
  )
}
