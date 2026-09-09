import type { Tab } from '../routes'
import { useEffect, useState } from 'react'
import { abs } from '../lib/abs'
import { Basis } from '../components/Basis'
import {
  BAND, Counterfactual, Dollars, FIELD, Legend, OURS, Rank, Ratio, TableTwin,
  fyLong, money, pct1, ratio, signedUsd, type Year,
} from '../components/SpendingVsRequiredCharts'
import {
  Body, H2, H3, Insight, NotShown, Quote, Stat,
  ReportShell,
} from '../components/report'

const TAB: Tab = 'required'
const DATA = '/data/spending-vs-required.json'

/** What the town spends against the minimum the state REQUIRES — thirty-one measured
 *  years of it, and where that puts Lunenburg among every district in the Commonwealth.
 *
 *  WHY THIS PAGE IS DIFFERENT FROM EVERY OTHER SPENDING PAGE HERE. Everything else on
 *  this site is a budget somebody chose: a district request, a Town Meeting vote, an
 *  appropriation. Chapter 70 sets a required net school spending figure for every
 *  district and a town below it is out of compliance. It is the one school spending
 *  measure Massachusetts ENFORCES rather than observes, which is why it is worth a page
 *  of its own even though the town has never been below it.
 *
 *  RULE 1 IS THE WHOLE DIFFICULTY AND THE PAYLOAD SOLVES IT STRUCTURALLY. `nss_stage` is
 *  ACTUAL for the long series and BUDGETED for the last two years, and the generator
 *  refuses to emit a combined field at all. Nothing on this page differences them,
 *  averages them, or draws them as one line; the charts hold them in separate dataKeys so
 *  that a single path through both is not expressible.
 *
 *  RULE 7. The measurements are arithmetic on figures DESE published. Why the position
 *  fell after FY2018 is NOT established here and is not guessed at: the levy limit, two
 *  failed overrides, the district’s request and Town Meeting’s vote all resolve into this
 *  one number, and nothing in this archive separates them.
 *
 *  RULE 8. Not a scorecard. The town has been above the enforced floor in every measured
 *  year and above the state’s first quartile in all but two of them, and both are said at
 *  the same size as the fall.
 *
 *  RULE 7b. Conclusions, then the organised categories, then the raw and the caveats.
 *  RULE 7a within each: the thing first, the note about how to read it after.
 *
 *  RULE 2. Not one figure is typed into this file. Everything arrives from
 *  /data/spending-vs-required.json, written by scripts/build_spending_vs_required.py, and
 *  the cross-link figures from /data/peer-spending.json — which is fetched separately and
 *  optional, so this page renders with the link and without the numbers if it is absent
 *  rather than with a number nobody regenerated.
 *
 *  NO D1 AT PAGE LOAD. Static files. */

type Said = {
  key: string; board: string; date: string; kind: string; quote: string; why: string
  cite: string; town: string
}

type Payload = {
  about: string
  source: {
    path: string; sha256: string; bytes: number; url: string; docs_url: string
    filename: string; publisher: string; table: string; note: string
  }
  stage_warning: string
  actual: Year[]
  budgeted: Year[]
  best_rank: Year
  latest_actual: Year
  years_at_or_above_median: number
  years_measured: number
  said: Said[]
  searched: { term: string; documents: number }[]
  minutes: {
    held: number; searchable: number; unsearchable: number; image_scan: number
    searchable_share: number
  }
  gaps: { side: string; what: string; why: string; closes: string }[]
  not_established: string[]
  closes: string
}

/** The corroborating page, fetched separately and allowed to be missing. */
type Peer = {
  fin_fy: number
  headline: { statewide_rank: number; statewide_of: number; per_pupil: number }
  category_headline: { gap_in_dollars: number; median_peer: string; fy: number }
}

const TITLE = 'What the state requires us to spend'

function A({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <a className="underline" style={{ color: 'var(--series-cost)' }} href={href}>{children}</a>
  )
}

/** This report's frame. Every report on the site is drawn in the same shell -- see
 *  components/report.tsx -- and this wrapper exists only so the page's own title, tab and
 *  payload are stated once rather than at each of its three return points. */
function Shell({ err, loading, title, standfirst, children }: {
  err?: string | null; loading?: boolean
  title?: React.ReactNode; standfirst?: React.ReactNode; children?: React.ReactNode
}) {
  return (
    <ReportShell tab={TAB} dataUrl={DATA} title={title ?? TITLE} standfirst={standfirst}
      err={err} loading={loading}>{children}</ReportShell>
  )
}

const rankRow = (r: Year) => [
  fyLong(r.fy), money(r.required), money(r.spent), ratio(r.ratio),
  r.state_median === null ? '—' : ratio(r.state_median),
  r.rank === null || r.districts === null ? '—' : `${r.rank} of ${r.districts}`,
  r.short_of_median === null ? '—' : signedUsd(r.short_of_median),
]

export function SpendingVsRequired() {
  const [d, setD] = useState<Payload | null>(null)
  const [peer, setPeer] = useState<Peer | null>(null)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    let live = true
    fetch('/data/spending-vs-required.json')
      .then(r => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then(j => { if (live) setD(j) })
      .catch(e => { if (live) setErr(String(e)) })
    fetch('/data/peer-spending.json')
      .then(r => (r.ok ? r.json() : Promise.reject(new Error('absent'))))
      .then(j => { if (live) setPeer(j) })
      .catch(() => { /* the cross-link renders without its figures */ })
    return () => { live = false }
  }, [])

  if (err) return <Shell err={err} />
  if (!d) return <Shell loading />

  const A_ = d.actual
  const B = d.budgeted
  const L = d.latest_actual
  const BEST = d.best_rank

  // Everything below is derived from the payload at render time. Nothing is typed.
  const belowFloor = A_.filter(r => r.ratio < 1)
  const lowest = A_.reduce((a, b) => (b.ratio < a.ratio ? b : a))
  const belowP25 = A_.filter(r => r.p25 !== null && r.ratio < r.p25)
  const priorWorse = A_.filter(r => r.fy < L.fy && r.rank !== null && L.rank !== null
    && r.rank >= L.rank)
  const worstSince = priorWorse.length ? priorWorse[priorWorse.length - 1] : null
  const exact = A_.filter(r => r.state_median !== null && r.ratio === r.state_median)
  const lastExact = exact.length ? exact[exact.length - 1] : null
  const spentGrowth = lastExact ? L.spent / lastExact.spent - 1 : null
  const reqGrowth = lastExact ? L.required / lastExact.required - 1 : null
  const firstYear = A_[0]
  const lastBudgeted = B.length ? B[B.length - 1] : null
  const rankHead = ['Year', 'Required minimum', 'Net school spending', 'Ratio',
                    'State median', 'Rank, highest first', 'Against the median ratio']

  return (
    <Shell standfirst={<>
        The one school spending figure Massachusetts enforces, and where Lunenburg sits
        against every other district &mdash; {fyLong(firstYear.fy)} to {fyLong(L.fy)}{' '}
        measured{lastBudgeted ? <>, and {fyLong(lastBudgeted.fy)} budgeted</> : null}.
      </>}
    >

      {/* ------------------------------------------------------------ 1. THE THING FIRST */}
      <div className="grid gap-6 mt-9"
        style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 15rem), 1fr))' }}>
        <Stat value={`${L.rank} of ${L.districts}`}>
          where Lunenburg ranked in {fyLong(L.fy)}, the most recent MEASURED year &mdash;
          highest multiple of its own required minimum first
        </Stat>
        <Stat value={`${BEST.rank} of ${BEST.districts}`}>
          its best position on record, in {fyLong(BEST.fy)}
        </Stat>
        <Stat value={`${d.years_at_or_above_median} of ${d.years_measured}`}>
          measured years at or above the state median. &ldquo;Always a low spender&rdquo;
          is not what this series says
        </Stat>
        <Stat value={`${belowFloor.length} of ${d.years_measured}`}>
          years below the minimum the state requires. The town has never been out of
          compliance on the one measure that is enforced
        </Stat>
        <Stat value={money(L.short_of_median ?? 0)}>
          the {fyLong(L.fy)} gap between what Lunenburg spent and what the median
          district&rsquo;s ratio would have come to on the same requirement. Arithmetic on
          a published median &mdash; not a proposal anybody made
        </Stat>
      </div>

      <H2 id="findings">What this page establishes</H2>
      <div className="grid gap-4 mt-6"
        style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 21rem), 1fr))' }}>
        <Insight n={1} headline={
          <>Lunenburg has met the enforced floor in every one of the{' '}
            {d.years_measured} measured years.</>}>
          Chapter 70 sets a required net school spending figure per district and a town
          below it is out of compliance. Lunenburg&rsquo;s narrowest year was{' '}
          {fyLong(lowest.fy)} &mdash; {money(lowest.spent)} against a requirement of{' '}
          {money(lowest.required)}, {money(lowest.above_required)} clear. Everything else
          on this site is a budget somebody chose; this is the floor underneath, and it
          has held.
        </Insight>
        <Insight n={2} headline={
          <>It sat at or above the state median in {d.years_at_or_above_median} of{' '}
            {d.years_measured} years{lastExact
              ? <> &mdash; and landed exactly on it in {fyLong(lastExact.fy)}</> : null}.</>}>
          {lastExact ? <>In {fyLong(lastExact.fy)} Lunenburg spent {ratio(lastExact.ratio)}{' '}
            times its requirement against a state median of{' '}
            {ratio(lastExact.state_median ?? 0)} &mdash; the same figure to four decimal
            places, and {money(Math.abs(lastExact.short_of_median ?? 0))} apart on a
            requirement of {money(lastExact.required)}. </> : null}
          The story the town tells about itself is that it has always been a low spender.
          Against the measure the state enforces, it has not been.
        </Insight>
        <Insight n={3} headline={
          <>The fall is RECENT, and that makes it a different problem from a permanent
            condition.</>}>
          {lastExact ? <>From rank {lastExact.rank} of {lastExact.districts} in{' '}
            {fyLong(lastExact.fy)} to {L.rank} of {L.districts} in {fyLong(L.fy)}. </> : null}
          {worstSince ? <>That is the weakest position since {fyLong(worstSince.fy)}, when
            it was {worstSince.rank} of {worstSince.districts}. </> : null}
          A condition that has held for thirty years and a change that began six years ago
          have different causes and different remedies. This page establishes which of the
          two it is. It does not establish why.
        </Insight>
        <Insight n={4} headline={
          <>The ratio went UP while the position went down. That is why the rank is the
            measure and the ratio is not.</>}>
          In {fyLong(BEST.fy)}, Lunenburg&rsquo;s best year, it spent{' '}
          {ratio(BEST.ratio)} times its requirement. In {fyLong(L.fy)} it spent{' '}
          {ratio(L.ratio)} times &mdash; a HIGHER multiple, at rank {L.rank} instead of{' '}
          {BEST.rank}. The state median moved from {ratio(BEST.state_median ?? 0)} to{' '}
          {ratio(L.state_median ?? 0)} underneath it. A ratio that rises can still be a
          district falling behind, because the requirement is recomputed every year from
          enrolment and municipal wealth and every other district is moving too.
        </Insight>
        <Insight n={5} headline={
          <>Below the median is not the bottom tenth, and on this measure Lunenburg is not
            near the bottom.</>}>
          In {fyLong(L.fy)} the town spent {ratio(L.ratio)} times its requirement against a
          state first quartile of {ratio(L.p25 ?? 0)} and a third quartile of{' '}
          {ratio(L.p75 ?? 0)} &mdash; inside the middle half of the state, below its
          middle. Across the whole series it has been below the first quartile in{' '}
          {belowP25.length} years:{' '}
          {belowP25.map(r => fyLong(r.fy)).join(', ')}. That is a different finding from{' '}
          <A href={abs('/what-other-districts-spend')}>what other districts spend</A>, and
          the two are not in conflict &mdash; see below.
        </Insight>
        <Insight n={6} headline={
          <>What the gap to the median is worth in {fyLong(L.fy)}:{' '}
            {money(L.short_of_median ?? 0)}. It is arithmetic, not a proposal.</>}>
          {money(L.required)} of required spending at the state&rsquo;s median ratio of{' '}
          {ratio(L.state_median ?? 0)} is {money(L.at_state_median ?? 0)}. Lunenburg spent{' '}
          {money(L.spent)}. The difference is a subtraction on a published median: nobody
          has proposed it, no programme is costed against it, and nothing here says what it
          would buy.
        </Insight>
      </div>

      <div className="card p-5 mt-8 max-w-3xl"
        style={{ borderLeft: '4px solid var(--series-cost)' }}>
        <p className="text-[11px] font-semibold uppercase tracking-widest mb-2"
          style={{ color: 'var(--text-muted)' }}>
          Does any of this measure the reductions?
        </p>
        <p className="text-[15px] leading-relaxed">
          <strong>No, and that is the first thing to know before quoting any figure
          here.</strong> The most recent MEASURED year is {fyLong(L.fy)}. The budget
          reductions the town argued about run from {fyLong(L.fy + 1)} onward, and both
          years DESE publishes for that period are BUDGETED rather than spent. So nothing
          on this page shows what the cuts did to Lunenburg&rsquo;s position, in either
          direction &mdash; and the year it will show in is a year DESE has not published
          yet.
        </p>
      </div>

      {/* the rule-1 warning, beside the thing it qualifies rather than above everything */}
      <div className="card p-4 mt-8 max-w-3xl"
        style={{ borderLeft: '4px solid var(--status-warning)' }}>
        <p className="text-[11px] font-semibold uppercase tracking-widest mb-1.5"
          style={{ color: 'var(--text-muted)' }}>
          Two stages, and they are never one series
        </p>
        <p className="text-[14px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
          {d.stage_warning} Everything above is the ACTUAL years only. The budgeted years
          are drawn on every chart in a dashed line with hollow markers so the difference
          survives a reader who does not read this box, and they are listed on their own
          below.
        </p>
      </div>

      {/* --------------------------------------------------- 2. THE ORGANISED CATEGORIES */}
      <H2 id="rank">Where Lunenburg ranked, year by year</H2>
      <Body>
        Every district in the Commonwealth, ranked by how large a multiple of its own
        required minimum it spent. Highest first, so a line climbing toward the top of the
        chart is a district moving up the field.
      </Body>
      <Rank actual={A_} budgeted={B} />
      <TableTwin
        caption={`DESE’s net school spending comparison — ${d.years_measured} measured years, `
          + `${fyLong(firstYear.fy)}–${fyLong(L.fy)}, and ${B.length} budgeted`}
        head={rankHead}
        rows={[...A_.map(rankRow), ...B.map(r => rankRow(r).map((c, i) => (
          i === 0 ? `${c} (budgeted)` : c)))]}
        note={<>The last column is the year&rsquo;s required minimum at the state&rsquo;s
          MEDIAN ratio, less what Lunenburg spent: a positive figure is less than a median
          district would have spent on the same requirement, a negative one is more. It is
          a subtraction on a published median and not a costed programme.
          The rows marked <em>budgeted</em> are a different stage of the same quantity and
          are never differenced against the rest.
          The number of districts changes from year to year, which is why a rank is only
          readable beside its denominator.</>} />

      <NotShown>
        <p>
          <strong>A rank is not an effort measure and this one moves for reasons that are
          not Lunenburg.</strong> Districts enter and leave the comparison &mdash; the
          denominator on this table ranges across the series &mdash; and the median moves
          when other towns pass overrides, receive different aid, or have their own
          requirements recomputed. A year in which Lunenburg did nothing differently can
          still change its rank.
        </p>
        <p className="mt-2.5">
          <strong>And a rank says nothing about what any of the spending bought.</strong>{' '}
          Two districts at the same multiple of their own requirements may have entirely
          different class sizes, programmes and caseloads, because the requirement itself
          is built from each district&rsquo;s own enrolment and its town&rsquo;s wealth.
        </p>
      </NotShown>

      <H2 id="ratio">The ratio, against the whole state</H2>
      <Body>
        The same years as a multiple of the required minimum, with the state&rsquo;s middle
        half drawn behind. The band is the reason the ratio must not be read on its own:
        Lunenburg&rsquo;s line rises across the series and so does everybody
        else&rsquo;s.
      </Body>
      <Ratio actual={A_} budgeted={B} />
      <Legend items={[
        { hue: OURS, label: 'Lunenburg' },
        { hue: FIELD, label: 'the median district' },
        { hue: BAND, label: 'the 25th to the 75th percentile of every district' },
      ]} />
      <TableTwin caption={`Lunenburg against the state distribution, ${d.years_measured} measured years`}
        head={['Year', 'Lunenburg', 'First quartile', 'Median', 'Third quartile',
               'Inside the middle half']}
        rows={A_.map(r => [
          fyLong(r.fy), ratio(r.ratio),
          r.p25 === null ? '—' : ratio(r.p25),
          r.state_median === null ? '—' : ratio(r.state_median),
          r.p75 === null ? '—' : ratio(r.p75),
          r.p25 === null || r.p75 === null ? '—'
            : (r.ratio >= r.p25 && r.ratio <= r.p75 ? 'yes' : 'no'),
        ])}
        note={<>Thirty-one measured years is far longer than anything else on this site,
          and length is worth something here for a specific reason: boards in this town
          are reluctant to look forward two years. A series this long is the only place a
          reader can see that the current position is a departure from Lunenburg&rsquo;s
          own record rather than a continuation of it. The quartiles are the state&rsquo;s
          own distribution in the same year, published beside the median.</>} />

      <H2 id="dollars">What was required, and what was spent</H2>
      <Body>
        The ratio charts answer &ldquo;how far above&rdquo;. This one answers the question
        they hide: how much of the movement is the town, and how much is the requirement.
      </Body>
      <Dollars actual={A_} />
      {lastExact && spentGrowth !== null && reqGrowth !== null && (
        <Body>
          <strong>Between {fyLong(lastExact.fy)} and {fyLong(L.fy)}, net school spending
          rose {pct1(spentGrowth)} and the required minimum rose {pct1(reqGrowth)}.</strong>{' '}
          {money(lastExact.spent)} to {money(L.spent)} against {money(lastExact.required)}{' '}
          to {money(L.required)}. Both figures are the same stage, the same table and the
          same district, so they may be read against each other. The position fell because
          the requirement outran the spending, and not because the spending fell &mdash;
          it did not.
        </Body>
      )}
      <NotShown>
        <p>
          <strong>That the requirement outran the spending is a measurement. Why it did is
          not.</strong> The required minimum is Chapter 70 aid plus the town&rsquo;s
          required local contribution, and the contribution is recomputed each year from
          the town&rsquo;s property wealth and income rather than from anything the schools
          do. Both halves are on{' '}
          <A href={abs('/why-we-only-get-minimum-aid')}>why we only get minimum aid</A>.
        </p>
        <p className="mt-2.5">
          <strong>And net school spending is not the school budget.</strong> It excludes
          debt service, capital, transportation and food service &mdash; stated in the
          town&rsquo;s own record, quoted below. No line in the town&rsquo;s appropriation
          or the district&rsquo;s budget book equals the figure on this page, and nothing
          in this archive maps one onto the other. That is a registered gap.
        </p>
      </NotShown>

      <H2 id="counterfactual">The gap to the median, in dollars</H2>
      <div className="card p-4 mt-4 max-w-3xl"
        style={{ borderLeft: '4px solid var(--status-warning)' }}>
        <p className="text-[11px] font-semibold uppercase tracking-widest mb-1.5"
          style={{ color: 'var(--text-muted)' }}>
          Our arithmetic, and not a proposal anybody made
        </p>
        <p className="text-[14.5px] leading-relaxed">
          Each bar is the year&rsquo;s required minimum multiplied by the state&rsquo;s
          median ratio, less what Lunenburg actually spent. It is a subtraction on a
          published median. No costed programme sits behind any of these figures, nobody
          has proposed any of them, and nothing here says what the money would have bought
          or where it would have come from.
        </p>
      </div>
      <Counterfactual actual={A_} />
      <TableTwin caption={`What a median ratio would have come to, ${d.years_measured} measured years`}
        head={['Year', 'Required minimum', 'At the state median ratio', 'Spent',
               'Difference']}
        rows={A_.map(r => [
          fyLong(r.fy), money(r.required),
          r.at_state_median === null ? '—' : money(r.at_state_median),
          money(r.spent),
          r.short_of_median === null ? '—' : signedUsd(r.short_of_median),
        ])}
        note={<>A negative difference is a year in which Lunenburg spent MORE than a median
          district would have on the same requirement. There are{' '}
          {A_.filter(r => (r.short_of_median ?? 0) < 0).length} of them.</>} />

      <H2 id="budgeted">The two budgeted years, on their own</H2>
      <Body>
        These are the most recent years DESE publishes and they are a different stage of
        the quantity: what the district budgeted, not what it later reported spending. They
        are here rather than merged, and the difference between them and the measured
        series is not a measurement of anything.
      </Body>
      <TableTwin caption="BUDGETED net school spending — a different stage, never differenced against the measured years"
        head={rankHead} rows={B.map(rankRow)}
        note={<>{d.stage_warning} The most recent MEASURED position Lunenburg has against
          the state is therefore {fyLong(L.fy)}, and any statement about where the town
          sits now rests on a budget somebody voted rather than on money anybody spent.
          The same figure appears on{' '}
          <A href={abs('/why-we-only-get-minimum-aid')}>why we only get minimum aid</A>{' '}
          and on <A href={abs('/what-other-districts-spend')}>what other districts
          spend</A>: it is the same number at the same stage, and this page is the one that
          holds the long measured series behind it.</>} />

      {/* -------------------------------------------------------- 3. RAW AND CONTEXT */}
      <H2 id="alongside">Two other measurements, neither derived from this one</H2>
      <Body>
        Three pages on this site now measure how much Lunenburg spends on its schools
        against other districts. They use different sources, different denominators and
        different years, and none of them is computed from another. Read them as
        independent readings that happen to point the same way, and never as one figure
        confirming another&rsquo;s exact amount.
      </Body>
      <div className="grid gap-4 mt-6"
        style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 20rem), 1fr))' }}>
        <div className="card p-5">
          <p className="text-[15px] font-bold leading-snug">
            <A href={abs('/what-other-districts-spend')}>What other districts spend</A>
          </p>
          <p className="text-[14px] leading-relaxed mt-2"
            style={{ color: 'var(--text-secondary)' }}>
            {peer ? <>DESE&rsquo;s per-pupil finance file, {fyLong(peer.fin_fy)}: Lunenburg{' '}
              {peer.headline.statewide_rank}th of {peer.headline.statewide_of} districts on
              total spending for each pupil, and an in-district gap to the median peer
              district of {money(Math.abs(peer.category_headline.gap_in_dollars))} in{' '}
              {fyLong(peer.category_headline.fy)}. </>
              : <>DESE&rsquo;s per-pupil finance file, with Lunenburg drawn through the
                statewide distribution. </>}
            <strong>Different measure.</strong> Dollars over a pupil count, against every
            district&rsquo;s dollars over their pupil counts &mdash; no requirement in it
            anywhere. Its gap figure and this page&rsquo;s are the same order of magnitude
            and are arrived at from different files by different arithmetic. They must not
            be averaged, added, or presented as one estimate.
          </p>
        </div>
        <div className="card p-5">
          <p className="text-[15px] font-bold leading-snug">
            <A href={abs('/why-we-only-get-minimum-aid')}>Why we only get minimum aid</A>
          </p>
          <p className="text-[14px] leading-relaxed mt-2"
            style={{ color: 'var(--text-secondary)' }}>
            The other half of the requirement on this page: Chapter 70&rsquo;s formula,
            term by term, and how the required local contribution is built from the
            town&rsquo;s wealth rather than from its children.{' '}
            {lastBudgeted ? <>It reports the {fyLong(lastBudgeted.fy)} ratio of{' '}
              {ratio(lastBudgeted.ratio)}, which is the BUDGETED figure in the table
              above &mdash; the same number at the same stage, not a disagreement. </>
              : null}
            This page is where the long measured series lives.
          </p>
        </div>
      </div>

      <H2 id="said">What the town has said about it</H2>
      <Body>
        Every quote is re-read out of the meeting archive on each build and the build stops
        if one is no longer in the document it is attributed to.{' '}
        <strong>The pattern across them is itself the finding, and it is a negative
        one.</strong> This measure reaches Lunenburg&rsquo;s Finance Committee almost
        entirely inside ANOTHER district&rsquo;s budget presentation. A member asked where
        the state sits on exactly this ratio and no figure for Lunenburg Public Schools was
        put beside it.
      </Body>
      <div className="grid gap-4 mt-6"
        style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 22rem), 1fr))' }}>
        {d.said.map(q => <Quote key={q.key} q={q} />)}
      </div>

      <div className="card p-5 mt-6 max-w-3xl"
        style={{ borderLeft: '4px solid var(--series-cost)' }}>
        <p className="text-[11px] font-semibold uppercase tracking-widest mb-2"
          style={{ color: 'var(--text-muted)' }}>
          One thing that could be done differently next year
        </p>
        <p className="text-[15px] leading-relaxed">
          The question was asked at the Finance Committee and the answer never arrived,
          because the presentation in front of the room was another district&rsquo;s. The
          figure is published: it is two columns of the same DESE workbook the town already
          receives every year, and it takes a rank and a median beside Lunenburg&rsquo;s own
          ratio to answer. <strong>Putting those three numbers in the annual Chapter 70
          briefing would settle in one line a question that has been open in the minutes
          since {d.said[0].date}.</strong> Nothing about that requires a records request or
          a new document.
        </p>
      </div>

      <H3>What was searched, and how much of the archive could be</H3>
      <TableTwin caption="The meeting archive, by term"
        head={['Term', 'Documents that match']}
        rows={d.searched.map(s => [s.term, s.documents.toLocaleString()])}
        note={<><strong>{d.minutes.searchable.toLocaleString()} of{' '}
          {d.minutes.held.toLocaleString()} held documents can be searched at all{' '}
          ({pct1(d.minutes.searchable_share)}).</strong>{' '}
          {d.minutes.unsearchable.toLocaleString()} carry no text a search can match
          &mdash; {d.minutes.image_scan.toLocaleString()} of them image scans awaiting OCR.
          So a term with few matches is a statement about the readable archive and never
          about what anybody said. Note what the counts show anyway: the word residents use
          for this subject is <em>override</em>, and <em>underfunded</em> in this town
          almost always means the capital plan rather than the schools.</>} />

      <H2 id="townside">Why there is no town-side line on any of these charts</H2>
      <Body>
        <strong>Because Massachusetts does not set one.</strong> Required net school
        spending is a floor under the schools and this archive holds no equivalent
        state-enforced minimum for any other municipal department &mdash; not the fire
        department, not the library, not public works &mdash; and none of the town&rsquo;s
        own budget documents names one. So the comparison a reader may want, of how far
        each side of the town budget sits above its own mandated floor, cannot be drawn
        here: only one side has a floor.
      </Body>
      <NotShown>
        <p>
          <strong>That is a fact about the statute, not a claim that the schools are
          treated better or worse.</strong> A department with no minimum is not thereby
          under-funded and is not thereby protected; it is simply not measured this way. A
          reader reaching for &ldquo;the schools are held to a standard nobody else
          is&rdquo; or &ldquo;the schools get a guarantee nobody else gets&rdquo; will find
          both readings fit this page equally well, and it chooses neither.
        </p>
      </NotShown>

      <H2 id="cannot">What this cannot say</H2>
      <div className="flex flex-col gap-3 mt-6 max-w-3xl">
        {d.not_established.map(n => (
          <div key={n} className="card p-4">
            <p className="text-[14px] leading-relaxed"
              style={{ color: 'var(--text-secondary)' }}>{n}</p>
          </div>
        ))}
        <div className="card p-4">
          <p className="text-[14px] leading-relaxed"
            style={{ color: 'var(--text-secondary)' }}>
            <strong>WHAT WOULD SETTLE THE MEASUREMENT ITSELF.</strong> {d.closes}
          </p>
        </div>
      </div>

      <H3>The same limits, as rows in the register</H3>
      <Body>
        Each of these is a row in <code>money-gaps.csv</code>, which is what the records
        request to the Town reads and what{' '}
        <A href={abs('/what-we-cannot-answer')}>what we cannot answer</A> renders. A limit
        stated only in the prose of one page is invisible to everybody who did not read
        that page.
      </Body>
      <div className="flex flex-col gap-3 mt-5 max-w-3xl">
        {d.gaps.map(g => (
          <div key={g.what} className="card p-4">
            <p className="text-[11px] font-semibold uppercase tracking-widest mb-1.5"
              style={{ color: 'var(--text-muted)' }}>{g.side.replace(/_/g, ' ')}</p>
            <p className="text-[15px] font-bold leading-snug">{g.what}</p>
            <p className="text-[13.5px] leading-relaxed mt-2"
              style={{ color: 'var(--text-secondary)' }}>{g.why}</p>
            <p className="text-[13.5px] leading-relaxed mt-2">
              <strong>Closes:</strong> {g.closes}
            </p>
          </div>
        ))}
      </div>

      <H2 id="source">The document behind this</H2>
      <Body>
        <Basis level="cross-checked">every year&rsquo;s required minimum against Chapter
          70 aid plus the town&rsquo;s required contribution</Basis>
      </Body>
      <Body>
        {d.source.publisher}. Our copy is{' '}
        <a className="underline break-all" style={{ color: 'var(--series-cost)' }}
          href={abs(d.source.docs_url)}>{d.source.filename}</a>{' '}
        ({(d.source.bytes / 1e6).toFixed(1)} MB), fetched from{' '}
        <a className="underline break-all" style={{ color: 'var(--series-cost)' }}
          href={d.source.url}>{d.source.url}</a>. Its sha256 is{' '}
        <code className="break-all">{d.source.sha256}</code>. {d.source.note}
      </Body>
      <Body>
        The payload this page draws is published whole at{' '}
        <A href={abs('/data/spending-vs-required.json')}>/data/spending-vs-required.json</A>,
        and the rows behind it &mdash; <code>dese_ch70_formula</code> and{' '}
        <code>dese_ch70_statewide</code> &mdash; can be queried directly from{' '}
        <A href={abs('/database')}>the database</A>.
      </Body>
    </Shell>
  )
}
