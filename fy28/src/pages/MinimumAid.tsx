import { useEffect, useState } from 'react'
import { abs } from '../lib/abs'
import { Basis } from '../components/Basis'
import {
  Adjustment, AidTerms, FLOOR, FORMULA, Legend, PerPupil, RequiredShare, TableTwin,
  dollars2, fy, money, share, signed,
  type ContribRow, type DistRow, type YearRow,
} from '../components/MinimumAidCharts'

/** Chapter 70, term by term — why the formula pays Lunenburg the Legislature's floor.
 *
 *  WHAT THIS PAGE IS, AND WHAT /state-aid IS. `/state-aid` is state aid as a WHOLE: the
 *  cherry sheet, the accounts in the town's ledger, what was budgeted against what was
 *  received, and the growth rate the projection uses. This page is ONE program inside it,
 *  and it is about the FORMULA — DESE's own aid components for Lunenburg, FY2007 to FY2026.
 *
 *  RULE 11 IS THE REASON IT SAYS SO IN THE FIRST SCREEN. This project once described
 *  $11,404,917 — ALL state aid in the Governor's FY27 budget — as Chapter 70, which is
 *  78.7% of it, and published a share eight points too high for months. Nothing on this
 *  page is total state aid, and the page names what it is not before a reader can make the
 *  same substitution.
 *
 *  RULE 1. Every series here is one stage: DESE's published calculation for the fiscal
 *  year. Two Governor's-stage figures appear, both quoted from meeting minutes, and they
 *  are printed BESIDE the enacted ones as an illustration of the gap between stages. They
 *  are never subtracted from them.
 *
 *  RULE 7. The measurements are exact arithmetic on published figures. Everything about
 *  WHY — why the town crossed from above its target contribution to below it, what one
 *  more child would do — is separated out and labelled, and the marginal-pupil question is
 *  stated as unsettled rather than answered.
 *
 *  RULE 7b. Conclusions, then the organised categories, then the raw and the caveats.
 *  RULE 7a within each: the thing first, the note about how to read it after.
 *
 *  RULE 2. Not one figure is typed into this file. Everything arrives from
 *  /data/minimum-aid.json, written by scripts/build_minimum_aid.py.
 *
 *  NO D1 AT PAGE LOAD. One static file. */

type Said = {
  key: string; board: string; date: string; kind: string; quote: string; why: string
  cite: string; town: string
}

type Payload = {
  about: string
  not_this_page: string
  source: {
    path: string; sha256: string; bytes: number; url: string; docs_url: string
    filename: string; publisher: string; sheets: string[]; stage: string
  }
  definitions: { cell: string; term: string; text: string }[]
  fy_first: number; fy_last: number; years: number
  headline: {
    fy: number; prior_fy: number; aid: number; prior_aid: number; increase: number
    minimum_aid_increment: number; foundation_aid_increment: number
    enrollment: number; per_pupil: number; foundation_budget: number
    foundation_per_pupil: number; times: number; target_aid_pct: number
    aid_share_of_foundation: number; cells: Record<string, string>
  }
  why_zero: {
    fy: number; foundation_budget: number; required_local_contribution: number
    need: number; prior_aid: number; headroom: number
    rule_holds_in: number; rule_of: number; rule_broken_in: number[]
    definition_cell: string
  }
  floor: {
    fy: number; districts: number; shared_rate: number | null; districts_at_rate: number
    lunenburg: number; lunenburg_at_rate: boolean
    rows: { district: string; per_pupil: number; min_per_pupil: number }[]
  }[]
  on_floor: number[]
  series: YearRow[]
  unreconciled: { fy: number; change: number; components_sum: number
    unexplained: number; reduction_column: number | null }[]
  reconciles_in: number; reconciles_of: number
  contribution: ContribRow[]
  contribution_build_holds: number; contribution_build_of: number
  contribution_build_anomaly: {
    fy: number; preliminary_printed: number; prior_rlc_times_mrgf: number
    rlc_printed: number; cells: Record<string, string>
  }[]
  regime: {
    above_first: number; above_last: number; above_years: number
    below_first: number; below_last: number; below_years: number
    effort_reduction_total: number; dollar_increment_total: number; note: string
    increment_first: number | null; increment_years: number
    reduction_first: number | null; reduction_years: number; quiet_years: number
  }
  share: {
    first_fy: number; first: number; low_fy: number; low: number
    last_fy: number; last: number; rose_since_trough: number; fell_since_trough: number
  }
  allocation: {
    fy: number; town_rlc: number; town_foundation_budget: number
    district_rlc: number; district_foundation_budget: number; predicted: number
    difference: number; holds: boolean; elsewhere_rlc: number; elsewhere_foundation: number
  }[]
  distribution: DistRow[]
  wealth: {
    fy_from: number; fy_to: number; municipalities: number
    eqv_growth: number; eqv_rank: number; eqv_median: number
    cey_growth: number; cey_rank: number; cey_median: number
  }
  marginal: {
    fy: number; foundation_per_pupil: number
    district_rlc_now: number; district_rlc_after: number; rlc_change: number
    need_now: number; need_after: number; need_change: number
    headroom: number; pupils_to_close: number; town_rlc_change: number
    assumptions: string[]; is_measurement: boolean
  }
  since: {
    from_fy: number; to_fy: number; aid_from: number; aid_to: number
    aid_change: number; aid_pct: number; required_from: number; required_to: number
    required_change: number; required_pct: number
    enrollment_from: number; enrollment_to: number
    foundation_from: number; foundation_to: number; stage: string
  }
  stage_examples: {
    key: string; fy: number; stage: string; said: number; said_on: string
    board: string; enacted: number
  }[]
  allocation_summary: {
    holds_in: number; of: number; exceptions: number[]; worst: number
  }
  corroboration: {
    board: string; date: string; stated_municipal: number; stated_state: number
    fy: number; recomputed: number; scope: string
  }
  spending: {
    years: number; first_fy: number; last_fy: number; above_required: number
    lowest: number; latest: number; latest_stage: string; stages: string[]
    rows: { fy: number; stage: string; pct_of_required: number }[]
  }
  said: Said[]
  searched: { term: string; documents: number }[]
  minutes: {
    held: number; searchable: number; unsearchable: number; image_scan: number
    searchable_share: number
  }
  gaps: { side: string; what: string; why: string; closes: string | null }[]
  not_established: string[]
}

const TITLE = 'Why we only get minimum aid'

function H2({ id, children }: { id?: string; children: React.ReactNode }) {
  return (
    <h2 id={id} className="text-2xl font-bold tracking-tight mt-14 mb-1 max-w-3xl
                           scroll-mt-24">{children}</h2>
  )
}

function H3({ children }: { children: React.ReactNode }) {
  return <h3 className="text-[17px] font-bold tracking-tight mt-9 mb-1 max-w-3xl">{children}</h3>
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
      <div className="text-3xl font-bold tracking-tight tnum"
        style={tone ? { color: tone } : undefined}>{value}</div>
      <div className="text-[13px] leading-snug mt-1 max-w-[16rem]"
        style={{ color: 'var(--text-secondary)' }}>{children}</div>
    </div>
  )
}

function Insight({ n, headline, children }: {
  n: number; headline: React.ReactNode; children: React.ReactNode
}) {
  return (
    <div className="card p-5">
      <div className="text-[11px] font-semibold uppercase tracking-widest mb-2"
        style={{ color: 'var(--text-muted)' }}>Finding {n}</div>
      <p className="text-[17px] font-bold leading-snug">{headline}</p>
      <div className="text-[14px] leading-relaxed mt-2.5"
        style={{ color: 'var(--text-secondary)' }}>{children}</div>
    </div>
  )
}

/** The half of every section that says what the measurement does NOT establish. */
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

function Quote({ q }: { q: Said }) {
  return (
    <div className="card p-4">
      <p className="text-[15px] leading-relaxed">&ldquo;{q.quote}&rdquo;</p>
      <p className="text-[12px] mt-2" style={{ color: 'var(--text-muted)' }}>
        {q.board} &middot; {q.kind.toLowerCase()} &middot; {q.date} &middot;{' '}
        <a className="underline" style={{ color: 'var(--series-cost)' }}
          href={abs(q.cite)}>our copy</a>{' '}
        &middot; <a className="underline" style={{ color: 'var(--series-cost)' }}
          href={q.town}>the town&rsquo;s</a>
      </p>
      <p className="text-[13.5px] leading-relaxed mt-2.5"
        style={{ color: 'var(--text-secondary)' }}>{q.why}</p>
    </div>
  )
}

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div className="mx-auto max-w-6xl px-5 pt-14 pb-16">
      <h1 className="text-3xl font-bold tracking-tight">{TITLE}</h1>
      {children}
    </div>
  )
}

export function MinimumAid() {
  const [d, setD] = useState<Payload | null>(null)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    let live = true
    fetch('/data/minimum-aid.json')
      .then(r => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then(j => { if (live) setD(j) })
      .catch(e => { if (live) setErr(String(e)) })
    return () => { live = false }
  }, [])

  if (err) {
    return (
      <Shell>
        <div className="card p-5 mt-8" style={{ borderLeft: '4px solid var(--status-warning)' }}>
          <p className="text-[15px] font-bold mb-1">The formula did not load</p>
          <p className="text-[13.5px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
            {err}. Nothing on this page is typed into it, so with the file missing there is
            nothing to show rather than something stale. The rows are published at{' '}
            <a className="underline" style={{ color: 'var(--series-cost)' }}
              href={abs('/data/minimum-aid.json')}>/data/minimum-aid.json</a>.
          </p>
        </div>
      </Shell>
    )
  }
  if (!d) {
    return (
      <Shell>
        <p className="mt-4 text-[15px]" style={{ color: 'var(--text-muted)' }}>
          Loading DESE&rsquo;s aid components&hellip;
        </p>
      </Shell>
    )
  }

  const H = d.headline
  const Z = d.why_zero
  const R = d.regime
  const W = d.wealth
  const M = d.marginal
  const SH = d.share
  const alloc = d.allocation[d.allocation.length - 1]
  const latestFloor = d.floor[d.floor.length - 1]
  const atRate = latestFloor.rows.filter(
    r => latestFloor.shared_rate !== null
      && Math.abs(r.per_pupil - latestFloor.shared_rate) < 0.005)
  const distLast = d.distribution[d.distribution.length - 1]
  const soa = d.series.find(s => s.change !== null && !d.on_floor.includes(s.fy)
    && s.fy > Math.min(...d.on_floor))
  const contribLast = d.contribution[d.contribution.length - 1]
  const contribFirstBelow = d.contribution.find(c => c.fy === R.below_first)!
  const C = d.corroboration
  const N = d.since
  const SP = d.spending

  return (
    <div className="mx-auto max-w-6xl px-5 pt-14 pb-16">
      <h1 className="text-3xl font-bold tracking-tight">{TITLE}</h1>
      <p className="text-[15px] leading-relaxed max-w-2xl mt-3"
        style={{ color: 'var(--text-secondary)' }}>
        Chapter 70 alone, term by term, from DESE&rsquo;s own workbook &mdash; {fy(d.fy_first)}{' '}
        to {fy(d.fy_last)}.
      </p>

      {/* ---------------------------------------------------------- 1. WHAT IT ESTABLISHES */}
      <div className="grid gap-6 mt-9"
        style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 15rem), 1fr))' }}>
        <Stat value={dollars2(H.per_pupil)} tone={FLOOR}>
          the whole of {fy(H.fy)}&rsquo;s Chapter 70 increase, for each of{' '}
          {H.enrollment.toLocaleString()} foundation pupils &mdash; exactly
        </Stat>
        <Stat value={money(H.foundation_aid_increment)} tone={FORMULA}>
          produced by the formula&rsquo;s own aid term in the same year
        </Stat>
        <Stat value={money(Z.headroom)}>
          how far Lunenburg sits ABOVE the point at which the formula pays anything
        </Stat>
        <Stat value={`${d.on_floor.length} of the last ${d.fy_last - Math.min(...d.on_floor) + 1}`}>
          years in which Lunenburg&rsquo;s whole Chapter 70 increase is the flat per-pupil
          floor rather than anything the formula produced
        </Stat>
      </div>

      <H2 id="findings">What this page establishes</H2>
      <div className="grid gap-4 mt-6"
        style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 21rem), 1fr))' }}>
        <Insight n={1} headline={
          <>In {fy(H.fy)} the entire Chapter 70 increase was the Legislature&rsquo;s flat
            minimum. The formula produced nothing.</>}>
          Aid rose {signed(H.increase)}, from {money(H.prior_aid)} to {money(H.aid)}. All of
          it is the <em>minimum aid increment</em>, and it is {dollars2(H.per_pupil)} for
          each of the {H.enrollment.toLocaleString()} foundation pupils DESE ran the formula
          on &mdash; to the cent. The <em>foundation aid increment</em>, which is the
          formula&rsquo;s own term, is {money(H.foundation_aid_increment)}.
        </Insight>
        <Insight n={2} headline={
          <>It is zero because Lunenburg already receives {money(Z.headroom)} more than the
            formula says it needs.</>}>
          DESE&rsquo;s rule, in its own words: foundation aid is the foundation budget less
          the required contribution, paid only where that exceeds last year&rsquo;s aid. For{' '}
          {fy(Z.fy)} that is {money(Z.foundation_budget)} less{' '}
          {money(Z.required_local_contribution)} = {money(Z.need)}, against{' '}
          {money(Z.prior_aid)} already being paid. The rule reproduces DESE&rsquo;s own
          printed increment in {Z.rule_holds_in} of {Z.rule_of} years.
        </Insight>
        <Insight n={3} headline={
          <>The floor is a statewide rate, not a Lunenburg number &mdash; and it moves every
            year.</>}>
          {atRate.length === latestFloor.districts
            ? <>Every one of the {latestFloor.districts} districts in this comparison lands</>
            : <>{atRate.length} of the {latestFloor.districts} districts in this comparison
              land</>} on {dollars2(latestFloor.shared_rate ?? 0)} a pupil in{' '}
          {fy(latestFloor.fy)}, to the cent. Across the four years Lunenburg has been on it, the rate has been{' '}
          {d.on_floor.map(f => dollars2(d.floor.find(x => x.fy === f)!.shared_rate ?? 0))
            .join(', ')}. It was not available at all before {fy(Math.min(...d.on_floor))}.
        </Insight>
        <Insight n={4} headline={
          <>What the town is required to contribute is a wealth calculation. The number of
            children is not in it.</>}>
          DESE&rsquo;s target local contribution equals the <em>combined effort yield</em> &mdash;
          property effort plus income effort &mdash; in all {d.years} years published.
          Lunenburg&rsquo;s equalized valuation rose {share(W.eqv_growth)} between{' '}
          {fy(W.fy_from)} and {fy(W.fy_to)}, against a median of {share(W.eqv_median)} across{' '}
          {W.municipalities} municipalities: rank {W.eqv_rank}, fastest first.
        </Insight>
        <Insight n={5} headline={
          <>The formula spent {R.above_years} years taking effort OFF the town&rsquo;s
            bill. Since {fy(R.increment_first ?? R.below_first)} it has been adding it
            ON.</>}>
          Through {fy(R.above_last)} Lunenburg was contributing more than its target and the
          formula reduced it &mdash; {money(R.effort_reduction_total)} summed across those{' '}
          {R.reduction_years} years. It has been SHORT of target since {fy(R.below_first)},
          which is not the same date: for {R.quiet_years} years the formula added nothing,
          and the <em>dollar increment</em> starts in {fy(R.increment_first ?? R.below_first)}{' '}
          &mdash; {money(R.dollar_increment_total)} across {R.increment_years} years. The
          required share of the foundation budget fell from {share(SH.first)} in{' '}
          {fy(SH.first_fy)} to {share(SH.low)} in {fy(SH.low_fy)} and is {share(SH.last)} now.
        </Insight>
        <Insight n={6} headline={
          <>Since {fy(N.from_fy)} what the town is required to put in has risen{' '}
            {(N.required_pct / N.aid_pct).toFixed(1)} times as fast as the aid it gets, on
            a smaller number of children.</>}>
          Required local contribution {money(N.required_from)} to {money(N.required_to)},{' '}
          {share(N.required_pct)}. Chapter 70 aid {money(N.aid_from)} to {money(N.aid_to)},{' '}
          {share(N.aid_pct)}. Foundation enrolment{' '}
          {N.enrollment_from.toLocaleString()} to {N.enrollment_to.toLocaleString()}.{' '}
          {N.stage}
        </Insight>
        <Insight n={7} headline={
          <>Whether one more child changes the town&rsquo;s bill is NOT established here.</>}>
          The aid side has an answer while the floor binds. The contribution side does not
          respond to enrolment at all, except through how the town&rsquo;s single
          requirement is split between its two districts. The two cannot simply be added,
          because a large enough foundation budget increase closes the {money(Z.headroom)} of
          headroom and moves the district off the floor entirely &mdash; and no document in
          this archive models that. <a className="underline"
            style={{ color: 'var(--series-cost)' }} href="#marginal">The working is below.</a>
        </Insight>
      </div>

      <div className="card p-4 mt-8 max-w-3xl" style={{ borderLeft: '4px solid var(--axis)' }}>
        <p className="text-[11px] font-semibold uppercase tracking-widest mb-1.5"
          style={{ color: 'var(--text-muted)' }}>What this page is not</p>
        <p className="text-[14px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
          {d.not_this_page}{' '}
          <a className="underline" style={{ color: 'var(--series-cost)' }}
            href={abs('/state-aid')}>State aid</a> is that page. This one is Chapter 70 and
          only Chapter 70 &mdash; and the distinction is here rather than in a footnote
          because this project once folded the two together and published a share eight
          points too high for months.
        </p>
      </div>

      {/* ---------------------------------------------------------- 2. THE BREAKDOWN */}
      <H2 id="per-pupil">Every year&rsquo;s increase, for each foundation pupil</H2>
      <PerPupil rows={d.series} onFloor={d.on_floor} />
      <TableTwin
        caption={`DESE’s published Chapter 70 calculation, FY${String(d.fy_first + 1).slice(2)}–FY${String(d.fy_last).slice(2)}`}
        head={['Year', 'Chapter 70 aid', 'Change', 'Per pupil', 'Foundation aid',
               'Minimum aid', 'Other increments', 'On the floor']}
        rows={d.series.filter(s => s.change !== null).map(s => [
          fy(s.fy), money(s.aid), signed(s.change ?? 0), dollars2(s.per_pupil ?? 0),
          money(s.foundation_aid), money(s.minimum_aid), money(s.other_increments),
          d.on_floor.includes(s.fy) ? 'yes' : 'no',
        ])}
        note={<>&ldquo;On the floor&rdquo; means the year&rsquo;s whole per-pupil increase is
          the identical figure at least one other district in this comparison received.{' '}
          {soa ? <>The exception since minimum aid appeared is {fy(soa.fy)}, at{' '}
            {dollars2(soa.per_pupil ?? 0)} a pupil.</> : null}</>} />

      <NotShown>
        <p>
          <strong>A per-pupil figure is a division, and the denominator is contested.</strong>{' '}
          Foundation enrolment is a count of the students a district is financially
          responsible for as of 1 October of the previous year. DESE publishes three other
          counts for the same district and they do not agree &mdash; that is a registered
          gap, not an aside. Every figure in this table divides by the first of the four.
        </p>
        <p className="mt-2.5">
          <strong>And it does not show what any child costs.</strong> The rate is a floor the
          Legislature sets on the year&rsquo;s <em>increase</em>. It has no relationship to
          what educating a child in Lunenburg costs, which DESE separately puts at{' '}
          {money(H.foundation_per_pupil)} a pupil in {fy(H.fy)} &mdash; about{' '}
          {Math.round(H.times)} times the amount by which aid actually moved.
        </p>
      </NotShown>

      <H2 id="terms">The two terms, in dollars</H2>
      <AidTerms rows={d.series} />
      <TableTwin caption="The aid build-up, and whether the printed components account for the year"
        head={['Year', 'Change in aid', 'Components as printed', 'Difference']}
        rows={d.series.filter(s => s.change !== null).map(s => [
          fy(s.fy), signed(s.change ?? 0), signed(s.components_sum ?? 0),
          s.reconciles ? '—' : signed((s.change ?? 0) - (s.components_sum ?? 0)),
        ])}
        note={<>The components sum to the change in {d.reconciles_in} of{' '}
          {d.reconciles_of} differenced years. The {d.unreconciled.length} that do not are{' '}
          {d.unreconciled.map(u => fy(u.fy)).join(', ')} &mdash; and the workbook prints no
          residual line, so the difference has no name in the source. That is registered
          below rather than smoothed over.</>} />

      <H2 id="peers">The same year, at every district around us</H2>
      <Body>
        All {latestFloor.districts} districts in this comparison received exactly{' '}
        {dollars2(latestFloor.shared_rate ?? 0)} for each of their foundation pupils in{' '}
        {fy(latestFloor.fy)}. That is what makes it a rate rather than a Lunenburg outcome.
      </Body>
      <TableTwin caption={`Chapter 70 increase per foundation pupil, FY${String(latestFloor.fy).slice(2)}`}
        head={['District', 'Whole increase, per pupil', 'Of which minimum aid, per pupil']}
        rows={latestFloor.rows.map(r => [
          r.district, dollars2(r.per_pupil), dollars2(r.min_per_pupil),
        ])}
        note={<>Where the two columns differ, the formula produced some aid of its own and
          minimum aid topped it up to the floor &mdash; which is DESE&rsquo;s definition
          working exactly as written. Where they are equal, the formula produced nothing.
          These are the districts this project&rsquo;s copy of the workbook holds row by
          row; the statewide distribution in the next section is every district in the
          Commonwealth.</>} />

      <H2 id="required">What the town is required to contribute, against every other district</H2>
      <RequiredShare rows={d.distribution} />
      <TableTwin caption="Required local contribution as a share of the foundation budget"
        head={['Year', 'Lunenburg', 'Statewide median', 'Middle half', 'Rank']}
        rows={d.distribution.map(r => [
          fy(r.fy), share(r.lunenburg), share(r.median),
          `${share(r.p25)}–${share(r.p75)}`, r.lunenburg_rank_of_districts,
        ])}
        note={<>Ranked highest share first, out of {distLast.districts} districts in{' '}
          {fy(distLast.fy)}. In {fy(d.distribution[0].fy)} Lunenburg was asked for a{' '}
          <em>higher</em> share than the median district; it is now asked for a lower one.
          The statewide maximum is {share(distLast.p_max)} in {fy(distLast.fy)}, which is the
          statutory cap on the target local share showing up in the data.</>} />

      <H3>Why it fell and then climbed</H3>
      <Adjustment rows={d.contribution} />
      <TableTwin caption="The town’s required contribution, built the way DESE builds it"
        head={['Year', 'Combined effort yield (the target)', 'Preliminary', 'Effort reduction',
               'Dollar increment', 'Required contribution', 'Target as % of foundation']}
        rows={d.contribution.map(c => [
          fy(c.fy), money(c.combined_effort_yield), money(c.preliminary),
          c.effort_reduction ? `−${money(c.effort_reduction)}` : '—',
          c.dollar_increment ? `+${money(c.dollar_increment)}` : '—',
          money(c.rlc), c.target_share === null ? '—' : share(c.target_share),
        ])}
        note={<>The preliminary contribution is last year&rsquo;s requirement multiplied by
          the municipal revenue growth factor, and the requirement is that figure adjusted
          toward the target. That identity reproduces in {d.contribution_build_holds} of{' '}
          {d.contribution_build_of} years; the exception is{' '}
          {d.contribution_build_anomaly.map(a => fy(a.fy)).join(', ')}, where the two columns
          appear to hold each other&rsquo;s quantity &mdash; registered below.</>} />

      <Body>
        Three things moved at once and all three are in the table. <strong>The town got
        wealthier as the state measures wealth</strong> &mdash; equalized valuation up{' '}
        {share(W.eqv_growth)} between {fy(W.fy_from)} and {fy(W.fy_to)}, faster than the
        median municipality&rsquo;s {share(W.eqv_median)}, and the combined effort yield with
        it, up {share(W.cey_growth)} against a median of {share(W.cey_median)}.{' '}
        <strong>That pushed the target above the contribution the town was actually
        making</strong>, in {fy(R.below_first)}: a shortfall of{' '}
        {money(contribFirstBelow.shortfall)} where the year before there had been excess
        effort. <strong>And the formula began adding a dollar increment</strong> rather than
        closing the gap at once &mdash; not immediately, but from{' '}
        {fy(R.increment_first ?? R.below_first)}, {money(R.dollar_increment_total)} across{' '}
        {R.increment_years} years, against a shortfall that is{' '}
        {money(contribLast.shortfall)} in {fy(d.fy_last)}.
      </Body>
      <NotShown>
        <p>
          <strong>Wealth here is the state&rsquo;s measurement, not a description of
          residents.</strong> Equalized valuation is a Department of Revenue statistic that
          adjusts assessed values to sale prices; income is aggregate income from state tax
          returns and excludes non-filers. A town whose property values rise contributes more
          under this formula whether or not any household has more money, and nothing here
          tests whether it does.
        </p>
        <p className="mt-2.5">
          <strong>And the share is a ratio of two published figures, not a verdict.</strong>{' '}
          A required share can fall because the town got relatively poorer, or because the
          foundation budget grew &mdash; the Student Opportunity Act raised foundation budgets
          across the state, which is the one year in this series where the climb reverses.
          Both readings fit the same line, and this page does not choose between them.
        </p>
      </NotShown>

      {/* --------------------------------------------------------- the marginal pupil */}
      <H2 id="marginal">What one more child would do &mdash; and why that is not settled</H2>
      <Body>
        <strong>What is established.</strong> Four identities, each of them exact arithmetic
        on figures DESE published, and each reproduced by the script behind this page.
      </Body>
      <div className="flex flex-col gap-3 mt-5 max-w-3xl">
        {[
          <>Aid moves at the Legislature&rsquo;s flat rate while the floor binds.{' '}
            {fy(H.fy)}: {money(H.increase)} across {H.enrollment.toLocaleString()} pupils
            is {dollars2(H.per_pupil)}, to the cent.</>,
          <>The town&rsquo;s target contribution is its combined effort yield, in all{' '}
            {d.years} years. Enrolment does not appear in it.</>,
          <>The statutory cap that WOULD bring enrolment in &mdash; the target local share
            may not exceed 82.5% of the foundation budget &mdash; is not binding here.
            Lunenburg&rsquo;s target share is{' '}
            {share(contribLast.target_share ?? 0)} in {fy(d.fy_last)}.</>,
          <>The town&rsquo;s single requirement is split between its districts in proportion
            to their foundation budgets, to under two dollars in{' '}
            {d.allocation_summary.holds_in} of {d.allocation_summary.of} years. In{' '}
            {fy(alloc.fy)}, {money(alloc.town_rlc)} times{' '}
            {money(alloc.district_foundation_budget)} over {money(alloc.town_foundation_budget)}{' '}
            gives {money(alloc.predicted)} against a printed {money(alloc.district_rlc)}. The
            remaining {money(alloc.elsewhere_rlc)} is the town&rsquo;s contribution toward its
            other district. The exception is{' '}
            {d.allocation_summary.exceptions.map(f => fy(f)).join(', ')}, where the printed
            figure is {money(d.allocation_summary.worst)} off the proportion &mdash; the
            first year of the series, and nothing here says why.</>,
        ].map((t, i) => (
          <div key={i} className="card p-4">
            <p className="text-[14px] leading-relaxed"
              style={{ color: 'var(--text-secondary)' }}>{t}</p>
          </div>
        ))}
      </div>

      <H3>The arithmetic that follows, with every assumption named</H3>
      <div className="card p-5 mt-4 max-w-3xl"
        style={{ borderLeft: '4px solid var(--status-warning)' }}>
        <p className="text-[11px] font-semibold uppercase tracking-widest mb-2"
          style={{ color: 'var(--text-muted)' }}>
          Our arithmetic, not DESE&rsquo;s &mdash; and not a measurement
        </p>
        <p className="text-[14.5px] leading-relaxed">
          Add one pupil at the average foundation amount of {money(M.foundation_per_pupil)}{' '}
          and re-run the two identities above. The town&rsquo;s requirement does not move at
          all. The district&rsquo;s allocated share of it rises by{' '}
          {money(M.rlc_change)} &mdash; the town&rsquo;s money shifting between its two
          districts, not new money. So what the formula says the district needs from the
          state rises by {money(M.need_change)}, and it would take about{' '}
          <strong>{Math.round(M.pupils_to_close)} more pupils</strong> to consume the{' '}
          {money(M.headroom)} of headroom and put Lunenburg back on the formula&rsquo;s own
          aid track.
        </p>
        <p className="text-[13px] font-semibold uppercase tracking-widest mt-4 mb-1.5"
          style={{ color: 'var(--text-muted)' }}>It assumes all of this</p>
        <ul className="text-[13.5px] leading-relaxed list-disc pl-5"
          style={{ color: 'var(--text-secondary)' }}>
          {M.assumptions.map(a => <li key={a} className="mt-1.5">{a}</li>)}
        </ul>
      </div>
      <NotShown>
        <p>
          <strong>&ldquo;One more student brings the town {dollars2(H.per_pupil)}&rdquo;
          does not follow, and it is the sentence this section exists to stop.</strong>{' '}
          Three separate reasons. The floor is a rate on the year&rsquo;s <em>increase</em>,
          set annually, and it has been{' '}
          {d.on_floor.map(f => dollars2(d.floor.find(x => x.fy === f)!.shared_rate ?? 0))
            .join(', ')} in the {d.on_floor.length} years it applied &mdash; there is no
          standing {dollars2(H.per_pupil)}. The
          arithmetic above is a linear step off one year&rsquo;s figures, and the quantity it
          steps is a floor that stops applying once the formula produces more than it. And
          the average foundation amount is not the marginal one: DESE builds the foundation
          budget from per-pupil rates that differ by grade and by category, so which child
          arrives changes the answer and the rates are not in this workbook.
        </p>
        <p className="mt-2.5">
          Nor does it show anything about the town&rsquo;s bill in the sense a taxpayer
          means. A required contribution is a floor on what the town must spend, not a
          description of what it does spend: DESE reports Lunenburg&rsquo;s net school
          spending above the requirement in {SP.above_required} of {SP.years} years from{' '}
          {fy(SP.first_fy)}, never below {share(SP.lowest)} of it. Those {SP.stages.length}{' '}
          stages are not one series &mdash; the last two years are{' '}
          <em>{SP.latest_stage}</em> net school spending rather than spent, in a column the
          workbook heads <code>actualNSS</code> regardless.
        </p>
      </NotShown>

      {/* ---------------------------------------------------------- 3. RAW AND CONTEXT */}
      <H2 id="said">What the town has said about it</H2>
      <Body>
        Every quote is re-read out of the meeting archive on each build and the build stops
        if one is no longer in the document it is attributed to. Two of them are the same
        year at a different stage from anything in the tables above, and that is why they
        are here.
      </Body>
      <div className="grid gap-4 mt-6"
        style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 22rem), 1fr))' }}>
        {d.said.map(q => <Quote key={q.key} q={q} />)}
      </div>

      <div className="card p-5 mt-6 max-w-3xl"
        style={{ borderLeft: '4px solid var(--series-cost)' }}>
        <p className="text-[11px] font-semibold uppercase tracking-widest mb-2"
          style={{ color: 'var(--text-muted)' }}>A figure stated in public, recomputed</p>
        <p className="text-[15px] leading-relaxed">
          The {C.board} was told on {C.date} that municipalities fund{' '}
          <strong>{share(C.stated_municipal)}</strong> of the foundation budget and the
          Commonwealth <strong>{share(C.stated_state)}</strong>. For Lunenburg, in the
          fiscal year that meeting was about, DESE&rsquo;s own figures give{' '}
          <strong>{share(C.recomputed)}</strong> required of the town. It is close, and it
          is not a constant: the same ratio was {share(SH.first)} in {fy(SH.first_fy)} and{' '}
          {share(SH.last)} in {fy(SH.last_fy)}.
        </p>
        <p className="text-[13.5px] leading-relaxed mt-2.5"
          style={{ color: 'var(--text-secondary)' }}>
          {C.scope} What it shows is that the number people carry around is a snapshot of a
          series that moves.
        </p>
      </div>

      <H3>What was searched, and how much of the archive could be</H3>
      <TableTwin caption="The meeting archive, by term"
        head={['Term', 'Documents that match']}
        rows={d.searched.map(s => [s.term, s.documents.toLocaleString()])}
        note={<><strong>{d.minutes.searchable.toLocaleString()} of{' '}
          {d.minutes.held.toLocaleString()} held documents can be searched at all{' '}
          ({share(d.minutes.searchable_share)}).</strong>{' '}
          {d.minutes.unsearchable.toLocaleString()} carry no text a search can match &mdash;{' '}
          {d.minutes.image_scan.toLocaleString()} of them image scans awaiting OCR. So a
          term with few matches is a statement about the readable archive and never about
          what anybody said.</>} />

      <H2 id="definitions">DESE&rsquo;s own definitions, by cell</H2>
      <Body>
        The rules the arithmetic on this page reproduces, quoted from the{' '}
        <code>User Guide</code> sheet of the same workbook rather than paraphrased. A
        rendered table is for reading and never for quoting.
      </Body>
      <TableTwin caption={`${d.source.filename}, sheet User Guide`}
        head={['Cell', 'Term', 'What DESE says it is']}
        rows={d.definitions.map(x => [x.cell, x.term, x.text])} />

      <H2 id="cells">The FY{String(d.fy_last).slice(2)} row, by coordinate</H2>
      <TableTwin caption={`${d.source.filename}, sheets ${d.source.sheets.slice(0, 2).join(' and ')}`}
        head={['What DESE calls it', 'Cell', 'Value']}
        rows={[
          ['Foundation enrolment', H.cells.enrollment, H.enrollment.toLocaleString()],
          ['Foundation budget', H.cells.foundation_budget, money(H.foundation_budget)],
          ['Required local contribution (district)', H.cells.required_local_contribution,
            money(Z.required_local_contribution)],
          ['Target aid share', H.cells.target_aid_pct, `${H.target_aid_pct.toFixed(1)}%`],
          ['Foundation aid increment', H.cells.foundation_aid_increment,
            money(H.foundation_aid_increment)],
          ['Minimum aid increment', H.cells.minimum_aid_increment,
            money(H.minimum_aid_increment)],
          ['Chapter 70 aid', H.cells.ch70_aid, money(H.aid)],
          ['Equalized valuation (town)', H.cells.town_equalized_valuation,
            money(contribLast.equalized_valuation)],
          ['Aggregate income (town)', H.cells.town_income, money(contribLast.income)],
          ['Combined effort yield (town)', H.cells.town_combined_effort_yield,
            money(contribLast.combined_effort_yield)],
          ['Target local contribution (town)', H.cells.town_target_contribution,
            money(contribLast.target)],
          ['Preliminary contribution (town)', H.cells.town_preliminary_contribution,
            money(contribLast.preliminary)],
          ['Shortfall from target (town)', H.cells.town_shortfall,
            money(contribLast.shortfall)],
          ['Dollar increment (town)', H.cells.town_dollar_increment,
            money(contribLast.dollar_increment)],
          ['Required local contribution (town)', H.cells.town_required_local_contribution,
            money(contribLast.rlc)],
        ]}
        note={<>Two grains, and they must not be read across. A <em>district</em> row is
          Lunenburg Public Schools; a <em>municipality</em> row is the town of Lunenburg,
          whose foundation budget and required contribution also cover its residents at the
          regional vocational district. The difference in {fy(d.fy_last)} is{' '}
          {money(alloc.elsewhere_foundation)} of foundation budget and{' '}
          {money(alloc.elsewhere_rlc)} of required contribution.</>} />

      <H2 id="stage">Which stage every figure on this page is</H2>
      <Body>
        <Basis level="cross-checked">DESE&rsquo;s workbook against the town&rsquo;s own
          ledger</Basis>
      </Body>
      <Body>
        A Chapter 70 figure for one year exists at several stages &mdash; the Governor&rsquo;s
        budget, the House, the Senate, the conference committee, the act as passed, and then
        the receipt. They are different numbers for the same year, and rule 1 of this project
        exists because differencing across them measures partly growth and partly the step
        between the stages.
      </Body>
      <Body>
        <strong>Every series above is one stage: {d.source.stage}</strong> Nothing here is
        subtracted from a Governor&rsquo;s-budget figure or from a receipt. The two
        Governor&rsquo;s-stage figures on this page are quotations, and they are in the
        table below beside the figures DESE later ran &mdash; printed together because the
        size of the gap is the point, and never differenced.
      </Body>
      <TableTwin caption="One year, two stages — read across, never subtracted"
        head={['Fiscal year', 'What the town was told, per pupil', 'When, and by whom',
               'What DESE ran, per pupil']}
        rows={d.stage_examples.map(x => [
          fy(x.fy), dollars2(x.said), `${x.board}, ${x.said_on}`, dollars2(x.enacted),
        ])}
        note={<>The practical consequence, for anybody setting a budget: the figure the
          town is quoted while it is building its own budget is an early-stage figure, and
          in both years here it was lower than the one that was eventually run &mdash; by a
          factor of {(d.stage_examples[0].enacted / d.stage_examples[0].said).toFixed(1)} in{' '}
          {fy(d.stage_examples[0].fy)} and {(d.stage_examples[1].enacted
            / d.stage_examples[1].said).toFixed(1)} in {fy(d.stage_examples[1].fy)}. That is
          two years and not a pattern, and it has moved the other way in other years and
          other places. Each row is two documents about one year, not a measurement of
          anything.
          Subtracting the columns would give a figure that is partly the Legislature
          changing its mind and partly the stage &mdash; which is rule 1 of this project in
          its plainest form.</>} />
      <Body>
        Chapter 70 as the town actually <em>received</em> it, year by year, and the estimate
        it was budgeted against, are on{' '}
        <a className="underline" style={{ color: 'var(--series-cost)' }}
          href={abs('/state-aid')}>state aid</a>. That is a different stage and a different
        question.
      </Body>

      <H2 id="cannot">What this cannot say</H2>
      <div className="flex flex-col gap-3 mt-6 max-w-3xl">
        {d.not_established.map(n => (
          <div key={n} className="card p-4">
            <p className="text-[14px] leading-relaxed"
              style={{ color: 'var(--text-secondary)' }}>{n}</p>
          </div>
        ))}
      </div>

      <H3>The same limits, as rows in the register</H3>
      <Body>
        Each of these is a row in <code>money-gaps.csv</code>, which is what the records
        request to the Town reads and what{' '}
        <a className="underline" style={{ color: 'var(--series-cost)' }}
          href={abs('/what-we-cannot-answer')}>what we cannot answer</a> renders. A limit
        stated only in the prose of one page is invisible to everybody who did not read that
        page.
      </Body>
      <div className="flex flex-col gap-3 mt-5 max-w-3xl">
        {d.gaps.map(g => (
          <div key={g.what} className="card p-4">
            <p className="text-[11px] font-semibold uppercase tracking-widest mb-1.5"
              style={{ color: 'var(--text-muted)' }}>{g.side.replace(/_/g, ' ')}</p>
            <p className="text-[15px] font-bold leading-snug">{g.what}</p>
            <p className="text-[13.5px] leading-relaxed mt-2"
              style={{ color: 'var(--text-secondary)' }}>{g.why}</p>
            {g.closes && (
              <p className="text-[13.5px] leading-relaxed mt-2">
                <strong>Closes:</strong> {g.closes}
              </p>
            )}
          </div>
        ))}
      </div>

      <H2 id="source">The document behind this</H2>
      <Body>
        {d.source.publisher}. Our copy is{' '}
        <a className="underline break-all" style={{ color: 'var(--series-cost)' }}
          href={abs(d.source.docs_url)}>{d.source.filename}</a>{' '}
        ({(d.source.bytes / 1e6).toFixed(1)} MB), fetched from{' '}
        <a className="underline break-all" style={{ color: 'var(--series-cost)' }}
          href={d.source.url}>{d.source.url}</a>. Its sha256 is{' '}
        <code className="break-all">{d.source.sha256}</code>. The sheets read are{' '}
        {d.source.sheets.map((s, i) => (
          <span key={s}>{i ? ', ' : ''}<code>{s}</code></span>
        ))} &mdash; the front <code>Summary</code> sheet is a lookup interface and reads as
        formula text, so the data is taken from the sheets behind it.
      </Body>
      <Body>
        The payload this page draws is published whole at{' '}
        <a className="underline" style={{ color: 'var(--series-cost)' }}
          href={abs('/data/minimum-aid.json')}>/data/minimum-aid.json</a>, and the rows
        behind it &mdash; <code>dese_ch70_aid_factor</code>,{' '}
        <code>dese_ch70_contribution</code> and <code>dese_ch70_statewide</code> &mdash; can
        be queried directly from{' '}
        <a className="underline" style={{ color: 'var(--series-cost)' }}
          href={abs('/database')}>the database</a>.
      </Body>

      <Legend items={[
        { hue: FORMULA, label: 'the formula’s own aid term' },
        { hue: FLOOR, label: 'the Legislature’s flat per-pupil floor' },
      ]} />
    </div>
  )
}
