import type { Tab } from '../routes'
import { useEffect, useState } from 'react'
import { abs } from '../lib/abs'
import {
  AgeProfile, Caption, IncomeByAge, IncomeDistribution, MarginTest, TableTwin,
  type AgeGroup, type Bin, type Est, type Test,
} from '../components/CensusCharts'
import {
  Body, Conclusions, Coverage, Grain, H2, H3, MoreReports, NotEstablished, NotShown,
  Provenance, Quote, ReportShell, Section, Stat,
} from '../components/report'
import type { Conclusion, Said, Source, Minutes } from '../components/report'

const TAB: Tab = 'bythenumbers'
const DATA = '/data/lunenburg-by-the-numbers.json'

/** WHO ACTUALLY LIVES IN LUNENBURG — age, households, income by age, and tenure.
 *
 *  WHY THIS PAGE EXISTS, AND WHY IT IS A FRONT DOOR RATHER THAN A CHAPTER. The override
 *  argument in this town runs on two claims about people — that seniors on fixed incomes
 *  cannot carry it, and that the schools serve about 30% of homes — and until the Census
 *  tables were fetched this project could check neither. It held DESE's detail on 1,568
 *  children and effectively nothing about the other ten thousand residents. A resident
 *  should be able to read this page knowing nothing about the budget and leave knowing
 *  who the town is.
 *
 *  RULE 8 IS THE HARDEST THING ABOUT IT. This is not an argument. The senior-versus-
 *  family split is the axis the whole override runs on, and the page hands both sides the
 *  same numbers and tells nobody what to want. Where the town's own rough claim turns out
 *  to be about right — "about 30% of homes" against a measured 32.6% — it says so.
 *
 *  RULE 7 ON EVERY SENTENCE. That a sixth of the town is 65 or over is a measurement.
 *  What that implies about how they vote, what they can afford beyond the income table,
 *  or what they want, is not, and none of it is here.
 *
 *  THE TWO THINGS THIS PAGE LIVES OR DIES ON, and both are structural rather than
 *  written:
 *
 *    1. EVERY FIGURE CARRIES ITS MARGIN, in the prose, in the stat boxes, and as a
 *       whisker on every bar. These are five-year SAMPLE estimates of a town of 11,804,
 *       and a bar drawn without its margin is a sample quoted as a count.
 *    2. THE RANK IS NEVER PRINTED WITHOUT ITS OVERLAP COUNT. Lunenburg ranks 167th of 350
 *       municipalities on median household income and 205 of them have an interval that
 *       overlaps this town's, so the rank is arithmetic and the band is the finding.
 *
 *  RULE 2. Not one figure is typed into this file. Everything arrives from
 *  /data/lunenburg-by-the-numbers.json, written by
 *  scripts/build_lunenburg_by_the_numbers.py and recomputed from the CSVs by a second
 *  route in scripts/verify_lunenburg_by_the_numbers.py.
 *
 *  NO D1 AT PAGE LOAD. Static files. */

type Ages = {
  vintage: number; window: string
  population: Est
  groups: AgeGroup[]
}

type Households = {
  vintage: number; window: string
  households: Est; with_child: Est; without_child: Est
  share: number; share_moe: number; share_text: string; share_moe_text: string
}

type Tenure = {
  vintage: number; window: string
  occupied: Est; owner: Est; renter: Est
  owner_share: number; owner_share_moe: number
  owner_share_text: string; owner_share_moe_text: string
}

type Income = {
  vintage: number; window: string
  all_households: Est; bands: Est[]
  unavailable: { label: string; variable: string; estimate_raw: string
                 moe_raw: string }[]
}

type Payload = {
  about: string; grain: string; generated_by: string
  vintage: number; window: string; previous_vintage: number; previous_window: string
  ages: Ages
  households: Households
  tenure: Tenure
  income: Income
  senior_gap: {
    senior: Est; middle: Est; share: number; share_text: string
    difference: number; difference_text: string
  }
  rank: {
    window: string
    estimate: number; moe: number; text: string
    estimate_text: string; moe_text: string
    low: number; high: number; low_text: string; high_text: string
    rank: number; municipalities: number; rank_text: string
    overlap: number; overlap_text: string
    overlap_share: number; overlap_share_text: string
    best_rank_in_band: number; worst_rank_in_band: number
    indistinguishable: number; indistinguishable_text: string
    no_margin: number
    no_margin_places: { geography: string; estimate_raw: string; moe_raw: string }[]
    state_median: number; state_median_text: string
    distribution: Bin[]
  }
  per_pupil: {
    first_fy: number; last_fy: number; years: number
    last: { fy: number; districts: number; per_pupil: number; rank: number
            rank_text: string; percentile_from_bottom: number; median: number
            basis: string }
    worst_percentile_from_bottom: number; worst_percentile_text: string
    below_median_years: number; bottom_quarter_years: number
    ppyears_text: string
  }
  children: { fy: number; students: number; students_text: string }
  change: {
    old: number; new: number; old_window: string; new_window: string
    tests: Test[]; compared: number; survived: number; inside_the_margin: number
    survived_text: string; survived_labels: string[]
  }
  previous: { ages: Ages; households: Households; tenure: Tenure; income: Income }
  sentinels: {
    rows: number
    detail: { vintage: number; variable: string; estimate_raw: string
              moe_raw: string }[]
    meanings: { code: string; field: string; means: string }[]
  }
  sources: Source[]
  said: Said[]
  searched: { term: string; documents: number }[]
  minutes: Minutes
  gaps: { side: string; what: string; why: string }[]
  not_established: string[]
  closes: string
  conclusions: Conclusion[]
}

const TITLE = 'Lunenburg by the numbers'

function A({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <a className="underline" style={{ color: 'var(--series-cost)' }} href={href}>{children}</a>
  )
}

function Shell({ err, loading, standfirst, children }: {
  err?: string | null; loading?: boolean
  standfirst?: React.ReactNode; children?: React.ReactNode
}) {
  return (
    <ReportShell tab={TAB} dataUrl={DATA} title={TITLE} standfirst={standfirst}
      err={err} loading={loading}>{children}</ReportShell>
  )
}

export function LunenburgByTheNumbers() {
  const [d, setD] = useState<Payload | null>(null)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    let live = true
    fetch(DATA)
      .then(r => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then(j => { if (live) setD(j) })
      .catch(e => { if (live) setErr(String(e)) })
    return () => { live = false }
  }, [])

  if (err) return <Shell err={err} />
  if (!d) return <Shell loading />
  return <Report d={d} />
}

function Report({ d }: { d: Payload }) {
  const senior = d.ages.groups.find(g => g.key === 'senior')!
  const children = d.ages.groups.find(g => g.key === 'children')!

  return (
    <Shell standfirst={<>Who lives here, from the Census Bureau&rsquo;s {d.window}{' '}
      estimates. Every figure is a sample with a margin, and every one of them is
      printed with it.</>}>

      {/* RULE 7a: THE THING FIRST. Four numbers a resident came for, before a word about
          how the survey works. The margins are on the numbers rather than in a preamble,
          which is also the shortest possible way of making the point. */}
      <Section kind="conclusions">
        <div className="grid gap-6 mt-8 sm:grid-cols-2 lg:grid-cols-4">
          <Stat value={d.ages.population.text}>
            residents, {d.window}
          </Stat>
          <Stat value={senior.text}>
            aged {senior.label.toLowerCase()} &mdash; {senior.share_text} of the town
          </Stat>
          <Stat value={d.households.with_child.text}>
            of {d.households.households.estimate_text} households have a child under 18
          </Stat>
          <Stat value={d.rank.text}>
            median household income
          </Stat>
        </div>

        <Body>
          Each of those is an <strong>estimate from a sample</strong>, not a count, and
          the number after the &plusmn; is how far out it may be. Two figures whose
          ranges overlap are not different from each other. That matters here more than
          it would in a city: the American Community Survey reaches a small number of
          households in a town this size, so {senior.label.toLowerCase()} is{' '}
          {senior.text} &mdash; somewhere between{' '}
          {(senior.estimate - senior.moe).toLocaleString('en-US')} and{' '}
          {(senior.estimate + senior.moe).toLocaleString('en-US')} people. The{' '}
          {d.children.students_text} children in the schools, by contrast, is a count:
          the district counted them.
        </Body>

        <H2 id="what-this-establishes">What this page establishes</H2>
        <Conclusions rows={d.conclusions} />
      </Section>

      <Section kind="categorical" id="age" title="The town, by age">
        <Body>
          Five age groups, each with its own margin. {senior.label} and under 18 are the
          two the budget argument is about, and they are closer in size than either side
          usually says: {senior.text} against {children.text}.
        </Body>
        <AgeProfile groups={d.ages.groups} />
        <Caption>
          Census table B01001, {d.ages.window}, for Lunenburg town. The whiskers are each
          group&rsquo;s own margin of error; the label above each bar is its share of the
          town. A group is a sum of twelve or more published cells, so its margin is the
          root of the sum of theirs &mdash; wider than any one of them.
        </Caption>
        <NotShown>
          An age is an age. Nothing here says what any group wants, how it votes, what it
          can afford, or whether anybody in it has a child in the schools.
        </NotShown>
      </Section>

      <Section kind="categorical" id="households" title="Households, and who is in them">
        <div className="grid gap-6 mt-6 sm:grid-cols-3">
          <Stat value={d.households.households.text}>households</Stat>
          <Stat value={d.households.with_child.text}>
            have a child under 18 &mdash; {d.households.share_text} &plusmn;{' '}
            {d.households.share_moe_text}
          </Stat>
          <Stat value={d.tenure.owner_share_text}>
            of occupied homes are owner-occupied &mdash; {d.tenure.owner.estimate_text}{' '}
            of them
          </Stat>
        </div>
        <Body>
          This is the denominator under the thing people say at meetings &mdash; that the
          schools are for about a third of homes. On this measure the claim is fair. But
          it counts a child <strong>under 18</strong>, which includes children at Monty
          Tech, at private and charter schools, and children not yet old enough for
          school, so it is a ceiling on homes with a child in the Lunenburg public
          schools rather than that figure. Nothing published joins a child to a household
          to a school; that limit is{' '}
          <A href={abs('/what-we-cannot-answer')}>a registered gap</A>, not an oversight
          of this page.
        </Body>
        <TableTwin
          caption={`households and tenure, ${d.households.window}`}
          head={['', 'Estimate', 'Margin']}
          rows={[
            ['Households', d.households.households.estimate_text,
              '± ' + d.households.households.moe_text],
            ['With a child under 18', d.households.with_child.estimate_text,
              '± ' + d.households.with_child.moe_text],
            ['With no child under 18', d.households.without_child.estimate_text,
              '± ' + d.households.without_child.moe_text],
            ['Owner-occupied', d.tenure.owner.estimate_text,
              '± ' + d.tenure.owner.moe_text],
            ['Renter-occupied', d.tenure.renter.estimate_text,
              '± ' + d.tenure.renter.moe_text],
          ]}
          note={<>Tenure is the reason a levy increase is felt so directly here:{' '}
            {d.tenure.owner_share_text} of occupied homes get the bill themselves. The
            remaining {d.tenure.renter.text} pay property tax through a rent, which is a
            different thing to experience and the same thing to fund &mdash; and nothing
            here measures how much of an increase reaches a rent.</>} />
      </Section>

      <Section kind="categorical" id="income" title="What households earn">
        <Body>
          Median household income overall, and by the age of the person who heads the
          household. The last of those is the number the &ldquo;fixed incomes&rdquo;
          argument has never had: a household headed by someone 65 or over has a median
          income of {d.senior_gap.senior.text}, which is {d.senior_gap.share_text} of the{' '}
          {d.senior_gap.middle.estimate_text} a household headed by someone{' '}
          {d.senior_gap.middle.label.toLowerCase()} has &mdash; a gap of{' '}
          {d.senior_gap.difference_text} a year.
        </Body>
        <IncomeByAge all={d.income.all_households} bands={d.income.bands} />
        <Caption>
          Census table B19049, {d.income.window}. Four separate medians of four separate
          sets of households, measured in the same five years &mdash; not one
          household&rsquo;s income changing as it ages, and not a series through time.
          {d.income.unavailable.length > 0 && <> The{' '}
            {d.income.unavailable.map(u => u.label.toLowerCase()).join(' and ')}{' '}
            band is not drawn because the Census published no estimate for it.</>}
        </Caption>
        <NotShown>
          What any household can afford. Income is not wealth, not savings, not equity in
          a house and not a tax bill &mdash; and nothing in this archive joins a property
          tax payment to the age of the person who paid it. That is registered as a gap of
          its own.
        </NotShown>
      </Section>

      <Section kind="categorical" id="massachusetts"
        title="Where Lunenburg sits in Massachusetts">
        <div className="grid gap-6 mt-6 sm:grid-cols-3">
          <Stat value={d.rank.overlap_text}>
            municipalities whose income range overlaps this town&rsquo;s
          </Stat>
          <Stat value={d.rank.rank_text}>
            the rank the arithmetic gives &mdash; and it is nearly meaningless
          </Stat>
          <Stat value={d.per_pupil.last.rank_text}>
            school districts on spending for each pupil, FY{d.per_pupil.last.fy}
          </Stat>
        </div>
        <Body>
          Lunenburg&rsquo;s median household income is {d.rank.text}. Ranked against the
          other {d.rank.municipalities} municipalities in Massachusetts that puts it{' '}
          {d.rank.rank_text} &mdash; and{' '}
          <strong>{d.rank.overlap} of those {d.rank.municipalities}</strong> have an
          interval that overlaps this town&rsquo;s, spanning everything from{' '}
          {d.rank.best_rank_in_band}th to {d.rank.worst_rank_in_band}th place. The rank is
          real arithmetic on real figures and it is not a ranking anybody should carry to
          a meeting. The honest sentence is that Lunenburg is an ordinary Massachusetts
          town on income, and no amount of sorting will make it otherwise.
        </Body>
        <IncomeDistribution bins={d.rank.distribution} low={d.rank.low}
          high={d.rank.high} estimate={d.rank.estimate} />
        <Caption>
          Census table B19013, {d.rank.window}, every Massachusetts municipality. The
          statewide median municipality is {d.rank.state_median_text}.{' '}
          {d.rank.no_margin > 0 && <>{d.rank.no_margin} municipalities publish no usable
            margin &mdash; the Census top-codes a median above its highest bracket &mdash;
            so they are counted in the distribution and in neither of the two counts
            above; every one of them is far above Lunenburg.</>} On the Census&rsquo;s own
          significance test, which is stricter than an overlap of intervals,{' '}
          {d.rank.indistinguishable_text} municipalities still cannot be told apart from
          this town.
        </Caption>

        <H3>And the same town, ranked on what it spends for each pupil</H3>
        <Body>
          Both of these are true at once. On income Lunenburg is in the middle of
          Massachusetts and indistinguishable from most of it. On spending for each pupil
          it is {d.per_pupil.last.rank_text} districts in FY{d.per_pupil.last.fy}, and in
          the bottom quarter in {d.per_pupil.ppyears_text} published years. The two ranks
          are not the same kind of rank &mdash; one is municipalities on a sample estimate
          with a margin, the other is school districts on a figure the state computes from
          returns, including charter and virtual districts &mdash; so they sit side by
          side and are never differenced.{' '}
          <A href={abs('/what-other-districts-spend')}>The per-pupil comparison in
            full</A>.
        </Body>
      </Section>

      <Section kind="categorical" id="change"
        title={`Did anything change between ${d.change.old_window} and ${d.change.new_window}?`}>
        <Body>
          Mostly, nothing that can be shown. {d.change.compared} measures were compared
          across the two releases and <strong>{d.change.survived_text}</strong> clear
          their own margins:{' '}
          {d.change.survived_labels.join('; ')}. The other{' '}
          {d.change.inside_the_margin} moved by less than the combined margin of their own
          two estimates, which is a difference this survey cannot see. That includes the
          share of the town 65 or over and the share of households with a child &mdash;
          the two figures an argument about a changing town would most want.
        </Body>
        <MarginTest tests={d.change.tests} />
        <Caption>
          {d.change.old_window} against {d.change.new_window}: two five-year windows that
          do not overlap, which is what makes the comparison permissible at all.
          Consecutive releases share four years of sample and may not be differenced.
          Every difference is drawn in multiples of its own combined margin, because the
          {d.change.compared} measures are counted in people, households, dollars and
          percentage points, and one axis cannot carry four units. Population clears by
          far the largest multiple because the survey measures the town total to{' '}
          &plusmn;{d.ages.population.moe_text} where a single age group inside it is
          measured to &plusmn;{senior.moe_text}.
        </Caption>
        <NotShown>
          That nothing changed. {d.change.inside_the_margin} of these are differences the
          instrument cannot resolve, and some of them may be real. And neither release is a single year &mdash;
          each is five years averaged, so a sharp change inside a window is flattened by
          it.
        </NotShown>
      </Section>

      <Section kind="raw" id="the-record" title="The record, and what it does not carry">
        <Grain>{d.grain}</Grain>

        <H3>What the town has said about who lives here</H3>
        <div className="grid gap-3 mt-4 sm:grid-cols-2">
          {d.said.map(s => <Quote key={s.key} q={s} />)}
        </div>
        <Coverage m={d.minutes} searched={d.searched} />

        <H3>The codes that are not numbers</H3>
        <Body>
          The Census publishes sentinels where it has no figure, and each is a large
          negative number that would read as data to anything that did not know better.
          They are kept verbatim in the archive and never rendered as figures here:{' '}
          {d.sentinels.rows} cell{d.sentinels.rows === 1 ? '' : 's'} in this
          page&rsquo;s tables carry one.
        </Body>
        <TableTwin
          head={['Code', 'Where', 'What it means']}
          rows={d.sentinels.meanings.map(m => [m.code, m.field, m.means])} />

        <H3>What this page cannot answer</H3>
        <ul className="mt-4 space-y-3 max-w-2xl">
          {d.gaps.map(g => (
            <li key={g.what} className="text-[14px] leading-relaxed pl-4 border-l-2"
              style={{ color: 'var(--text-secondary)', borderColor: 'var(--axis)' }}>
              <span className="font-semibold">{g.what}</span>
              <span className="block mt-1">{g.why}</span>
            </li>
          ))}
        </ul>

        <H2 id="not-established">What this does not establish</H2>
        <NotEstablished rows={d.not_established} closes={d.closes} />

        <H2 id="sources">Where every figure came from</H2>
        <Body>
          The Census answers a query with JSON, and an API answer is a document like any
          other: each raw response is saved, hashed and published, and the figures on this
          page are read from those files rather than from a query nobody kept.
        </Body>
        <Provenance sources={d.sources} />
        <Caption>
          Built by <code>{d.generated_by}</code>, and recomputed from the CSVs by a second
          route in <code>scripts/verify_lunenburg_by_the_numbers.py</code>.
        </Caption>

        <MoreReports here={TAB} />
      </Section>
    </Shell>
  )
}
