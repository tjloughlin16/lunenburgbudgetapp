import type { Tab } from '../routes'
import { useEffect, useMemo, useState } from 'react'
import { abs } from '../lib/abs'
import { usd } from '../model/engine'
import { TableTwin, fy, share } from '../components/StateAidCharts'
import {
  AidHistory, Asymmetry, BothWays, ChoiceIn, Dial, Flows, LOSS, PerGrade, SAVE, Sensitivity,
  type AidYear, type BothWaysYear, type FlowYear, type FundYear, type Grade,
} from '../components/LeavingCharts'
import {
  Conclusions,
  Body, H2, H3, Insight, Maybe, NotShown, Stat,
  ReportShell,
} from '../components/report'
import type { Conclusion } from '../components/report'

/** The frame this report is drawn in. See components/report.tsx.
 *  TITLE is the report's NAME, used before the payload arrives; the h1 the
 *  reader lands on is the finding, which needs the data to state. */
const TAB: Tab = 'leaving'
const DATA = '/data/if-students-leave.json'
const TITLE = 'If students leave'

/** If students leave — what school choice would cost Lunenburg.
 *
 *  WHY THIS PAGE EXISTS. A member of the Select Board put a scenario to an AI assistant and
 *  sent it to this site: a 40% school choice transfer rate among athletes, who are 45% of
 *  the high school, and what that does to Chapter 70 and to school choice money. It was
 *  sound reasoning on the documents that are easy to find. This page runs the same scenario
 *  against the whole archive and lets the reader move every input.
 *
 *  RULE 8. Not an audit of anybody's arithmetic. The scenario's premise checks out on two
 *  independent tests and the page says so first, before it says anything else. The two
 *  places the fuller data lands differently are presented as what they are — things the
 *  published documents show that a public search would not surface.
 *
 *  SHAPE (rule 7b). Conclusions, then the model and the organised data, then the raw and
 *  the caveats. A reader who stops after the first screen carries away the asymmetry, which
 *  is the finding that survives every setting of every dial.
 *
 *  RULE 3 IS THE DIFFICULTY HERE, not rule 1. Almost nothing on this page is a
 *  measurement of a transfer, because nobody has measured one. So every input is badged
 *  `measured`, `statute` or `assumed`, the assumed ones are dials, and the page never
 *  presents a net figure without the range around it.
 *
 *  RULE 2. Not one figure is typed into this file. The measured ones arrive from
 *  /data/if-students-leave.json; the scenario ones are computed here from those.
 *
 *  NO D1 AT PAGE LOAD. One static file. */

type Basis = [string, string]

type Prov = {
  key: string; file: string; sheet: string; dataset: string | null; title: string
  path: string; sha256: string; rows: number
}

type Payload = {
  conclusions: Conclusion[]
  generated_by: string
  source: string
  enrollment: {
    fy: number; page: string; document: string
    headings: string[]; headings_raw: string
    status: string; status_means: string; checks: string[]
    hs_resident: number; hs_choice_in: number; hs_total: number
    district_resident: number; district_choice_in: number; district_total: number
    grades: { grade: string; resident: number; choice_in: number; total: number }[]
    schools: { school: string; resident: number; choice_in: number; total: number }[]
    choice_in_outside_hs: number
  }
  premise: {
    fy: number; hs_participations: number
    seasons: { season: string; participations: number }[]
    biggest_season: string; biggest_season_participations: number
    implied_athletes: number; implied_athletes_exact: number; per_athlete: number
    biggest_season_share: number; participation_share: number
    verdict: string; verdict_note: string
  }
  formula: {
    source: string; sheet: string; row: number; fy: number; as_of: string | null
    cells: Record<string, string>; headings: Record<string, string>
    enrollment: number; foundation: number; required: number; aid: number; nss: number
    gap: number; above_gap: number; above_gap_share_of_aid: number
    foundation_per_pupil: number; aid_per_pupil: number
    operating_districts: number; districts_above_gap: number
    districts_above_gap_share: number
    appropriation: number; appropriation_per_pupil: number
    appropriation_denominator: string
  }
  formula_history: {
    sources: Prov[]
    series: AidYear[]; span: [number, number]
    latest: AidYear & { foundation: number; required: number }
    town_ledger_ch70: number; fy27_aid: number
    enrollment_fell_years: { fy: number; pupils: number; aid_change: number
      aid_fell: boolean }[]
    enrollment_fell: number; aid_fell_too: number; aid_fell_in: number[]
    aid_fell_with_reduction: number[]; aid_fell_unexplained: number[]
    components_from: number
    recent_from: number
    recent_fell: { fy: number; pupils: number; aid_change: number; aid_fell: boolean }[]
    components: {
      fy: number; enrollment: number; aid: number; foundaidinc: number
      downpymtaidinc: number; growthaidinc: number; targaidphaseinaid: number
      minaidinc: number; increments: number
    }[]
    identity_ties: { fy: number; residual: number }[]
    identity_breaks: { fy: number; residual: number }[]
    latest_components: {
      fy: number; enrollment: number; aid: number; minaidinc: number; increments: number
      foundaidinc: number
    }
    min_aid_per_pupil: number; min_aid_total: number; foundation_aid_inc: number
    latest_named: [string, number][]
  }
  key_factors: {
    file: string; sheet: string; row: number; title: string | null
    enrollment: number; el: number; el_share: number; voc: number; voc_share: number
    lowinc: number; lowinc_share: number; lowinc_group: number | string
    labor_market: string; wage_factor: number
    foundation: number; foundation_per_pupil: number
  }
  flows: {
    sources: Prov[]
    years: number[]; latest_sy: number
    series: FlowYear[]
    latest: FlowYear & { resident_total: number; attending_lunenburg: number }
    destinations: { district: string; reason: string; students: number }[]
    origins: { town: string; reason: string; students: number }[]
    member_elsewhere: { district: string; students: number }[]
    peak: FlowYear; low: FlowYear; mean_out: number
    first: FlowYear; last: FlowYear; reasons_seen: string[]
    both_ways: {
      series: BothWaysYear[]
      years: number[]
      first: BothWaysYear; last: BothWaysYear
      out_first: number; out_last: number; out_change: number; out_change_pct: number
      out_max: number; out_min: number
      in_first: number; in_last: number; in_change: number; in_change_pct: number
      in_max: number; in_min: number
      net_first: number; net_last: number
      net_worst: number; net_worst_sy: number; net_best: number; net_best_sy: number
      years_net_positive: number; net_positive_years: number[]
      in_latest: { reason: string; students: number }[]
      definitions: { out: string; inn: string; net: string }
      money: {
        overlap: number[]; first_fy: number; last_fy: number
        receipts_first: number; receipts_last: number; receipts_pct: number
        in_first: number; in_last: number; in_pct: number
        per_student_established: boolean; per_student_why: string
      }
    }
  }
  choice_in: {
    fund_series: (FundYear & {
      edition: string; page: string; fund: string; status: string
      forward: number | null; disbursements: number | null; derived: string | null
    })[]
    usable_years: number[]; status: string[]; status_means: string
    arithmetic_checks: number; chain_checks: number
    first: FundYear; last: FundYear; peak: FundYear
    receipts_change: number; receipts_pct: number
    cherry_sheet: { fy: number; amount: number }[]
    cherry_line: number; cherry_source: string
    implied_from_cherry: { fy: number; amount: number; students: number }[]
  }
  scenario: {
    defaults: {
      athlete_share: number; transfer_rate: number; tuition: number
      aid_per_pupil: number; avoidable_share: number
    }
    basis: Record<string, Basis>
    aid_per_pupil: number; aid_per_pupil_max: number; aid_ratio: number | null
    baseline_sy: number; baseline_out: number; baseline_in: number; baseline_net: number
    after_out: number; after_multiple: number | null
    hs_resident: number; athletes: number; leavers: number
    per_grade: Grade[]; biggest_grade_loss: number
    foundation_per_pupil: number; appropriation_per_pupil: number
    foundation_reduction: number; tuition_out: number
    aid_loss: number; aid_loss_upper: number; aid_loss_ratio: number | null
    max_avoidable: number; avoided: number
    net_cost: number; net_cost_upper: number
    break_even_avoidable_share: number; break_even_upper: number
    fee: { fy: number; amount: number; school_year: string | null; source: string | null }
    participations_lost: number; fees_lost: number | null
  }
  said: { key: string; board: string; date: string; who: string; quote: string; why: string
    cite: string; town: string }[]
  gaps: { side: string; what: string; why: string; closes: string | null }[]
  related: { id: string; title: string; why: string; words: number; updated: string
    url: string; pdf: string | null }[]
}

function Said({ q }: { q: Payload['said'][number] }) {
  return (
    <div className="card p-4">
      <p className="text-[11px] font-semibold uppercase tracking-widest mb-2"
        style={{ color: 'var(--text-muted)' }}>{q.board} &middot; {q.date}</p>
      <blockquote className="text-[15px] leading-relaxed italic">
        &ldquo;{q.quote}&rdquo;
      </blockquote>
      <p className="text-[12px] mt-1.5" style={{ color: 'var(--text-muted)' }}>{q.who}</p>
      <p className="text-[13.5px] leading-relaxed mt-2.5"
        style={{ color: 'var(--text-secondary)' }}>{q.why}</p>
      <p className="text-[12px] mt-2.5">
        <a className="underline" style={{ color: 'var(--series-cost)' }} href={abs(q.cite)}>
          the minutes, as text
        </a>
        {' · '}
        <a className="underline" style={{ color: 'var(--series-cost)' }} href={abs(q.town)}>
          the town&rsquo;s own copy
        </a>
      </p>
    </div>
  )
}

const pctLabel = (x: number) => `${(x * 100).toFixed(0)}%`

export function IfStudentsLeave() {
  const [d, setD] = useState<Payload | null>(null)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    let live = true
    fetch('/data/if-students-leave.json')
      .then(r => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then(j => { if (live) setD(j) })
      .catch(e => { if (live) setErr(String(e)) })
    return () => { live = false }
  }, [])

  if (err) return <ReportShell tab={TAB} title={TITLE} dataUrl={DATA} err={err} />

  if (!d) return <ReportShell tab={TAB} title={TITLE} dataUrl={DATA} loading />
  return <Page d={d} />
}

function Page({ d }: { d: Payload }) {
  const E = d.enrollment
  const P = d.premise
  const F = d.formula
  const H = d.formula_history
  const K = d.key_factors
  const W = d.flows
  const B = d.flows.both_ways
  const C = d.choice_in
  const S = d.scenario
  const D = S.defaults

  const [athleteShare, setAthleteShare] = useState(D.athlete_share)
  const [transferRate, setTransferRate] = useState(D.transfer_rate)
  const [tuition, setTuition] = useState(D.tuition)
  const [aidPerPupil, setAidPerPupil] = useState(D.aid_per_pupil)
  const [avoidable, setAvoidable] = useState(D.avoidable_share)

  /** The scenario, recomputed. The same arithmetic the generator runs at the defaults —
   *  which is why the generator runs it at all: a reader who moves nothing must see the
   *  scenario exactly as it was put to this site, and the page must not be the only place
   *  that knows how to compute it. */
  const m = useMemo(() => {
    const athletes = Math.round(athleteShare * E.hs_resident)
    const leavers = Math.round(transferRate * athletes)
    const foundationReduction = leavers * F.foundation_per_pupil
    const tuitionOut = leavers * tuition
    const aidLoss = leavers * aidPerPupil
    const maxAvoidable = leavers * F.appropriation_per_pupil
    const avoided = avoidable * maxAvoidable
    const grades: Grade[] = E.grades.map(g => {
      const n = leavers * g.resident / E.hs_resident
      return {
        grade: g.grade, resident: g.resident, leaving: n,
        remaining: g.resident - n,
        share: g.resident ? n / g.resident : 0,
      }
    })
    const curve = Array.from({ length: 21 }, (_, i) => {
      const a = i / 20
      return {
        avoidable: a,
        hold: tuitionOut + aidLoss - a * maxAvoidable,
        full: tuitionOut + foundationReduction - a * maxAvoidable,
      }
    })
    const breakEven = maxAvoidable > 0 ? (tuitionOut + aidLoss) / maxAvoidable : null
    return {
      athletes, leavers, foundationReduction, tuitionOut, aidLoss, maxAvoidable, avoided,
      grades, curve, breakEven,
      net: tuitionOut + aidLoss - avoided,
      participationsLost: leavers * P.per_athlete,
      feesLost: leavers * P.per_athlete * S.fee.amount,
      perGradeMax: grades.length ? Math.max(...grades.map(g => g.leaving)) : 0,
      afterOut: W.latest.out_choice + leavers,
      afterMultiple: W.latest.out_choice ? (W.latest.out_choice + leavers) / W.latest.out_choice : null,
      netAfter: W.latest.out_choice + leavers - W.latest.in_choice,
    }
  }, [athleteShare, transferRate, tuition, aidPerPupil, avoidable, E, F, P, S, W])

  const moved = athleteShare !== D.athlete_share || transferRate !== D.transfer_rate
    || tuition !== D.tuition || aidPerPupil !== D.aid_per_pupil
    || avoidable !== D.avoidable_share

  const resetAll = () => {
    setAthleteShare(D.athlete_share); setTransferRate(D.transfer_rate)
    setTuition(D.tuition); setAidPerPupil(D.aid_per_pupil)
    setAvoidable(D.avoidable_share)
  }

  const fund = C.fund_series

  return (
    <ReportShell tab={TAB} dataUrl={DATA}
      title={<>
        The money leaves in one year. The cost does not.
      </>}
      standfirst={<>
        {B.out_last} Lunenburg children are already enrolled somewhere other than
        Lunenburg and {B.in_last} children from other towns are enrolled here &mdash; a net
        loss in every one of the {B.series.length} years the state publishes. A scenario
        put to this site adds {S.leavers} more leaving in a single year. The measured
        record first, then the dials.
      </>}
    >

      <div className="mt-10 flex flex-wrap gap-x-12 gap-y-6">
        <Stat value={String(m.leavers)} tone={LOSS}>
          students leaving, at the settings currently on this page &mdash; on top of the{' '}
          {W.latest.out_choice} DESE counts already leaving in SY{String(W.latest_sy).slice(2)}
        </Stat>
        <Stat value={usd(m.tuitionOut + m.aidLoss)} tone={LOSS}>
          leaves the town in the first year: sending tuition, plus whatever Chapter 70 does
        </Stat>
        <Stat value={usd(H.min_aid_per_pupil)} tone={SAVE}>
          is what Chapter 70 currently moves for one foundation pupil, against a foundation
          budget of {usd(F.foundation_per_pupil)} each &mdash; DESE&rsquo;s own aid
          components, FY{String(H.latest_components.fy).slice(2)}
        </Stat>
        <Stat value={usd(m.avoided)} tone={SAVE}>
          stops being spent &mdash; which is a decision somebody has to take, not a
          consequence of the students going
        </Stat>
        <Stat value={m.perGradeMax.toFixed(0)}>
          students from the largest grade &mdash; the loss spread over four grades, which
          is why nothing closes on its own
        </Stat>
      </div>

      {/* ------------------------------------------------------------ 1. THE CONCLUSIONS */}
      {/* ------------------------------------------------ 1. CONCLUSIONS (rule 7b) */}
      {/* NOT WRITTEN HERE. Every word and every figure comes out of this report's own
          payload, computed by the generator that computed the figures -- see
          scripts/conclusions.py. The same rows appear on /what-it-all-adds-up-to, read
          from the same file, so the two cannot drift apart. */}
      <H2 id="conclusions">If you read nothing else</H2>
      <Conclusions rows={d.conclusions} />

      <H2 id="findings">What this page establishes</H2>
      <Body>
        Six claims. The first two are about the scenario as it was put; the rest are what
        the town&rsquo;s and the state&rsquo;s own documents show once you have all of them.
      </Body>

      <div className="grid gap-4 mt-6"
        style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 20rem), 1fr))' }}>
        <Insight n={1} headline={
          <>The scenario&rsquo;s premise holds. {share(D.athlete_share)} of the high school
            playing sports is, if anything, low.</>
        }>
          Two independent tests, neither of which is a headcount. At {share(D.athlete_share)}{' '}
          of {E.hs_resident} the scenario implies {P.implied_athletes} athletes playing{' '}
          {P.per_athlete} sports each &mdash; an ordinary number. And the district&rsquo;s
          largest single season in {fy(P.fy)}, {P.biggest_season}, records{' '}
          {P.biggest_season_participations.toFixed(0)} high school participations on its
          own, which is {share(P.biggest_season_share)} of the student body in one season.
        </Insight>
        <Insight n={2} headline={
          <>Revenue goes at once and in full. Cost goes only where somebody decides it
            goes.</>
        }>
          {m.leavers} students spread across four grades is {m.perGradeMax.toFixed(0)} out
          of the largest one. No section closes, no building is heated less and no contract
          ends because of that, so the town keeps very nearly all of the cost while the
          tuition assessment and any aid change land immediately. This is the finding that
          holds at every setting of every dial on this page.
        </Insight>
        <Insight n={3} headline={
          <>This is not a new flow. At the settings on this page it is{' '}
            {m.afterMultiple?.toFixed(2)}&times; an existing one, arriving in a single
            year.</>
        }>
          DESE counts {W.latest.out_choice} Lunenburg residents leaving under school choice
          in SY{String(W.latest_sy).slice(2)} and {W.latest.in_choice} arriving &mdash; a
          net {W.latest.net_choice} out. It has run between {W.low.out_choice} and{' '}
          {W.peak.out_choice} every year since SY{String(W.years[0]).slice(2)}. The scenario
          would take the outward flow to {m.afterOut}. That is the useful way to read it:
          not whether school choice happens, but how fast.
        </Insight>
        <Insight n={4} headline={
          <>Chapter 70 currently moves {usd(H.min_aid_per_pupil)} for a foundation pupil,
            not {usd(F.foundation_per_pupil)}. The two differ by a factor of{' '}
            {S.aid_ratio}.</>
        }>
          DESE&rsquo;s own aid-component columns make this year&rsquo;s aid last
          year&rsquo;s aid plus named increments &mdash; an identity that holds to the
          dollar in the last {H.identity_ties.filter(t => t.fy >= H.latest_components.fy - 6).length}{' '}
          of seven years. In FY{String(H.latest_components.fy).slice(2)} the whole of
          Lunenburg&rsquo;s {usd(H.latest_components.increments)} increase is the minimum
          aid increment, and the foundation aid increment is{' '}
          {usd(H.foundation_aid_inc)}. {usd(H.min_aid_total)} over{' '}
          {H.latest_components.enrollment.toLocaleString()} foundation pupils is{' '}
          {usd(H.min_aid_per_pupil)} each.
        </Insight>
        <Insight n={5} headline={
          <>Over {H.span[1] - H.span[0]} years, foundation enrollment fell in{' '}
            {H.enrollment_fell} of them and Chapter 70 aid fell in {H.aid_fell_too}.</>
        }>
          FY{H.span[0]} to FY{H.span[1]}, from DESE&rsquo;s Chapter 70 district profile.
          The {H.aid_fell_too} years aid fell are{' '}
          {H.aid_fell_in.map(y => `FY${String(y).slice(2)}`).join(', ')}.{' '}
          {H.aid_fell_with_reduction.length > 0 && <>
            DESE&rsquo;s component columns carry a reduction in{' '}
            {H.aid_fell_with_reduction.map(y => `FY${String(y).slice(2)}`).join(' and ')}.
          </>}{' '}
          {H.aid_fell_unexplained.length > 0 && <>
            {H.aid_fell_unexplained.map(y => `FY${String(y).slice(2)}`).join(' and ')}{' '}
            predates those columns, which start at FY{String(H.components_from).slice(2)},
            so nothing here says why aid fell that year.
          </>}{' '}
          This measures what happened. It does not establish what would happen.
        </Insight>
        <Insight n={6} headline={
          <>Even if aid barely moves, the town has to stop spending{' '}
            {share(S.break_even_avoidable_share)} of a student&rsquo;s appropriation just to
            break even.</>
        }>
          At {usd(F.appropriation_per_pupil)} per pupil, {m.leavers} students carry{' '}
          {usd(m.maxAvoidable)} of appropriation with them at most. Sending tuition alone
          is {usd(m.tuitionOut)}, and it is assessed whatever Chapter 70 does. If aid fell
          by the whole foundation reduction the break-even would be{' '}
          {share(S.break_even_upper)} of per-pupil spending, which is more than exists to
          cut.
        </Insight>
      </div>

      <NotShown>
        <p>
          <strong>This is a scenario and not a forecast.</strong> Nothing here is evidence
          that {S.leavers} more children will leave, or that athletes are the ones who
          would. The children who leave are counted; nobody counts why, and nobody counts
          whether they play sports.
        </p>
        <p className="mt-2.5">
          <strong>The counts carry no money.</strong> DESE publishes how many children go
          where. Not one document in this archive states the tuition that follows any of
          them, in either direction, so every dollar figure on this page rests on an
          assumed rate.
        </p>
        <p className="mt-2.5">
          It also does not show that {share(D.athlete_share)} of the high school are
          athletes. A participation is not a child &mdash; {fy(P.fy)}&rsquo;s{' '}
          {P.hs_participations.toFixed(0)} high school participations are{' '}
          {share(P.participation_share)} of the entire student body, which is the proof
          that column is counting something other than people.
        </p>
      </NotShown>

      {/* -------------------------------------------- 1a. THE RECORD, BOTH DIRECTIONS, ALL OF IT */}
      {/* MEASURED. Everything in this section is DESE's count of children and none of it
          moves when a dial moves. It is deliberately placed before the scenario and
          rendered without a single control, because a scenario's numbers are ours and a
          measurement's are the state's, and printing them alike is how an estimate turns
          into a fact (rule 3). The scenario picks up below and is labelled where it does. */}
      <H2 id="record">The record: every child who leaves, and every child who arrives</H2>
      <Body>
        Not school choice alone &mdash; every programme, both ways, every year the state
        publishes. This is measured. Nothing in this section responds to the dials.
      </Body>

      <div className="mt-8 flex flex-wrap gap-x-12 gap-y-6">
        <Stat value={String(B.out_last)} tone={LOSS}>
          Lunenburg children were enrolled somewhere other than Lunenburg in{' '}
          SY{String(B.last.sy).slice(2)} &mdash; school choice, charter schools and the
          vocational district together
        </Stat>
        <Stat value={String(B.in_last)} tone={SAVE}>
          children from other towns were enrolled in Lunenburg in the same year, down from{' '}
          {B.in_first} in SY{String(B.first.sy).slice(2)}
        </Stat>
        <Stat value={String(B.net_last)}>
          net &mdash; arriving minus leaving. It has been between {B.net_worst} and{' '}
          {B.net_best} in every one of the {B.series.length} years published
        </Stat>
        <Stat value={String(B.years_net_positive)}>
          years of net gain in {B.series.length}. The town has never once taken in more
          children than it sent out
        </Stat>
      </div>

      <BothWays series={B.series} />

      <TableTwin
        caption={`Both directions, all programmes — DESE, SY${String(B.first.sy).slice(2)} to SY${String(B.last.sy).slice(2)}`}
        head={['School year', 'Leaving — all', 'Arriving — all', 'Net',
               'of which: vocational member', 'school choice out', 'charter out',
               'school choice in']}
        rows={B.series.map(r => [`SY${String(r.sy).slice(2)}`, r.out_all, r.in_all,
                                 r.net_all, r.out_member, r.out_choice, r.out_charter,
                                 r.in_choice])}
        note={<>
          <strong>Leaving</strong> is {B.definitions.out}. <strong>Arriving</strong> is{' '}
          {B.definitions.inn}. <strong>Net</strong> is {B.definitions.net}. Counted by the
          state in two separate files, one per direction; each year&rsquo;s two halves are
          added back to DESE&rsquo;s own row count for that year before this page will
          build.
        </>} />

      <H3>The net is flat. One of its two halves is not</H3>
      <Body>
        Leaving has barely moved: {B.out_first} in SY{String(B.first.sy).slice(2)},{' '}
        {B.out_last} in SY{String(B.last.sy).slice(2)}, never outside{' '}
        {B.out_min}&ndash;{B.out_max} in between. Arriving has fallen from {B.in_first} to{' '}
        {B.in_last}, a fall of {share(-B.in_change_pct)}, and it is the only one of the
        two totals that has moved at all. A chart of the net alone would be a
        near-straight line drawn across the whole of that movement, which is why all three
        series are on the axis above.
      </Body>
      <Body>
        What moved inside the outward count is composition rather than size. Children at
        charter schools fell from {B.first.out_charter} to {B.last.out_charter} and
        children attending the vocational district as members of it rose from{' '}
        {B.first.out_member} to {B.last.out_member}. That second route is not a school
        choice transfer and never has been: Lunenburg is a member town, so the state
        splits one required contribution rather than charging a tuition. Families apply,
        compete in a lottery and may not get a place &mdash; what differs is how the bill
        behaves, not whether a decision was made.
      </Body>

      <TableTwin
        caption={`Arriving in SY${String(B.last.sy).slice(2)}, by the mechanism that brought each child`}
        head={['Mechanism', 'Children']}
        rows={B.in_latest.map(r => [r.reason, r.students])}
        note={<>Three different mechanisms, and they do not carry money the same way.
          Only the first is school choice.</>} />

      <Maybe settle={<>The School Committee&rsquo;s annual school choice vote &mdash; seats
        opened, by grade, for every year since SY{String(B.first.sy).slice(2)}. The minutes
        hold it in pieces; nobody has compiled it as a series.</>}>
        <p>
          A receiving district decides every year how many school choice seats to open, and
          at which grades. So {B.in_last} arrivals against {B.in_first} is equally
          consistent with <strong>fewer seats being offered</strong> and with{' '}
          <strong>fewer families applying</strong>, and the two imply opposite remedies.
          The published record states both counts for a single year &mdash; the
          Superintendent&rsquo;s figures to the Finance Committee, quoted further down
          &mdash; and in that year the seats were opened and the applications did not
          arrive. One year cannot speak for the other {B.series.length - 1}.
        </p>
      </Maybe>

      <H3>What the arriving half is worth, and why this page does not say</H3>
      <Body>
        An arriving school choice student brings tuition into the district, so a fall in
        arrivals is money as well as children. Two measured series describe it and{' '}
        <strong>neither is divided into the other</strong>: over the {B.money.overlap.length}{' '}
        years the two files share, DESE&rsquo;s count of arrivals went from{' '}
        {B.money.in_first} to {B.money.in_last} ({share(-B.money.in_pct)} down), and the
        town&rsquo;s own School Choice fund receipts went from{' '}
        {usd(B.money.receipts_first)} in {fy(B.money.first_fy)} to{' '}
        {usd(B.money.receipts_last)} in {fy(B.money.last_fy)} ({share(-B.money.receipts_pct)}{' '}
        down).
      </Body>
      <NotShown>
        <p>
          <strong>What one arriving child is worth.</strong> {B.money.per_student_why}
        </p>
        <p className="mt-2.5">
          So the money value of a {share(-B.in_change_pct)} fall in arrivals is not
          established here, and dividing the receipts above by the count above would not
          establish it either. Two reasons, and both are on this page:{' '}
          {B.last.in_all - B.last.in_choice} of SY{String(B.last.sy).slice(2)}&rsquo;s{' '}
          {B.last.in_all} arrivals came by a mechanism that is not school choice, so they
          are in the count and cannot be in the tuition; and the statutory rate is higher
          for special education, which nothing published here counts among arriving
          children. An average across both would be a number, not a rate.
        </p>
        <p className="mt-2.5">
          <strong>And it would not reduce the appropriation one-for-one if it were known.</strong>{' '}
          Tuition received is revenue into a fund; a budget line is what the town has to
          raise after everything else that pays for the thing has been subtracted. Money
          arriving and an appropriation falling are two different events.
        </p>
      </NotShown>
      <p className="text-[13.5px] mt-4">
        <a className="underline font-semibold" style={{ color: 'var(--series-cost)' }}
          href={abs('/where-students-go-instead')}>
          The outward half, decomposed &mdash; who receives these children, and by which route
        </a>
      </p>

      {/* ------------------------------------------------------------- 1b. THE BASELINE */}
      <H2 id="baseline">Within that record, school choice &mdash; and where the scenario would put it</H2>
      <Body>
        The same thirteen years, narrowed to the one programme the scenario is about. The
        two solid lines are DESE&rsquo;s count; <strong>the dashed rule is the scenario</strong>,
        and it is the only thing on this chart that moves when you move a dial.
      </Body>
      <Flows series={W.series} scenarioOut={m.afterOut}
        scenarioLabel={`the scenario: ${m.afterOut} leaving`} />
      <TableTwin
        caption="Lunenburg residents, by where they go — DESE, school years"
        head={['School year', 'Leaving under school choice', 'At charter schools',
               'Arriving under school choice', 'Net school choice']}
        rows={W.series.map(r => [`SY${String(r.sy).slice(2)}`, r.out_choice, r.out_charter,
                                 r.in_choice, r.net_choice])}
        note={<>Counted by the state, not by us. The outward flow peaked at{' '}
          {W.peak.out_choice} in SY{String(W.peak.sy).slice(2)} and has averaged{' '}
          {W.mean_out} over the {W.years.length} years published.</>} />

      <H3>Where they go, and where the arrivals come from</H3>
      <div className="grid gap-6 mt-5"
        style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 20rem), 1fr))' }}>
        <div>
          <TableTwin
            caption={`Leaving, SY${String(W.latest_sy).slice(2)}`}
            head={['District', 'Programme', 'Children']}
            rows={W.destinations.map(x => [x.district, x.reason, x.students])} />
        </div>
        <div>
          <TableTwin
            caption={`Arriving, SY${String(W.latest_sy).slice(2)}`}
            head={['Town of residence', 'Programme', 'Children']}
            rows={W.origins.map(x => [x.town, x.reason, x.students])} />
        </div>
      </div>
      <NotShown>
        <p>
          <strong>Families choose Monty Tech. The bill is what behaves differently.</strong>{' '}
          {W.member_elsewhere.map((x, i) => (
            <span key={x.district}>{i ? ', ' : ''}{x.students} Lunenburg children attend{' '}
              {x.district}</span>
          ))} &mdash; the largest single destination outside Lunenburg. They applied, and a
          place is not guaranteed. What is different is not whether a decision was made but
          how the money moves: Lunenburg is a <em>member town</em>, so the state computes
          one required local contribution for the town and splits it between its two
          districts by foundation-budget share, rather than charging a tuition per child.
          That is a different rule from school choice, which is why these children are
          counted separately here and not added to a school choice total.
        </p>
        <p className="mt-2.5">
          These are counts of children and they carry <strong>no money at all</strong>. The
          tuition that follows each of them is set differently for school choice and for
          charters, is higher for special education, and appears in no document this
          archive holds.
        </p>
      </NotShown>

      {/* ------------------------------------------------------------------- 2. THE MODEL */}
      <H2 id="model">The model &mdash; move anything you disagree with</H2>
      <Body>
        The dials open on the scenario as it was put to this site. Every one of them is an
        assumption; the badge on each says what kind, and the measured figures they run
        against are further down with the cell each came out of.
      </Body>

      {moved && (
        <p className="text-[12.5px] mt-3">
          <button onClick={resetAll} className="underline font-semibold"
            style={{ color: 'var(--series-cost)' }}>
            reset every dial to the scenario as it was put
          </button>
        </p>
      )}

      <div className="grid gap-4 mt-6"
        style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 15rem), 1fr))' }}>
        <Dial label="Share of the high school who are athletes"
          value={athleteShare} setValue={setAthleteShare} min={0} max={1} step={0.01}
          format={pctLabel} tone={LOSS} reset={D.athlete_share}
          basis={S.basis.athlete_share[0]} note={S.basis.athlete_share[1]} />
        <Dial label="Share of those athletes who transfer out"
          value={transferRate} setValue={setTransferRate} min={0} max={1} step={0.01}
          format={pctLabel} tone={LOSS} reset={D.transfer_rate}
          basis={S.basis.transfer_rate[0]} note={S.basis.transfer_rate[1]} />
        <Dial label="School choice tuition, per student"
          value={tuition} setValue={setTuition} min={0} max={25000} step={250}
          format={usd} tone={LOSS} reset={D.tuition}
          basis={S.basis.tuition[0]} note={S.basis.tuition[1]} />
        <Dial label="Chapter 70 aid lost per student"
          value={aidPerPupil} setValue={setAidPerPupil} min={0}
          max={Math.round(S.aid_per_pupil_max)} step={10}
          format={usd} tone={LOSS} reset={D.aid_per_pupil}
          basis={S.basis.aid_per_pupil[0]} note={S.basis.aid_per_pupil[1]} />
        <Dial label="Share of a student’s appropriation the district stops spending"
          value={avoidable} setValue={setAvoidable} min={0} max={1} step={0.01}
          format={pctLabel} tone={SAVE} reset={D.avoidable_share}
          basis={S.basis.avoidable_share[0]} note={S.basis.avoidable_share[1]} />
      </div>

      <H3>What it costs the town, at these settings</H3>
      <Asymmetry items={[
        {
          label: <>School choice tuition the town is assessed for {m.leavers} students</>,
          amount: m.tuitionOut, hue: LOSS,
          note: <>{m.leavers} &times; {usd(tuition)}. Assessed rather than appropriated:
            it sits inside the Cherry Sheet assessments the FY2027 Town Meeting booklet
            takes off the top, and no document in this archive breaks it out.</>,
        },
        {
          label: <>Chapter 70 aid, at {usd(aidPerPupil)} a student</>,
          amount: m.aidLoss, hue: LOSS,
          note: <>The foundation budget would fall {usd(m.foundationReduction)} &mdash;{' '}
            {m.leavers} &times; {usd(F.foundation_per_pupil)} per pupil, cell{' '}
            <code>{F.cells.foundation}</code> over <code>{F.cells.enrollment}</code> &mdash;
            but the aid attached to a foundation pupil at the margin is currently{' '}
            {usd(H.min_aid_per_pupil)}, because the minimum aid increment is the only thing
            adding to Lunenburg&rsquo;s aid in FY{String(H.latest_components.fy).slice(2)}.
            The dial spans both readings.</>,
        },
        {
          label: <>Spending the district stops, at {share(avoidable)} of per-pupil
            appropriation</>,
          amount: m.avoided, hue: SAVE,
          note: <>Up to {usd(m.maxAvoidable)} at {usd(F.appropriation_per_pupil)} a pupil.
            {' '}{F.appropriation_denominator}</>,
        },
        {
          label: <><strong>Net cost to the town, per year</strong></>,
          amount: m.net, hue: m.net > 0 ? LOSS : SAVE,
          note: <>The first two, less the third. It repeats every year those students stay
            away, and it compounds if they are followed.</>,
        },
      ]} />

      <H3>The whole range, not one number</H3>
      <Body>
        The single input the answer is most sensitive to is the one nothing measures: how
        much a district stops spending when students go. Both curves below are drawn across
        every value of it &mdash; the lower at the aid figure currently on the dial, the
        upper at the reading the scenario was originally built on.
      </Body>
      <Sensitivity curve={m.curve} breakEven={m.breakEven} />
      <TableTwin
        caption="Net cost to the town, by how much spending the district avoids"
        head={['Spending avoided', `At ${usd(aidPerPupil)} of aid per student`,
               'If aid fell by the whole foundation reduction']}
        rows={m.curve.filter((_, i) => i % 4 === 0).map(r => [
          share(r.avoidable), usd(r.hold), usd(r.full)])}
        note={<>Break-even at the current aid setting is{' '}
          {m.breakEven != null && m.breakEven <= 1
            ? <>{share(m.breakEven)} of a student&rsquo;s appropriation</>
            : <>beyond 100% of a student&rsquo;s appropriation &mdash; the town cannot get
              there by not spending</>}.</>} />

      <H3>Where the students would come from</H3>
      <Body>
        The scenario&rsquo;s students are spread across the four grades in proportion to how
        big each grade actually is, printed on the same page as the total. Grade{' '}
        {E.grades[0].grade} is the smallest, so it loses the fewest.
      </Body>
      <PerGrade grades={m.grades} />
      <TableTwin
        caption={`High school, FY${String(E.fy).slice(2)} annual town report, printed page ${E.page}`}
        head={['Grade', 'Lunenburg resident students', 'School choice students', 'Total',
               'Leaving, in this scenario', 'Left in the grade']}
        rows={E.grades.map((g, i) => [
          g.grade, g.resident, g.choice_in, g.total,
          m.grades[i].leaving.toFixed(1), m.grades[i].remaining.toFixed(1)])}
        note={<>The first three columns are the report&rsquo;s own, headed{' '}
          <code>{E.headings_raw}</code>. The last two are this scenario.</>} />

      <Maybe settle={<>the district&rsquo;s own staffing and section plan by grade &mdash;
        the document behind the School Committee&rsquo;s April 2025 discussion of each
        grade, its size and its potential seats &mdash; which would state the class sizes at
        which a section is added or removed.</>}>
        <p>
          At about {m.perGradeMax.toFixed(0)} students out of a grade, one class section per
          grade is the largest reduction the arithmetic alone could support, and it would
          need every one of those students to have been in the same courses. Whether any
          section could actually be removed depends on how they distribute across a
          timetable, and nothing published says.
        </p>
      </Maybe>

      {/* ------------------------------------------------ 3. THE ORGANISED, MEASURED DATA */}
      <H2 id="measured">What is measured, and where each figure comes from</H2>
      <Body>
        Four inputs above are assumptions. These are not &mdash; each is one row or one cell
        of one document, with the coordinate, and each is checked against something else
        before this page will build.
      </Body>

      <H3>The children: the FY{String(E.fy).slice(2)} annual town report, printed page {E.page}</H3>
      <Body>
        The report prints its own column headings, which matters: in the database this table
        is stored as <code>v1</code>, <code>v2</code>, <code>v3</code> with no column
        meaning, and <code>v1</code> means only <em>the first figure column of this page</em>.
        The page itself calls it <code>{E.headings[1]}</code>.
      </Body>
      <TableTwin
        head={['', ...E.headings.slice(1)]}
        rows={[...E.schools.map(s => [s.school, s.resident, s.choice_in, s.total]),
               ['All Schools Total', E.district_resident, E.district_choice_in,
                E.district_total]]}
        note={<>Extract status <code>{E.status}</code>. {E.status_means} What is established
          instead is the table&rsquo;s own arithmetic, asserted by the generator before this
          page will build: {E.checks.join('; ')}.</>} />
      <Body>
        Every one of the {E.district_choice_in} school choice students the town counted is
        in the high school &mdash; {E.choice_in_outside_hs} anywhere else. Lunenburg is a
        net receiver at exactly the grades this scenario is about.
      </Body>

      <H3>The athletes: the district&rsquo;s athletics workbook, FY{String(P.fy).slice(2)}</H3>
      <TableTwin
        head={['Season', 'High school participations', 'As a share of the high school']}
        rows={[...P.seasons.map(s => [s.season, s.participations.toFixed(0),
                                      share(s.participations / E.hs_resident)]),
               ['All three seasons', P.hs_participations.toFixed(0),
                share(P.participation_share)]]}
        note={<>{P.verdict_note}</>} />
      <NotShown>
        A participation is not a child. One student playing three seasons is three of them,
        which is why the year&rsquo;s total exceeds the entire student body. Nothing
        published is an unduplicated count of Lunenburg athletes, and this page never
        multiplies one as though it were.
      </NotShown>

      <H3>
        The formula: DESE&rsquo;s FY{String(F.fy).slice(2)} Chapter 70 district summary,
        row {F.row}
      </H3>
      <TableTwin
        head={['Cell', 'As DESE heads the column', 'Lunenburg']}
        rows={[
          [F.cells.enrollment, F.headings.D6, F.enrollment.toLocaleString()],
          [F.cells.foundation, F.headings.E6, usd(F.foundation)],
          [F.cells.required, F.headings.F6, usd(F.required)],
          [F.cells.aid, F.headings.G6, usd(F.aid)],
          [F.cells.nss, F.headings.H6, usd(F.nss)],
        ]}
        note={<><code>{F.cells.required}</code> + <code>{F.cells.aid}</code> ={' '}
          <code>{F.cells.nss}</code> exactly, which is the identity the sheet states about
          itself and the generator asserts. Sheet <code>{F.sheet}</code> of{' '}
          <a className="underline" style={{ color: 'var(--series-cost)' }}
            href={abs('/docs/' + F.source.replace('sources/', ''))}>{F.source}</a>
          {F.as_of ? `, as of ${F.as_of}` : ''}. The same five figures are carried
          independently in <code>model/taxbase.py</code> and the two are compared before
          this page will build.</>} />

      <div className="card p-5 mt-6 max-w-3xl"
        style={{ borderLeft: `4px solid ${LOSS}` }}>
        <p className="text-[11px] font-semibold uppercase tracking-widest mb-2"
          style={{ color: 'var(--text-muted)' }}>The subtraction that is not doing the work</p>
        <p className="text-[15px] leading-relaxed">
          {usd(F.foundation)} &minus; {usd(F.required)} = <strong>{usd(F.gap)}</strong>.
          Chapter 70 aid is <strong>{usd(F.aid)}</strong> &mdash; {usd(F.above_gap)} more,
          or {share(F.above_gap_share_of_aid)} of the aid.{' '}
          {F.districts_above_gap} of the {F.operating_districts} operating districts on the
          same sheet ({share(F.districts_above_gap_share)}) are in the same position.
        </p>
        <p className="text-[14px] leading-relaxed mt-3" style={{ color: 'var(--text-secondary)' }}>
          So a model that removes foundation dollars per pupil and reduces aid by the same
          amount is assuming a relationship these numbers do not currently display. That is
          not a flaw in anybody&rsquo;s reasoning &mdash; it is a fact that only shows up if
          you have the district summary open at the right row.
        </p>
      </div>

      <Maybe settle={<>DESE&rsquo;s FY{String(F.fy).slice(2)} preliminary Chapter 70 aid
        calculation for Lunenburg &mdash; the per-district worksheet that states the
        foundation aid, minimum aid and hold-harmless components separately. This archive
        holds the summary, which publishes the result of the calculation and not the
        calculation.</>}>
        <p>
          Chapter 70 carries minimum aid and hold-harmless provisions, and they are the
          obvious reason aid would sit above the foundation gap. Nothing in this archive
          applies them to Lunenburg, and the sheet does not say which provision produced
          this row. What is established is the {usd(F.above_gap)}; the mechanism is a
          hypothesis, and so is any claim about what aid would do in a year enrollment fell.
        </p>
      </Maybe>

      <H3>
        What Chapter 70 has actually done &mdash; FY{H.span[0]} to FY{H.span[1]}
      </H3>
      <Body>
        DESE&rsquo;s Chapter 70 district profile carries {H.series.length} years of
        Lunenburg&rsquo;s foundation enrollment, foundation budget, required local
        contribution and aid. Its FY{String(H.latest.fy).slice(2)} aid figure is{' '}
        {usd(H.latest.aid)}, which is exactly what the town&rsquo;s own FY2026 revenue
        ledger budgets for Chapter 70 &mdash; two independent documents, and the generator
        refuses to publish this series if they ever stop agreeing.
      </Body>
      <AidHistory series={H.series} fellYears={H.enrollment_fell_years.map(f => f.fy)} />
      <TableTwin
        caption="Every year foundation enrollment was lower than the year before"
        head={['FY', 'Change in foundation pupils', 'Change in Chapter 70 aid',
               'Did aid fall?']}
        rows={H.enrollment_fell_years.map(f => [
          `FY${String(f.fy).slice(2)}`, f.pupils, usd(f.aid_change),
          f.aid_fell ? 'yes' : 'no'])}
        note={<>{H.enrollment_fell} of the {H.span[1] - H.span[0]} year-on-year steps in the
          series. Aid fell in {H.aid_fell_too} of them. <strong>This is a record, not a
          rule.</strong> A year in this table is a year enrollment happened to be lower, not
          a year anybody left in the way this page models, and the size of the fall is not
          held constant across them.</>} />

      <H3>And why: the aid calculation, in DESE&rsquo;s own components</H3>
      <Body>
        The trends workbook splits the calculation into named increments. The identity is
        that this year&rsquo;s aid is <em>last year&rsquo;s aid plus the increments</em>,
        and it holds to the dollar in{' '}
        {H.identity_ties.length} of the {H.identity_ties.length + H.identity_breaks.length}{' '}
        year-to-year steps published &mdash; the exceptions are{' '}
        {H.identity_breaks.map(b => `FY${String(b.fy).slice(2)}`).join(', ')}, and they are
        shown rather than smoothed.
      </Body>
      <TableTwin
        caption="Chapter 70 aid, and what added to it — DESE’s own column names"
        head={['FY', 'Foundation pupils', 'foundaidinc', 'downpymtaidinc', 'growthaidinc',
               'targaidphaseinaid', 'minaidinc', 'Chapter 70 aid']}
        rows={H.components.map(r => [
          `FY${String(r.fy).slice(2)}`, r.enrollment.toLocaleString(),
          usd(r.foundaidinc), usd(r.downpymtaidinc), usd(r.growthaidinc),
          usd(r.targaidphaseinaid), usd(r.minaidinc), usd(r.aid)])}
        note={<>Sheet <code>dataAid</code> of DESE&rsquo;s Chapter 70 trends workbook. In
          FY{String(H.latest_components.fy).slice(2)} every dollar of the increase is{' '}
          <code>minaidinc</code>.</>} />

      <div className="card p-5 mt-6 max-w-3xl" style={{ borderLeft: `4px solid ${SAVE}` }}>
        <p className="text-[11px] font-semibold uppercase tracking-widest mb-2"
          style={{ color: 'var(--text-muted)' }}>
          What a foundation pupil is currently worth in aid
        </p>
        <p className="text-[15px] leading-relaxed">
          FY{String(H.latest_components.fy).slice(2)}:{' '}
          <code>minaidinc</code> {usd(H.min_aid_total)} over{' '}
          {H.latest_components.enrollment.toLocaleString()} foundation pupils ={' '}
          <strong>{usd(H.min_aid_per_pupil)} each</strong>. <code>foundaidinc</code> is{' '}
          {usd(H.foundation_aid_inc)}, so nothing about the foundation budget is adding to
          Lunenburg&rsquo;s aid this year.
        </p>
        <p className="text-[14px] leading-relaxed mt-3"
          style={{ color: 'var(--text-secondary)' }}>
          The division is ours. What DESE states is the {usd(H.min_aid_total)} and the{' '}
          {H.latest_components.enrollment.toLocaleString()}; that the minimum aid increment
          is paid per pupil is what makes dividing them meaningful, and the page says so
          rather than assuming a reader will infer it.
        </p>
      </div>

      <Maybe settle={<>DESE&rsquo;s preliminary Chapter 70 aid calculation for Lunenburg
        for the year in question, which states the foundation aid, minimum aid and
        hold-harmless components before the year is set.</>}>
        <p>
          The obvious reading is hold-harmless: aid does not fall below last year&rsquo;s,
          so the only thing enrollment moves is the minimum aid increment on top. That fits
          every number above and this archive does not test it. Two things would break the
          {' '}{usd(H.min_aid_per_pupil)}: the Legislature setting a different minimum aid
          rate, which it has done repeatedly, and an enrollment fall large enough to move
          Lunenburg onto a different track in the formula, which nothing here models.
        </p>
      </Maybe>

      <H3>Which children leave, not only how many</H3>
      <Body>
        DESE calculates the foundation budget from the composition of a district, not from
        a headcount alone. Its key-factors summary, row {K.row}, gives Lunenburg&rsquo;s
        FY{String(H.latest_components.fy).slice(2)} foundation enrollment as{' '}
        {K.enrollment.toLocaleString()} and splits it three ways.
      </Body>
      <TableTwin
        head={['Category', 'Children', 'Share of foundation enrollment']}
        rows={[
          ['English learners', K.el, share(K.el_share)],
          ['Low income (group ' + K.lowinc_group + ')', K.lowinc, share(K.lowinc_share)],
          ['Vocational', K.voc, share(K.voc_share)],
        ]}
        note={<>Wage adjustment factor {K.wage_factor.toFixed(3)},{' '}
          {K.labor_market}. Foundation budget {usd(K.foundation)}, or{' '}
          {usd(K.foundation_per_pupil)} a pupil &mdash; the FY
          {String(H.latest_components.fy).slice(2)} figure, which is not the FY
          {String(F.fy).slice(2)} figure the scenario above uses.</>} />
      <NotShown>
        The sheet is headed <em>{K.title}</em> and lists these categories as factors in the
        calculation, which is what establishes that they are inputs to it. It does not
        publish the rate attached to any of them. So this page can say that <strong>which
        children leave changes the foundation figure and not only how many</strong>, and it
        cannot say in which direction or by how much &mdash; which means it cannot say what
        a departing athlete is worth as against any other child. Registered below.
      </NotShown>

      <H3>School choice money, the way Lunenburg currently sees it &mdash; coming in</H3>
      <Body>
        The town has a School Choice revolving fund and its annual reports have printed it
        for thirteen years. It holds tuition for students who choose <em>into</em> Lunenburg
        &mdash; the opposite direction to this scenario, and the only direction anybody
        publishes.
      </Body>
      <ChoiceIn series={fund} cherry={C.cherry_sheet} />
      <TableTwin
        caption="The School Choice revolving fund, as the annual town reports print it"
        head={['FY', 'Balance forward', 'Receipts', 'Disbursements', 'Carried forward',
               'Printed page']}
        rows={fund.map(r => [
          fy(r.fy),
          r.forward != null ? usd(r.forward) : '—',
          r.receipts != null && r.usable ? usd(r.receipts) : '—',
          r.disbursements != null ? usd(r.disbursements) : '—',
          r.carried != null ? usd(r.carried) + (r.derived ? ' *' : '') : '—',
          r.page,
        ])}
        note={<>Status <code>{C.status.join('`, `')}</code>. {C.status_means} The generator
          checks {C.arithmetic_checks} rows against their own arithmetic and{' '}
          {C.chain_checks} year-to-year balances across separately published reports, and
          refuses to write if any fails. An asterisk marks a carried balance the row itself
          implies where the extract captured only three of the four printed columns.</>} />
      <Body>
        Receipts into the fund moved from {usd(C.first.receipts ?? 0)} in{' '}
        {fy(C.first.fy)} to {usd(C.last.receipts ?? 0)} in {fy(C.last.fy)} &mdash;{' '}
        {share(Math.abs(C.receipts_pct))} lower, having peaked at{' '}
        {usd(C.peak.receipts ?? 0)} in {fy(C.peak.fy)}. The cherry sheet&rsquo;s own{' '}
        <code>School Choice Receiving</code> line, on line {C.cherry_line} of the FY2027
        Town Meeting booklet, gives{' '}
        {C.cherry_sheet.map((r, i) => (
          <span key={r.fy}>{i ? ', ' : ''}{usd(r.amount)} for {fy(r.fy)}</span>
        ))}.
      </Body>
      <NotShown>
        <p>
          <strong>These two series are not the same quantity and are not differenced here.</strong>{' '}
          One is cash the town&rsquo;s fund received in a closed fiscal year; the other is
          the state&rsquo;s estimate for a year not yet closed. This archive holds no Cherry
          Sheet for any year, so the figure a Finance Committee member quoted in January
          2026 can be reported as said and cannot be checked against the document it names.
        </p>
        <p className="mt-2.5">
          Dividing the cherry sheet line by the assumed tuition gives{' '}
          {C.implied_from_cherry.map((r, i) => (
            <span key={r.fy}>{i ? ', ' : ''}{r.students} students in {fy(r.fy)}</span>
          ))} &mdash; against the {E.district_choice_in} the town counted in {fy(E.fy)}.
          That is two assumptions stacked and it is shown only because it lands near a
          count the town printed. It is not a headcount and must not be quoted as one.
        </p>
      </NotShown>

      {/* -------------------------------------------------------- 4. WHAT THE TOWN SAID */}
      <H2 id="said">What the town said about this, in its own meetings</H2>
      <Body>
        Found by searching the meeting archive &mdash; every board, 2025 onward. Each quote
        is checked against the file it is attributed to before this page will build.
      </Body>
      <div className="grid gap-4 mt-6"
        style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 21rem), 1fr))' }}>
        {d.said.map(q => <Said key={q.key + q.date} q={q} />)}
      </div>

      {/* -------------------------------------------------------------- 5. THE CAVEATS */}
      <H2 id="limits">What this page does not show</H2>

      <div className="grid gap-4 mt-6"
        style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 20rem), 1fr))' }}>
        {[
          ['It is a scenario, not a forecast.',
           'Nothing here predicts that any student will transfer. Every dial is an input '
           + 'somebody chose, and the page exists so a reader can choose differently.'],
          ['The children are counted. The money is not.',
           'DESE publishes how many Lunenburg residents attend every other district, in '
           + 'both directions, for thirteen school years. No document in this archive '
           + 'states the tuition that follows one of them.'],
          ['Nothing here says why any child left.',
           'Athletics, class offerings, a family moving town, a programme somewhere else — '
           + 'the count is the same number under all of them, and attaching a cause to it '
           + 'would be a hypothesis dressed as a measurement.'],
          ['Participations are not students.',
           'The 45% is tested against a participation count and bounded by it, not '
           + 'measured from it. No unduplicated athlete roster is published.'],
          ['The Chapter 70 figure is a marginal rate, not a model of the formula.',
           'DESE’s components show what added to aid in each year. They do not let anyone '
           + 'run the calculation forward, and the minimum aid rate is set annually by the '
           + 'Legislature — it has been as low as $30 a pupil in the years published.'],
          ['A budget line is net, and it is dollars.',
           'The per-pupil appropriation here is what the town raises after aid, divided by '
           + 'a count. It is not what educating a child costs, and grants, fees and '
           + 'revolving funds are in documents this one does not read.'],
          ['The tuition rate is statute, not a measurement of Lunenburg.',
           'It is higher for special education, and this archive holds no document stating '
           + 'either rate. Every dollar figure on this page moves with that dial.'],
        ].map(([h, b]) => (
          <div key={h} className="card p-4">
            <p className="text-[14px] font-bold leading-snug">{h}</p>
            <p className="text-[13.5px] leading-relaxed mt-2"
              style={{ color: 'var(--text-secondary)' }}>{b}</p>
          </div>
        ))}
      </div>

      <H3>And the same limits, in the register</H3>
      <Body>
        A limit written on one page is invisible to everyone who did not read that page. All
        of these are rows in the gap register, which is what{' '}
        <a className="underline" style={{ color: 'var(--series-cost)' }}
          href={abs('/what-we-cannot-answer')}>the gaps page</a>, the records request and{' '}
        <a className="underline" style={{ color: 'var(--series-cost)' }}
          href={abs('/api/money_gaps.json')}>the API</a> all read.
      </Body>
      <div className="grid gap-3 mt-5">
        {d.gaps.map(g => (
          <div key={g.what} className="pl-4" style={{ borderLeft: '3px solid var(--grid)' }}>
            <p className="text-[10.5px] font-semibold uppercase tracking-widest"
              style={{ color: 'var(--text-muted)' }}>{g.side.replace(/_/g, ' ')}</p>
            <p className="text-[14px] font-bold mt-0.5">{g.what}</p>
            <p className="text-[13px] leading-relaxed mt-1"
              style={{ color: 'var(--text-secondary)' }}>{g.why}</p>
            {g.closes && (
              <p className="text-[13px] leading-relaxed mt-1.5">
                <span className="font-semibold">Closes with:</span>{' '}
                <span style={{ color: 'var(--text-secondary)' }}>{g.closes}</span>
              </p>
            )}
          </div>
        ))}
      </div>

      {/* ----------------------------------------------------------------- 6. THE RAW */}
      <H2 id="raw">The data behind this page</H2>
      <Body>
        Everything above is computed from one static file, written by one script that
        refuses to write if any of eleven checks fails.
      </Body>
      <ul className="mt-4 text-[14px] leading-relaxed list-disc pl-5 max-w-2xl"
        style={{ color: 'var(--text-secondary)' }}>
        <li>
          <a className="underline" style={{ color: 'var(--series-cost)' }}
            href={abs('/data/if-students-leave.json')}>/data/if-students-leave.json</a>{' '}
          &mdash; every measured figure on this page, with its coordinate
        </li>
        <li>
          <a className="underline" style={{ color: 'var(--series-cost)' }}
            href={abs('/docs/' + F.source.replace('sources/', ''))}>{F.source}</a> &mdash;
          DESE&rsquo;s FY{String(F.fy).slice(2)} Chapter 70 district summary
        </li>
        <li>
          <a className="underline" style={{ color: 'var(--series-cost)' }}
            href={abs('/data/athletics.json')}>/data/athletics.json</a> &mdash; the
          participation counts and the fee schedule
        </li>
        <li>
          <a className="underline" style={{ color: 'var(--series-cost)' }}
            href={abs('/data/money_gaps.json')}>/data/money_gaps.json</a> &mdash; the gap
          register, in full
        </li>
        <li><code>{d.generated_by}</code> &mdash; the generator, and its refusals</li>
      </ul>
      <H3>The state&rsquo;s own files, by name and by hash</H3>
      <Body>
        Four DESE workbooks, located by filename rather than by folder &mdash; this archive
        re-files documents on purpose, and a script that names a folder is a break with a
        date on it. A spreadsheet can be replaced in place, so each is hashed.
      </Body>
      <TableTwin
        head={['File', 'Sheet', 'DESE dataset', 'Rows', 'sha256']}
        rows={[...H.sources, ...W.sources].map(x => [
          x.file, x.sheet, x.dataset ?? '—', x.rows.toLocaleString(),
          x.sha256.slice(0, 16) + '…'])}
        note={<>{[...H.sources, ...W.sources].map((x, i) => (
          <span key={x.file}>{i ? ' ' : ''}<strong>{x.file}</strong> &mdash; {x.title}.</span>
        ))}</>} />

      <H3>The athletics fund loses fees too, and that is a different pot</H3>
      <Body>
        At the {fy(S.fee.fy)} high school fee of {usd(S.fee.amount)},{' '}
        {m.leavers} athletes taking {P.per_athlete} sports each is{' '}
        {m.participationsLost.toFixed(0)} participations and {usd(m.feesLost)} that does not
        reach the athletics revolving fund. That is not the town&rsquo;s general fund and
        the two must not be added: the fund also stops incurring some of the cost of those
        athletes, and{' '}
        <a className="underline" style={{ color: 'var(--series-cost)' }}
          href={abs('/what-sports-cost')}>what a sport actually costs</a> is not
        established. The fee is from {S.fee.source}.
      </Body>

      <H2 id="related">Related analyses</H2>
      <div className="grid gap-3 mt-5">
        {d.related.map(r => (
          <a key={r.id} href={abs(r.url)}
            className="card block px-4 py-4 min-h-[44px] transition-opacity hover:opacity-90">
            <span className="flex items-baseline gap-2 flex-wrap">
              <span className="text-[15px] font-bold leading-tight"
                style={{ color: 'var(--series-cost)' }}>{r.title} &rarr;</span>
              <span className="text-[10.5px] font-semibold uppercase tracking-wider tnum"
                style={{ color: 'var(--text-muted)' }}>
                {r.words.toLocaleString()} words &middot; {r.updated}
              </span>
            </span>
            <span className="block text-[13.5px] mt-1.5 leading-snug"
              style={{ color: 'var(--text-secondary)' }}>{r.why}</span>
          </a>
        ))}
      </div>

      <p className="text-[12px] mt-12 max-w-2xl" style={{ color: 'var(--text-muted)' }}>
        Generated by <code>{d.generated_by}</code> from {d.source}
      </p>
    </ReportShell>
  )
}
