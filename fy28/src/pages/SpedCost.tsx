import { abs } from '../lib/abs'
import { usd } from '../model/engine'
import type { Base } from '../components/spedPage'
import {
  Body, Coverage, Grain, H2, Insight, Maybe, NotEstablished, NotShown, OtherReports,
  Provenance, Quote, Shell, Stat, useReport,
} from '../components/spedPage'
import type { Breaker, Spend } from '../components/SpedCharts'
import { CircuitBreaker, Span, TableTwin, TuitionByFund, fy } from '../components/SpedCharts'

/** WHAT IT COSTS, AND WHAT COMES BACK. Report three of four.
 *
 *  THIS PAGE IS RULE 11 MEASURED RATHER THAN WARNED ABOUT. CLAUDE.md says a budget line is
 *  NET — what the town has to raise after everything else that pays for the thing has been
 *  subtracted — and that nothing in the document marks it as net. For out-of-district
 *  tuition that is not a caution, it is an identity that can be checked: the district's own
 *  restated budget figure equals DESE's GENERAL FUND column, to the dollar, in almost every
 *  year of the record, while DESE's ALL FUNDS column is far larger. So the line the town
 *  votes is the town's share, and the rest was spent from money that never appears in the
 *  appropriation at all.
 *
 *  THE ONE SENTENCE THIS PAGE MUST NOT WRITE. "The money outside the appropriation is the
 *  circuit breaker." It is the obvious reading, the two series are the same order of
 *  magnitude, and it is not established: the grants and revolving column holds every
 *  non-general fund together, and the circuit breaker account carries a balance forward, so
 *  the two would not be equal even if one paid the whole of the other. Both series are
 *  published, the difference is computed, and it is never differenced into a claim.
 *
 *  WHAT IS SIMPLY NOT MEASURABLE HERE, and the page says so where a reader will look for
 *  it: DESE's End of Year Financial Report has NO in-district special education category.
 *  Functions 9300 and 9400 are the only two on the whole return that name special
 *  education, and both are tuition paid to somebody else. Every in-district figure this
 *  project holds rests on a classification we made, and it lives on /bend-the-curve where
 *  it says so.
 *
 *  RULE 1. Every figure on this page is closed-year spending from a statutory return, or a
 *  restated budget column, and the two are never differenced against each other for a
 *  growth rate. They are compared for IDENTITY, in the same year, which is a different
 *  operation and the only one the pairing supports.
 *
 *  RULE 2. Not one figure is typed into this file. */

type Payload = Base & {
  fy_first: number; fy_last: number
  spend: Spend[]
  per_code: { fy: number; [code: string]: unknown }[]
  last: Spend; widest: Spend
  budget_vs_fund: {
    fy: number; budget: number; dese_gen_fund: number; dese_all_funds: number
    vs_gen_fund: number; vs_all_funds: number; ties_gen_fund: boolean
  }[]
  ties_years: number[]; miss_years: number[]
  ties_count: number; compared_count: number
  breaker: (Breaker & {
    claim_residual: number; threshold_per_student: number | null; comment: string
  })[]
  cb_first: Breaker; cb_last: Breaker
  cb_peak_students: Breaker; cb_low_students: Breaker
  cb_transport_first_year: number | null
  cb_identity_years: number[]; cb_identity_breaks: number[]
  beside: {
    fy: number; outside_appropriation: number; circuit_breaker_paid: number
    difference: number
  }[]
}

const L = (href: string, t: string) => (
  <a className="underline" style={{ color: 'var(--series-cost)' }} href={abs(href)}>{t}</a>
)

export function SpedCost() {
  const { d, err } = useReport<Payload>('sped-cost.json')
  const title = 'What out-of-district special education costs, and what comes back'
  if (!d) return <Shell title={title} err={err} loading={!err} />

  const last = d.last
  const outside = last.total - last.gen_fund
  const cb = d.cb_last
  const bigOutside = d.spend.reduce(
    (a, b) => (b.outside_share_pct > a.outside_share_pct ? b : a))
  const cbShareLast = cb.paid_share_of_eligible
  const cbHigh = d.breaker.reduce((a, b) => (b.paid > a.paid ? b : a))
  const transportYears = d.breaker.filter(b => b.reimb_transport > 0)
  const besideLast = d.beside[d.beside.length - 1]
  const sameSign = d.beside.filter(b => b.difference > 0).length

  return (
    <Shell title={title}
      standfirst={`${usd(last.total)} spent in ${fy(last.fy)}. The line in the budget the town votes said ${usd(last.gen_fund)}. Both figures are correct, and they are not the same quantity.`}>

      <div className="flex flex-wrap gap-x-12 gap-y-6 mt-8">
        <Stat value={usd(last.total)}>
          out-of-district tuition actually spent in {fy(last.fy)}, all funds
        </Stat>
        <Stat value={usd(last.gen_fund)} tone="var(--series-cost)">
          the general fund share &mdash; the figure that appears in the budget
        </Stat>
        <Stat value={usd(outside)} tone="var(--fund-enterprise)">
          spent from funds that are not in the appropriation at all
        </Stat>
        <Stat value={usd(cb.paid)}>
          circuit breaker reimbursement received in {fy(cb.fy)}, for {cb.students} students
        </Stat>
      </div>

      <Grain>
        Dollars &mdash; closed-year spending from a statutory return, and a state payment
        schedule. <strong>Not students.</strong> Nothing on this page divides a dollar by a
        child: the counts come from a different return with a different census rule, and
        they are{' '}
        {L('/how-many-students-are-on-an-iep', 'their own report')} for exactly that reason.
      </Grain>

      <H2 id="findings">What this establishes</H2>
      <div className="grid gap-4 mt-5 md:grid-cols-2">
        <Insight n={1} headline={`The budget line for out-of-district tuition is the town’s share, not the cost — and that is measured, not assumed`}>
          The district&rsquo;s own restated budget figure equals DESE&rsquo;s GENERAL FUND
          column, to within a dollar or two, in{' '}
          <strong>{d.ties_count} of the {d.compared_count} years</strong> the two can be
          compared. It does not equal the all-funds column in any of them. So the line is
          what the town raises after everything else that paid for those placements has
          been taken off &mdash; and nothing in the budget document says so.
        </Insight>
        <Insight n={2} headline={`In ${fy(last.fy)}, ${last.outside_share_pct.toFixed(0)}% of what was spent on out-of-district tuition was not in the appropriation`}>
          {usd(outside)} of {usd(last.total)}. The widest year in the record is{' '}
          {fy(bigOutside.fy)}, at {bigOutside.outside_share_pct.toFixed(0)}%. A reader
          following only the budget line sees the smaller number move and has no way of
          knowing whether the thing got cheaper or somebody else started paying for more
          of it.
        </Insight>
        <Insight n={3} headline={`The circuit breaker paid ${usd(cb.paid)} in ${fy(cb.fy)} against ${usd(cb.eligible)} of eligible expense`}>
          {cbShareLast.toFixed(0)}% of what was claimed, because the state takes a
          threshold off before it reimburses anything. That the threshold is a DEDUCTION
          and not a rate is measured rather than described: eligible expense minus
          threshold equals the net claim exactly in {d.cb_identity_years.length} of the{' '}
          {d.breaker.length} years published. The number of students claimed has been as
          high as {d.cb_peak_students.students} ({fy(d.cb_peak_students.fy)}) and as low as{' '}
          {d.cb_low_students.students} ({fy(d.cb_low_students.fy)}).
        </Insight>
        <Insight n={4} headline="The state's return has no in-district special education category at all">
          Functions 9300 and 9400 &mdash; tuition to non-public schools and to
          collaboratives &mdash; are the only two codes on the whole End of Year Financial
          Report that name special education, and both are money paid to somebody else.
          Everything this project publishes about in-district special education rests on a
          classification we made, and it says so on{' '}
          {L('/bend-the-curve', 'the curve page')}.
        </Insight>
      </div>

      <H2 id="fund">What was spent, and out of which pocket</H2>
      <Body>
        DESE&rsquo;s End of Year Financial Report attributes every dollar of district
        spending either to the general fund or to grants and revolving funds. The lower
        segment of each bar is, in almost every year, exactly the figure printed in the
        district&rsquo;s own budget book. The whole bar is what was spent.
      </Body>
      <TuitionByFund spend={d.spend} />
      <Span from={d.fy_first} to={d.fy_last}
        what="functions 9300 and 9400, tuition to non-public schools and to collaboratives" />
      <TableTwin
        caption="the same rows, as numbers"
        head={['year', 'general fund', 'other funds', 'all funds', 'outside the budget', 'all funds ÷ budget line']}
        rows={d.spend.map(s => [
          fy(s.fy), usd(s.gen_fund), usd(s.grants), usd(s.total),
          `${s.outside_share_pct.toFixed(1)}%`, s.ratio ? `${s.ratio.toFixed(2)}×` : '—'])} />
      <NotShown>
        Which fund. The grants and revolving column holds every non-general fund together
        &mdash; circuit breaker, federal grants, school choice receipts, gifts. It is one
        column on a statutory return, and DESE does not break it out by fund on this file.
      </NotShown>

      <H2 id="identity">The check that establishes what the budget line is</H2>
      <Body>
        Rule 13 says quote the source rather than your rendering of it, and rule 11 says a
        budget line is net without saying so. Both are settled here by comparison rather
        than by assertion: the district&rsquo;s restated budget total for these two lines is
        set beside DESE&rsquo;s two columns for the same two functions in the same year. It
        ties to one of them and not the other, in {d.ties_count} of {d.compared_count} years.
      </Body>
      <TableTwin
        caption="the district’s own budget figure against DESE, by fund"
        head={['year', 'district budget line', 'DESE general fund', 'DESE all funds',
          'budget − general fund', 'budget − all funds', 'ties']}
        rows={d.budget_vs_fund.map(m => [
          fy(m.fy), usd(m.budget), usd(m.dese_gen_fund), usd(m.dese_all_funds),
          usd(m.vs_gen_fund), usd(m.vs_all_funds), m.ties_gen_fund ? 'yes' : 'no'])} />
      <Body>
        {d.miss_years.length
          ? `The ${d.miss_years.length === 1 ? 'exception is' : 'exceptions are'} ${d.miss_years.map(y => fy(y)).join(', ')}. An identity that holds in ${d.ties_count} years and not in ${d.miss_years.length} is still an identity with something unexplained in it, and the year is named here rather than dropped.`
          : 'There is no exception in the record.'}
      </Body>
      <NotShown>
        That the same is true of any other budget line. This is one pair of functions where
        two documents can be laid side by side because both name the same thing. Rule 11
        applies to every line; it has been demonstrated on this one.
      </NotShown>

      <H2 id="breaker">The circuit breaker</H2>
      <Body>
        The state reimburses part of what a district spends on a high-cost special education
        placement &mdash; above a threshold set per student, not from the first dollar. The
        file below is DESE&rsquo;s own payment schedule: what the district claimed, what the
        threshold took off, and what was actually paid.
      </Body>
      <CircuitBreaker rows={d.breaker} />
      <Span from={d.cb_first.fy} to={cb.fy} what="DESE’s circuit breaker reimbursement schedule" />
      <TableTwin
        caption="claimed, deducted, paid"
        head={['year', 'students', 'eligible expense', 'threshold', 'threshold ÷ students',
          'tuition reimbursed', 'transport reimbursed', 'paid', 'paid ÷ eligible',
          'eligible − threshold − claim']}
        rows={d.breaker.map(b => [
          fy(b.fy), b.students, usd(b.eligible), usd(b.threshold),
          b.threshold_per_student === null ? '—' : usd(b.threshold_per_student),
          usd(b.reimb_tuition),
          b.reimb_transport ? usd(b.reimb_transport) : '—', usd(b.paid),
          `${b.paid_share_of_eligible.toFixed(0)}%`,
          b.claim_residual ? usd(b.claim_residual) : '0'])} />
      <Body>
        The last column is that identity, checked: it is zero in{' '}
        {d.cb_identity_years.length} of the {d.breaker.length} years and not in{' '}
        {d.cb_identity_breaks.length}
        {d.cb_identity_breaks.length
          ? ` — ${d.cb_identity_breaks.map(y => fy(y)).join(', ')}`
          : ''}
        . The threshold divided by the number of students claimed rises smoothly year on
        year, which is what a per-student threshold indexed to a state rate would do; that
        reading is not stated in the file and is not asserted here.
      </Body>
      <Body>
        Transport reimbursement appears in this file only from{' '}
        {d.cb_transport_first_year ? fy(d.cb_transport_first_year) : 'no year'} onward
        &mdash; {transportYears.length} of the {d.breaker.length} years &mdash; and the
        highest payment in the whole record is {usd(cbHigh.paid)} in {fy(cbHigh.fy)}.
      </Body>
      <div className="grid gap-4 mt-5 md:grid-cols-2">
        {d.said.map(q => <Quote key={q.key} q={q} />)}
      </div>
      <NotShown>
        That the reimbursement rate is a policy Lunenburg can plan on. It is set in the
        state budget and changed inside a single year in the record &mdash; the meeting
        quote above names transport reimbursement rising from 44% to 75% for a year already
        under way. A line that fell because the reimbursement rose is not a line that got
        cheaper.
      </NotShown>

      <H2 id="beside">The two series, side by side and not netted</H2>
      <Body>
        The money spent on these placements from outside the appropriation, and the circuit
        breaker payment received, for every year both are published. They are the same order
        of magnitude. They are not the same series, and this page does not treat one as an
        explanation of the other.
      </Body>
      <TableTwin
        caption="outside the appropriation, against circuit breaker received"
        head={['year', 'spent from other funds', 'circuit breaker paid', 'difference']}
        rows={d.beside.map(b => [
          fy(b.fy), usd(b.outside_appropriation), usd(b.circuit_breaker_paid),
          usd(b.difference)])} />
      <Maybe settle="The district’s circuit breaker revolving fund cashbook for the year, which shows what the receipt was actually spent on — already the named remedy in the gap registry.">
        Most of the money spent on these placements from outside the appropriation is
        circuit breaker reimbursement being spent on the thing it was paid for. The
        difference between the two runs the same way in {sameSign} of the{' '}
        {d.beside.length} years, and in {fy(besideLast.fy)} it is {usd(besideLast.difference)}
        . Nothing here tests it: the column holds every non-general fund together, and a
        reserve account that carries a balance forward will not match a payment schedule
        year for year even when one funds the other entirely.
      </Maybe>

      <H2 id="said">What the town said about this</H2>
      <Coverage m={d.minutes} searched={d.searched} />

      <H2 id="sources">The documents</H2>
      <Provenance sources={d.sources} />

      <H2 id="limits">What this report cannot answer</H2>
      <NotEstablished rows={d.not_established} closes={d.closes} />

      <H2 id="other">The other three reports</H2>
      <OtherReports here="what-special-education-costs" />
    </Shell>
  )
}
