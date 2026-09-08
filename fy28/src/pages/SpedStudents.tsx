import { abs } from '../lib/abs'
import type { Base } from '../components/spedPage'
import {
  Body, Coverage, Grain, H2, Insight, Maybe, NotEstablished, NotShown,
  OtherReports, Provenance, Quote, Shell, Stat, useReport,
} from '../components/spedPage'
import type { Count, Para } from '../components/SpedCharts'
import { CountBars, ParaFte, Span, TableTwin, fy } from '../components/SpedCharts'

/** HOW MANY CHILDREN. Report one of four, and the four are separate on purpose.
 *
 *  WHY THIS PAGE EXISTS. CLAUDE.md rule 5: special education is about 22% of school
 *  spending and had no page here, because "the district must place a child where the plan
 *  requires" read like nothing to model. A line nobody controls still sets the size of the
 *  problem — and the first thing anybody needs about that line is how many children it is
 *  for. DESE publishes the count. Nobody in town was reading it.
 *
 *  THE GRAIN IS CHILDREN, AND NOTHING ON THIS PAGE IS A DOLLAR. That is the constraint
 *  `notes/QUEUE.md` item 10 sets — "four reports, not one; merging them into one narrative
 *  is how a proxy becomes a fact" — and it is enforced by the payload rather than by care:
 *  /data/sped-students.json contains no money at all, so a cost-per-student sentence
 *  cannot be written on this page even by accident.
 *
 *  RULE 7 IS THE WHOLE DIFFICULTY HERE. "The count rose 31 since FY2022" is a
 *  measurement. "More children need special education" is not: a count of children with an
 *  IEP is a count of children who HAVE one, and referral and eligibility practice move it
 *  without anything about any child changing. CLAUDE.md lists "the mix shifted toward
 *  intensity" as a sentence that shipped as fact when all that was established was that
 *  two counts disagreed. Every section here carries both halves.
 *
 *  RULE 13, AND IT COST THE MOST WORK ON THIS PAGE. DESE's special education staff table
 *  prints an FTE, a count and a rate on every row. The rate reproduces from the other two
 *  for paraprofessionals in all eight years and for no other staff category in any year,
 *  so this page publishes the paraprofessional row and REFUSES to publish the others as
 *  figures — the generator computes that reconciliation and fails rather than shipping a
 *  row that does not tie.
 *
 *  RULE 2. Not one figure is typed into this file. */

type Payload = Base & {
  fy_first: number; fy_last: number
  counts: Count[]
  counts_reconcile: boolean
  counts_mismatch_years: number[]
  first: Count; last: Count; lowest: Count
  change_count: number; change_share_points: number
  denominator: { fy: number; ratio_base: number; in_district: number; total: number; residual: number }[]
  denominator_all_match: boolean
  paras: Para[]; para_first: Para; para_last: Para
  staff_reconciliation: { indicator: string; reproduces: number; years: number }[]
  third_count: {
    fy: number; enrolled: number; on_iep: number; moved_in: number; moved_out: number
    repeats_prior_year: boolean
  }[]
  third_count_gap: { fy: number; movement: number; program: number; difference: number }[]
  disability: { fy: number; kind: string; count: number; share_pct: number }[]
  placement: { fy: number; setting: string; count: number; share_pct: number }[]
  placement_shortfall: {
    fy: number; parts: number; total: number; in_district: number; unaccounted: number
  }[]
  grade_span: { fy: number; span: string; count: number }[]
}

const L = (href: string, t: string) => (
  <a className="underline" style={{ color: 'var(--series-cost)' }} href={abs(href)}>{t}</a>
)

export function SpedStudents() {
  const { d, err } = useReport<Payload>('sped-students.json')
  const title = 'How many Lunenburg children are on an IEP'
  if (!d) return <Shell title={title} err={err} loading={!err} />

  const last = d.last
  const lowest = d.lowest
  const paraFall = d.para_first.fte - d.para_last.fte
  const paraPct = (100 * paraFall) / d.para_first.fte
  const staff = d.staff_reconciliation
  const good = staff.filter(s => s.reproduces === s.years)
  const bad = staff.filter(s => s.reproduces !== s.years)
  const years = [...new Set(d.disability.map(r => r.fy))].sort()
  const kinds = [...new Set(d.disability.map(r => r.kind))].sort()
  const disFirst = years[0]
  const disLast = years[years.length - 1]
  const moved = (k: string) => {
    const a = d.disability.find(r => r.fy === disFirst && r.kind === k)
    const b = d.disability.find(r => r.fy === disLast && r.kind === k)
    return a && b ? b.share_pct - a.share_pct : 0
  }
  const biggestUp = kinds.reduce((a, b) => (moved(b) > moved(a) ? b : a))
  const biggestDown = kinds.reduce((a, b) => (moved(b) < moved(a) ? b : a))
  const gap = d.third_count_gap
  const widestGap = gap.reduce((a, b) => (Math.abs(b.difference) > Math.abs(a.difference) ? b : a))
  const repeated = d.third_count.filter(t => t.repeats_prior_year)
  const latestPlacement = d.placement.filter(p => p.fy === last.fy)
  const latestShort = d.placement_shortfall.find(p => p.fy === last.fy)
  const spans = [...new Set(d.grade_span.map(g => g.span))].sort()

  return (
    <Shell title={title}
      standfirst={`${last.swd} of them, in ${fy(last.fy)}. The state publishes the count; this is what it says.`}>

      {/* -------------------------------------------------- the thing, first (rule 7a) */}
      <div className="flex flex-wrap gap-x-12 gap-y-6 mt-8">
        <Stat value={String(last.swd)}>
          children on an individual education programme in {fy(last.fy)}
        </Stat>
        <Stat value={`${last.share_pct.toFixed(1)}%`}>
          of the {last.enrolled.toLocaleString()} students DESE counts as enrolled
        </Stat>
        <Stat value={String(last.in_district)}>educated in Lunenburg</Stat>
        <Stat value={String(last.out_of_district)} tone="var(--fund-school)">
          placed out of district
        </Stat>
      </div>

      <Grain>
        Children, counted by the state at its own census. Nothing on this page is a dollar,
        an FTE budget line, or a cost per pupil &mdash; those are{' '}
        {L('/what-special-education-costs', 'a separate report')}, and they are separate
        because a student is not a dollar and every retraction this project has had to make
        came from a sentence that slid between the two.
      </Grain>

      {/* ---------------------------------------------------------------- conclusions */}
      <H2 id="findings">What this establishes</H2>
      <div className="grid gap-4 mt-5 md:grid-cols-2">
        <Insight n={1} headline={`The count is up ${d.change_count} since ${fy(lowest.fy)}, and the share is up ${d.change_share_points.toFixed(1)} points`}>
          {lowest.swd} children in {fy(lowest.fy)}, {last.swd} in {fy(last.fy)}, against a
          total enrolment that went from {lowest.enrolled.toLocaleString()} to{' '}
          {last.enrolled.toLocaleString()}. So the proportion moved from{' '}
          {lowest.share_pct.toFixed(1)}% to {last.share_pct.toFixed(1)}%. This is DESE&rsquo;s
          own published count, not a percentage multiplied back out by us.
        </Insight>
        <Insight n={2} headline="The two published parts add up, in every year">
          DESE prints a total and prints in-district and out-of-district separately.
          They reconcile exactly in all {d.counts.length} years
          {d.counts_reconcile ? '' : ` except ${d.counts_mismatch_years.join(', ')}`}. That
          matters because the staffing rates in the same file are computed on the
          in-district figure, which is{' '}
          {last.swd - last.in_district} lower than the count printed beside them &mdash; a
          disagreement {L('/what-we-cannot-answer', 'this project had registered as unexplained')}.
          It is not unexplained. The difference is the out-of-district count, exactly, in
          every year.
        </Insight>
        <Insight n={3} headline={`The state's paraprofessional FTE for Lunenburg falls ${paraPct.toFixed(0)}% while the count of children does not`}>
          {d.para_first.fte} FTE in {fy(d.para_first.fy)}, {d.para_last.fte} in{' '}
          {fy(d.para_last.fy)}. Per 100 students with disabilities that is{' '}
          {d.para_first.per_100.toFixed(1)} falling to {d.para_last.per_100.toFixed(1)}.
          The denominator over the same span went from {d.para_first.swd_base} to{' '}
          {d.para_last.swd_base}, so this is not a base effect.
        </Insight>
        <Insight n={4} headline={`Only ${good.length} of the ${staff.length} staff rows in that table reproduces from its own printed figures`}>
          Every row prints an FTE, a count and a rate. Recomputing the rate from the other
          two:{' '}
          {staff.map((s, i) => (
            <span key={s.indicator}>
              {i ? '; ' : ''}
              {s.indicator.replace('Special education ', '').replace(' per 100 SWD', '')}{' '}
              <strong>{s.reproduces} of {s.years}</strong>
            </span>
          ))}. So this page publishes the paraprofessional row and refuses to publish{' '}
          {bad.map(s => s.indicator.replace('Special education ', '').replace(' per 100 SWD', '')).join(', ')}{' '}
          as figures at all.
        </Insight>
      </div>

      {/* ------------------------------------------------------- categorical (rule 7b) */}
      <H2 id="count">The count, year by year</H2>
      <Body>
        In district and out of district, from DESE&rsquo;s Special Education Program
        Characteristics file. The two segments are the file&rsquo;s own split and they sum
        to the total it prints.
      </Body>
      <CountBars counts={d.counts} />
      <Span from={d.fy_first} to={d.fy_last} what="DESE’s published count of students with disabilities" />
      <TableTwin
        caption="the same rows, as numbers"
        head={['year', 'on an IEP', 'in district', 'out of district', 'enrolled', 'share']}
        rows={d.counts.map(c => [
          fy(c.fy), c.swd, c.in_district, c.out_of_district, c.enrolled.toLocaleString(),
          `${c.share_pct.toFixed(1)}%`])} />
      <NotShown>
        That a rising count means rising need. A count of children with an IEP is a count
        of children who have one. Referral rates, evaluation practice, eligibility
        decisions and the arrival of a family who already had a plan all move it, and none
        of those is published. A count is a real quantity and it is not a measure of how
        many children require services.
      </NotShown>
      <NotShown>
        What happened before {fy(d.fy_first)}. This file starts there. A longer series of
        the out-of-district half alone exists in the town&rsquo;s own annual reports and is
        on {L('/who-ends-up-out-of-district', 'the route report')} &mdash; on its own frame,
        because it is a different instrument measured on a different date.
      </NotShown>

      <H2 id="paras">The paraprofessional figure, and why only one row of it is published</H2>
      <Body>
        DESE reports special education staffing as a rate per 100 students with
        disabilities, and prints the FTE and the denominator beside the rate. That makes
        every row checkable: the rate has to reproduce. Recomputed on every build, the
        paraprofessional row reproduces in {d.para_last.fy - d.para_first.fy + 1} of{' '}
        {d.para_last.fy - d.para_first.fy + 1} years and the others do not, which is why
        the chart below has one line for staff and not four.
      </Body>
      <ParaFte paras={d.paras} />
      <Span from={d.para_first.fy} to={d.para_last.fy}
        what="DESE Special Education Indicators — the one staff row that reconciles" />
      <TableTwin
        caption="the row, and its own arithmetic"
        head={['year', 'FTE printed', 'students printed', 'per 100', 'recomputed']}
        rows={d.paras.map(p => [
          fy(p.fy), p.fte, p.swd_base, p.per_100.toFixed(1),
          ((100 * p.fte) / p.swd_base).toFixed(1)])} />
      <TableTwin
        caption="every staff row in the same table, and whether it reproduces"
        head={['row', 'reproduces in', 'years published']}
        rows={staff.map(s => [s.indicator, s.reproduces, s.years])} />
      <NotShown>
        That this is a count of posts. {L('/what-we-cannot-answer', 'The registry')} already
        records two reasons it cannot be: DESE&rsquo;s FTE times the published count implies
        a per-FTE figure a paraprofessional does not cost, so the state&rsquo;s figure and
        the district&rsquo;s budget line are not describing the same population; and
        DESE&rsquo;s special education TEACHER FTE for Lunenburg falls about 90% while total
        teacher FTE holds flat, which is the signature recoding would produce. A fall in
        this series is consistent with fewer posts, with the same posts reported
        differently, and with a change in how a part-time assignment is apportioned.
      </NotShown>
      <Maybe settle="EPIMS work assignment records for Lunenburg by job classification and year, which would show whether the same people were reported under a different code.">
        The federal grant money that ended in FY2025 was paying for staff in the function
        DESE calls Paraprofessionals &mdash; {L('/when-grants-end', 'measured on its own page')},
        where grants in that function fall and the general fund rises in the same year.
        Two series moving the same way is not one series explaining the other, and the
        years do not line up cleanly: this fall begins before the grant fall and continues
        after it.
      </Maybe>
      <div className="grid gap-4 mt-5 md:grid-cols-2">
        {d.said.map(q => <Quote key={q.key} q={q} />)}
      </div>

      <H2 id="mix">What the children are, by DESE&rsquo;s own categories</H2>
      <Body>
        The uncollapsed disability categories. Between {fy(disFirst)} and {fy(disLast)} the
        largest movement up is {biggestUp} ({moved(biggestUp) > 0 ? '+' : ''}
        {moved(biggestUp).toFixed(1)} points of the total) and the largest down is{' '}
        {biggestDown} ({moved(biggestDown).toFixed(1)} points). Those are movements in a
        classification, and a classification is a decision somebody made about a child
        rather than a fact about the child.
      </Body>
      <TableTwin
        caption={`share of the count, by disability category, FY${disFirst}–FY${disLast}`}
        head={['category', ...years.map(y => fy(y))]}
        rows={kinds.map(k => [
          k, ...years.map(y => {
            const r = d.disability.find(x => x.fy === y && x.kind === k)
            return r ? `${r.count} · ${r.share_pct.toFixed(1)}%` : '—'
          })])} />
      <NotShown>
        That the mix shifting means anything about severity, cost or service intensity.
        CLAUDE.md carries &ldquo;the mix shifted toward intensity&rdquo; as one of the
        sentences this project shipped as fact when nothing established it. A category is
        an eligibility label. Nothing here links a label to an hour of service or to a
        dollar, and the categories themselves were not defined by Lunenburg.
      </NotShown>

      <H2 id="setting">Where they are taught &mdash; and what that table leaves out</H2>
      <Body>
        DESE publishes a Placement breakdown in the same file. It is in-district only, and
        its parts run short of the total printed beside them. In {fy(last.fy)} the parts
        sum to {latestShort?.parts} against a published total of {latestShort?.total} and
        an in-district count of {latestShort?.in_district}. The shortfall is shown rather
        than the rows being rescaled to look complete.
      </Body>
      <TableTwin
        caption={`placement, FY${last.fy}`}
        head={['setting', 'children', 'share of the published total']}
        rows={latestPlacement.map(p => [p.setting, p.count, `${p.share_pct.toFixed(1)}%`])} />
      <TableTwin
        caption="the parts against the totals, every year"
        head={['year', 'parts sum to', 'in district', 'published total', 'unaccounted']}
        rows={d.placement_shortfall.map(s => [
          fy(s.fy), s.parts, s.in_district, s.total, s.unaccounted])} />
      <TableTwin
        caption="by grade span"
        head={['span', ...years.map(y => fy(y))]}
        rows={spans.map(s => [
          s, ...years.map(y => d.grade_span.find(g => g.fy === y && g.span === s)?.count ?? '—')])} />
      <NotShown>
        Which children the unaccounted rows are. The category is documented as in-district
        only, which explains part of the shortfall and not all of it &mdash; in{' '}
        {fy(last.fy)} the parts fall short of even the in-district count. Suppression of
        small cells fits, and so does a setting the table does not name.
      </NotShown>

      {/* ------------------------------------------------------------- raw and caveats */}
      <H2 id="third">A third file, and a fourth answer</H2>
      <Body>
        DESE also publishes a caseload movement file. Its count of children on an IEP is
        lower than the count above in every overlapping year &mdash; by{' '}
        {Math.abs(widestGap.difference)} in {fy(widestGap.fy)}, the widest &mdash; and it
        reports a different enrolment to go with it. Both are DESE, both are Lunenburg,
        both are the same school year.
      </Body>
      <TableTwin
        caption="two DESE counts of the same thing"
        head={['year', 'movement file', 'programme file', 'difference']}
        rows={gap.map(g => [fy(g.fy), g.movement, g.program, g.difference])} />
      <TableTwin
        caption="what the movement file is for — children entering and leaving services"
        head={['year', 'enrolled', 'on an IEP', 'moved in', 'moved out', 'note']}
        rows={d.third_count.map(t => [
          fy(t.fy), t.enrolled.toLocaleString(), t.on_iep, t.moved_in, t.moved_out,
          t.repeats_prior_year ? 'identical to the prior year — do not read as a second year' : ''])} />
      <NotShown>
        Which of the two is right, or what they count differently. An October census
        against a March one, a K-12 grade basis against an all-grades one, and the
        inclusion or exclusion of out-of-district children all fit. Note also that{' '}
        {repeated.length ? `${repeated.map(t => fy(t.fy)).join(' and ')} repeats the previous year across every column in this file` : 'no year repeats the previous one'}
        , which the extract flags in the data itself so that two years of movement are
        never read where one was published.
      </NotShown>

      <H2 id="said">What the town said about this</H2>
      <Body>
        Rule 15a. The measurement above is the state&rsquo;s; this is what was said out
        loud in the same years, and none of it is a measurement.
      </Body>
      <Coverage m={d.minutes} searched={d.searched} />

      <H2 id="sources">The documents</H2>
      <Provenance sources={d.sources} />

      <H2 id="limits">What this report cannot answer</H2>
      <NotEstablished rows={d.not_established} closes={d.closes} />

      <H2 id="other">The other three reports</H2>
      <Body>
        Four reports, deliberately not one. Each counts something different, and the
        difference is the point &mdash; a placement is not a cost and a dollar is not a
        child.
      </Body>
      <OtherReports here="how-many-students-are-on-an-iep" />
    </Shell>
  )
}
