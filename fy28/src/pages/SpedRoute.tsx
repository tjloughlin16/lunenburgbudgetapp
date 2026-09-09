import type { Tab } from '../routes'
import { abs } from '../lib/abs'
import type { Base } from '../components/report'
import {
  Body, Coverage, Grain, H2, Insight, Maybe, NotEstablished, NotShown, OtherReports,
  Provenance, Quote, Shell, Stat, useReport,
} from '../components/report'
import type { Cohort, PlaceCount } from '../components/SpedCharts'
import { PlacementCounts, RouteBars, Span, TableTwin, fy } from '../components/SpedCharts'

const TAB: Tab = 'spedroute'

/** THE ROUTE INTO OUT-OF-DISTRICT PLACEMENT. Report four of four.
 *
 *  WHY IT IS THE HARDEST OF THE FOUR TO WRITE HONESTLY. The measurement is clean and the
 *  causal sentence everybody will reach for is not available. DESE follows a cohort from
 *  where its placement started to where the same children are now, and the children who
 *  started in a substantially separate classroom end up out of district many times more
 *  often than the children who started in an inclusive setting. That is a fact about two
 *  groups of children who were ALREADY placed differently, and selection alone fits it
 *  perfectly: the children in the more intensive setting are not a random sample of the
 *  others. "Substantially separate placement leads to out-of-district" is the sentence
 *  this page must not write, and it is one word away from the sentence it does write.
 *
 *  THE BASES ARE TENS OF CHILDREN. 14.3% of 28 is four. Every percentage on this page
 *  carries its count, in the tooltip, in the table twin and in the prose, because a
 *  percentage off a base this small is a headline waiting to be made out of one family's
 *  year.
 *
 *  TWO INSTRUMENTS, KEPT APART. DESE's own out-of-district count and the town's published
 *  count from the Special Services report in each annual town report measure the same
 *  quantity with different census dates, and they agree in some years and not others. Both
 *  are published here. Neither is averaged into the other, and neither is joined to a
 *  dollar — CLAUDE.md is explicit that the placement counts do not settle the money.
 *
 *  WHAT NOBODY PUBLISHES, and it is the load-bearing gap: over what INTERVAL the
 *  trajectory measures. DESE ships the file with no documentation of the span between the
 *  starting placement and the destination, and there is nothing in the workbook. Every
 *  rate here is therefore a rate over an unstated period.
 *
 *  RULE 2. Not one figure is typed into this file. */

type Payload = Base & {
  fy_first: number; fy_last: number
  cohorts: Cohort[]; k12: Cohort[]; starts: string[]
  pooled: { start: string; years: number; cohort: number; out_of_district: number; ood_pct: number }[]
  latest_fy: number; latest: Cohort[]
  state: { fy: number; start: string; cohort: number; out_of_district: number; ood_pct: number }[]
  latest_state: { fy: number; start: string; cohort: number; out_of_district: number; ood_pct: number }[]
  counts: (PlaceCount & {
    as_of: string; collaborative_basis: string; parts_tie: boolean; chain_agrees: boolean
    page: string; document: string
  })[]
  count_no_split: number[]
  count_other_basis: string[]
  count_other_basis_years: number[]
  count_first: PlaceCount; count_last: PlaceCount
  count_peak: PlaceCount; count_low: PlaceCount
  two_counts: { fy: number; town: number; dese: number; difference: number }[]
  two_counts_agree: number; two_counts_compared: number
}

const L = (href: string, t: string) => (
  <a className="underline" style={{ color: 'var(--series-cost)' }} href={abs(href)}>{t}</a>
)

export function SpedRoute() {
  const { d, err } = useReport<Payload>('sped-route.json')
  const title = 'Who ends up out of district'
  if (!d) return <Shell tab={TAB} title={title} err={err} loading={!err} />

  const incl = d.pooled.find(p => /Inclusive/.test(p.start))!
  const sub = d.pooled.find(p => /Separate/.test(p.start))!
  const ratio = sub.ood_pct / incl.ood_pct
  const lastIncl = d.latest.find(c => /Inclusive/.test(c.start))!
  const lastSub = d.latest.find(c => /Separate/.test(c.start))!
  const stIncl = d.latest_state.find(s => /Inclusive/.test(s.start))
  const stSub = d.latest_state.find(s => /Separate/.test(s.start))
  const counted = d.counts.filter(c => c.total !== null)
  const cLast = d.count_last
  const k2 = d.cohorts.filter(c => c.grade_span === 'K-2')

  return (
    <Shell tab={TAB} title={title}
      standfirst={`Of ${sub.cohort.toLocaleString()} children who started in a substantially separate classroom, ${sub.out_of_district} are now out of district. Of ${incl.cohort.toLocaleString()} who started in an inclusive setting, ${incl.out_of_district} are.`}>

      <div className="flex flex-wrap gap-x-12 gap-y-6 mt-8">
        <Stat value={`${sub.out_of_district} of ${sub.cohort}`} tone="var(--fund-school)">
          started substantially separate, now out of district ({sub.ood_pct.toFixed(1)}%,
          pooled across {sub.years} cohorts)
        </Stat>
        <Stat value={`${incl.out_of_district} of ${incl.cohort.toLocaleString()}`} tone="var(--series-cost)">
          started in an inclusive setting, now out of district ({incl.ood_pct.toFixed(1)}%)
        </Stat>
        <Stat value={String(cLast.total)}>
          children the town reported placed out of district on 1 March {cLast.fy}
        </Stat>
      </div>

      <Grain>
        <strong>Two grains, kept apart on purpose.</strong> A placement COHORT the state
        follows, and a HEADCOUNT the town prints on 1 March. Neither is a cost. A count of
        children placed says nothing about which fund paid or what any placement cost
        &mdash; that is {L('/what-special-education-costs', 'the money report')}, and it is
        a separate page for exactly this reason.
      </Grain>

      <H2 id="findings">What this establishes</H2>
      <div className="grid gap-4 mt-5 md:grid-cols-2">
        <Insight n={1} headline={`The two starting points differ by a factor of about ${ratio.toFixed(0)}`}>
          Pooled over {sub.years} cohorts: {sub.ood_pct.toFixed(1)}% against{' '}
          {incl.ood_pct.toFixed(1)}%. In the most recent year alone it is{' '}
          {lastSub.out_of_district} of {lastSub.cohort} against {lastIncl.out_of_district}{' '}
          of {lastIncl.cohort}. <strong>The counts are the figure.</strong> A rate off a
          base of {lastSub.cohort} moves by {(100 / lastSub.cohort).toFixed(1)} points when
          one child does.
        </Insight>
        {stIncl && stSub && (
          <Insight n={2} headline={
            lastIncl.ood_pct === stIncl.ood_pct && lastSub.ood_pct === stSub.ood_pct
              ? 'Lunenburg matches the state on both starting points'
              : `Against the state, Lunenburg is ${lastIncl.ood_pct < stIncl.ood_pct ? 'lower' : lastIncl.ood_pct > stIncl.ood_pct ? 'higher' : 'level'} from an inclusive start and ${lastSub.ood_pct < stSub.ood_pct ? 'lower' : lastSub.ood_pct > stSub.ood_pct ? 'higher' : 'level'} from a substantially separate one`}>
            In {fy(d.latest_fy)} the state&rsquo;s own figures are{' '}
            {stIncl.ood_pct.toFixed(1)}% from an inclusive start (
            {stIncl.out_of_district.toLocaleString()} of{' '}
            {stIncl.cohort.toLocaleString()}) and {stSub.ood_pct.toFixed(1)}% from a
            substantially separate one. Lunenburg is {lastIncl.ood_pct.toFixed(1)}% and{' '}
            {lastSub.ood_pct.toFixed(1)}%. Both Lunenburg figures rest on tens of children
            and the state figures on tens of thousands, so this is a bearing rather than a
            comparison.
          </Insight>
        )}
        <Insight n={3} headline={`The town's own placement count runs from ${d.count_peak.total} down to ${d.count_low.total} and back to ${cLast.total}`}>
          Published every year since {fy(d.counts[0].fy)} in the Special Services report
          inside the annual town report, sourced to SIMS Report 7 and measured on 1 March.
          The peak is {d.count_peak.total} in {fy(d.count_peak.fy)}; the low is{' '}
          {d.count_low.total} in {fy(d.count_low.fy)}. It sat unread for the whole of that
          span because it is two sentences of prose with no heading naming it.
        </Insight>
        <Insight n={4} headline={`Two published counts of the same quantity agree in ${d.two_counts_agree} of the ${d.two_counts_compared} years they overlap`}>
          The town&rsquo;s figure and DESE&rsquo;s. Both are published below and neither is
          averaged into the other. Different census dates fit the disagreement and so does
          a different inclusion rule; nothing states either date beside the other.
        </Insight>
      </div>

      <H2 id="route">Where a placement leads</H2>
      <Body>
        DESE follows a cohort from the setting its placement started in to where the same
        children are now. Two starting points are published for Lunenburg, and the chart is
        the share of each that is now out of district &mdash; with the counts in the
        tooltip, because the bases are tens of children.
      </Body>
      <RouteBars k12={d.k12} />
      <Span from={d.fy_first} to={d.latest_fy}
        what="K-12 cohorts — the percentage never travels without its count" />
      <TableTwin
        caption="every cohort, with the destinations the file publishes"
        head={['year', 'grade span', 'started in', 'cohort', 'no longer on an IEP',
          'included', 'substantially separate', 'out of district', 'unaccounted']}
        rows={d.cohorts.map(c => [
          fy(c.fy), c.grade_span, c.start, c.cohort, c.no_iep, c.included, c.sub_separate,
          `${c.out_of_district} · ${c.ood_pct.toFixed(1)}%`, c.unaccounted])} />
      <Body>
        The K-2 rows in that table are a subset grade span, not a peer of the K-12 rows, so
        they are never added to them. {k2.length} of them are published.
      </Body>
      <NotShown>
        That a substantially separate placement leads to an out-of-district one. The two
        groups were already placed differently before either was followed, and children
        placed in the more intensive setting are not a random sample of the others.
        Selection fits this measurement exactly as well as any process does, and nothing
        here separates the two.
      </NotShown>
      <NotShown>
        The period. DESE publishes this file with no documentation of the interval between
        the starting placement and the destination, and nothing in the workbook states it.
        Every rate above is a rate over an unstated span, which is why none of them is
        annualised anywhere on this page.
      </NotShown>
      <Maybe settle="The district’s own record of placements by origin — how many were referred from an in-district setting and how many arrived already placed — which nothing in this archive publishes.">
        Some of the placements in the town&rsquo;s count never travelled this route at all.
        The district told the School Committee in February 2026 that children move into
        Lunenburg already requiring an out-of-district placement; such a child enters the
        count without ever appearing in a cohort followed from an in-district setting. How
        many is not established, and the quote is evidence that it happens rather than a
        measure of how often.
      </Maybe>
      <div className="grid gap-4 mt-5 md:grid-cols-2">
        {d.said.map(q => <Quote key={q.key} q={q} />)}
      </div>

      <H2 id="counts">The town&rsquo;s own count</H2>
      <Body>
        A different instrument on the same question, and the longer of the two: the Special
        Services report inside every annual town report, on 1 March, split into
        collaborative, day and residential placements. Two checks travel with it &mdash; the
        parts sum to the stated total, and each year restates the previous year&rsquo;s
        figure, which chains the series to itself.
      </Body>
      <PlacementCounts rows={counted} />
      <Span from={d.counts[0].fy} to={cLast.fy}
        what="the Special Services report, measured on 1 March each year" />
      <TableTwin
        caption="the published rows, with their own checks"
        head={['year', 'as of', 'total', 'collaborative', 'day', 'residential',
          'how the report counts collaborative', 'parts tie',
          'agrees with the next year’s restatement', 'report', 'page']}
        rows={d.counts.map(c => [
          fy(c.fy), c.as_of, c.total ?? '—', c.collaborative ?? '—', c.day ?? '—',
          c.residential ?? '—', c.collaborative_basis || '—', c.parts_tie ? 'yes' : '—',
          c.chain_agrees ? 'yes' : '—', c.document, c.page || '—'])} />
      <NotShown>
        {d.count_no_split.length
          ? `The split for ${d.count_no_split.map(y => fy(y)).join(', ')}: that year’s report prints no breakdown at all, and the total shown was recovered from the following year’s restatement. The chart draws no segments where none were published rather than interpolating them.`
          : 'Every year in this series prints its own split.'}
      </NotShown>
      <NotShown>
        That the collaborative column means the same thing in every year. In{' '}
        {d.count_other_basis_years.map(y => fy(y)).join(', ')} the report counts
        collaborative placements on a different basis &mdash; recorded in the data as{' '}
        {d.count_other_basis.map((b, i) => (
          <span key={b}>{i ? ' and ' : ''}&ldquo;{b}&rdquo;</span>
        ))}{' '}
        &mdash; so a collaborative figure from one of those years and one from a year
        marked &ldquo;parallel category&rdquo; are not the same measurement, even though
        both sum correctly to their own printed total. The chart stacks the parts as each
        report published them and does not restate the earlier ones.
      </NotShown>

      <H2 id="two">The two counts, against each other</H2>
      <Body>
        Both are published counts of Lunenburg children placed out of district, from two
        publishers, for the same school years. They are set side by side and left there.
      </Body>
      <TableTwin
        caption="the town’s count and DESE’s"
        head={['year', 'the town (1 March)', 'DESE', 'difference']}
        rows={d.two_counts.map(t => [fy(t.fy), t.town, t.dese, t.difference])} />
      <NotShown>
        Which is right. Averaging them, or picking one, would be this project adding a
        claim neither document makes &mdash; the same rule that governs the three
        irreconcilable athletics cost figures elsewhere in this archive. Publish the spread.
      </NotShown>

      <H2 id="said">What the town said about this</H2>
      <Coverage m={d.minutes} searched={d.searched} />

      <H2 id="sources">The documents</H2>
      <Provenance sources={d.sources} />

      <H2 id="limits">What this report cannot answer</H2>
      <NotEstablished rows={d.not_established} closes={d.closes} />

      <H2 id="other">The other three reports</H2>
      <OtherReports here="who-ends-up-out-of-district" />
    </Shell>
  )
}
