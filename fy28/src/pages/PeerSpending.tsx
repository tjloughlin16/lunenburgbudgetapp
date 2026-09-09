import type { Tab } from '../routes'
import { useEffect, useState } from 'react'
import { abs } from '../lib/abs'
import {
  CategoryGap, FIELD, FundSplit, Legend, MoneyAgainstPupils, OURS, OneYear, Span,
  Statewide, TableTwin, TeacherSplit, fy, money, pct1, shortName, signedPct, signedUsd,
  type CatRow, type DecompRow, type SwRow, type TeacherRow, type YearRow,
} from '../components/PeerSpendingCharts'
import {
  Body, H2, H3, Insight, NotShown, Quote, Stat,
  ReportShell,
} from '../components/report'

const TAB: Tab = 'peers'
const DATA = '/data/peer-spending.json'

/** What Lunenburg spends for each pupil, against every district in Massachusetts and
 *  against five neighbours.
 *
 *  RULE 11 IS THE FIRST CAVEAT AND IT IS BESIDE THE FIGURE, NOT ABOVE THE PAGE. DESE's
 *  measure is ALL FUNDS: grants, revolving funds, school choice, gifts, and town-paid
 *  insurance and retirement attributed to the schools. It is not the appropriation and it
 *  is not what a household pays. The stat row carries that line under the headline number
 *  rather than in a preamble, because a reader who has not yet seen $18,027 has nothing to
 *  attach the warning to.
 *
 *  RULE 1. Two collections at two stages appear on this page and are never differenced:
 *  DESE's end-of-year finance figures (FY2025, reported) and DESE's Chapter 70 profile
 *  (FY2026, budgeted). The standing section says which is which in its own first line, and
 *  the generator refuses to write if the net-school-spending measure stops carrying a
 *  stage at all.
 *
 *  RULE 7 GOVERNS EVERY SECTION. The arithmetic here is exact — a per-pupil figure
 *  decomposed into its numerator and denominator, a category gap that sums, a teacher
 *  identity that reproduces. Every explanation for any of it is a hypothesis and is
 *  labelled one. MCAS is printed because residents argue about it in both directions, and
 *  the section says in its own heading that nothing on the page tests a relation to
 *  spending.
 *
 *  RULE 8. Not a scorecard. Spending less than a neighbour is not a failure and spending
 *  more is not a success; no mark on this page means good or bad.
 *
 *  RULE 7b. Conclusions, then the organised categories, then the raw and the caveats.
 *  RULE 7a within each: the thing first, the note about how to read it after.
 *
 *  RULE 2. Not one figure is typed into this file. Everything arrives from
 *  /data/peer-spending.json, written by scripts/build_peer_spending.py.
 *
 *  THE PEER SET IS OURS AND THE PAGE SAYS SO WHERE IT MATTERS. Every headline rests on
 *  DESE's statewide distribution — 318 districts, with quartiles and a rank — precisely so
 *  that a set this project chose does not have to carry a claim. The six are texture.
 *
 *  NO D1 AT PAGE LOAD. One static file. */

type Said = {
  key: string; board: string; date: string; kind: string; quote: string; why: string
  who: string; cite: string; town: string
}

type Payload = {
  about: string
  not_this_page: string
  fin_fy: number; ch70_fy: number
  first_fy: number; last_fy: number; years: number; first_comparable_fy: number
  regionalisation: { ayer_last_fy: number; ayer_shirley_first_fy: number }
  documents: {
    key: string; what: string; publisher: string; stage: string; path: string
    sha256: string; bytes: number; url: string; docs_url: string; filename: string
  }[]
  denominators: {
    rows_tested: number; total_fte: number; in_district_fte: number; ambiguous: number
    tolerance: number; label_in_our_table: string; label_is_wrong_on: string
  }
  districts: {
    lea: string; district: string; first_fy: number; last_fy: number; years: number
    is_lunenburg: boolean; in_current_set: boolean
  }[]
  headline: {
    fy: number; per_pupil: number; total: number; gen_fund: number
    grants_revolving: number; grant_share: number; grant_share_is_lowest: boolean
    fte_total: number; fte_in_district: number; rank: number; of: number
    statewide_rank: number; statewide_of: number; statewide_spend_less: number
    statewide_median: number; statewide_below_median: number
    statewide_p25: number; statewide_p75: number
    bottom_quarter_years: number; bottom_quarter_of: number
    bottom_quarter_unbroken: boolean; best_rank: number; worst_rank: number
  }
  totals: YearRow[]
  last_year: YearRow[]
  statewide: SwRow[]
  statewide_categories: {
    code: string; desc: string; districts: number; median: number; lunenburg: number
    rank: number; spend_less: number; share_of_median: number | null
    in_bottom_quarter: boolean
  }[]
  decomposition: DecompRow[]
  lunenburg_denominator: {
    from_fy: number; to_fy: number; spend_from: number; spend_to: number
    spend_pct: number; pupils_from: number; pupils_to: number; pupils_pct: number
    per_pupil_from: number; per_pupil_to: number; per_pupil_change: number
    at_old_enrolment: number; denominator_share: number
  }
  categories: CatRow[]
  category_headline: {
    fy: number; median_peer: string; lunenburg: number; peer: number; gap: number
    fte_in_district: number; gap_in_dollars: number
    peer_median_of_categories: number; why_not_category_medians: number
    by_district: Record<string, number>
  }
  teachers: TeacherRow[]
  teachers_meta: { fy: number; worst_gap: number }
  demographics: {
    district: string; is_lunenburg: boolean; headcount: number; low_income: number
    swd: number; el: number
  }[]
  mcas: (Record<string, number> & { fy: number; district: string; is_lunenburg: boolean })[]
  mcas_meta: { measures: string[]; years: number[]; first_fy: number; last_fy: number }
  standing: {
    fy: number
    series: {
      fy: number; measure: string; basis: string; stage: string | null; districts: number
      p25: number; median: number; p75: number; lunenburg: number; rank: number
      above: number
    }[]
    stages: Record<string, number>
    peers: {
      district: string; is_lunenburg: boolean; foundation_budget: number
      required_local_contribution: number; rlc_share: number; ch70_aid: number
      required_nss: number; net_school_spending: number; stage: string
      pct_of_required: number; nss_over_foundation: number
    }[]
    nss: { fy: number; districts: number; median: number; p25: number; p75: number
      lunenburg: number; rank: number; above: number; stage: string | null }
    rlc: { fy: number; districts: number; median: number; p25: number; p75: number
      lunenburg: number; rank: number; above: number; stage: string | null }
    target: {
      target_aid_pct: number; target_local_share: number; actual_local_share: number
      points_below_target: number; statewide_target_aid_pct: number
      shortfall: number; dollar_increment: number
      town_foundation_budget: number; town_rlc: number
      district_foundation_budget: number; district_rlc: number; ch70_aid: number
      foundation_enrollment: number
    }
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

const TITLE = 'What other districts spend'

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

const kb = (n: number) => (n >= 1e6 ? `${(n / 1e6).toFixed(1)} MB` : `${Math.round(n / 1024)} KB`)

export function PeerSpending() {
  const [d, setD] = useState<Payload | null>(null)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    let live = true
    fetch('/data/peer-spending.json')
      .then(r => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then(j => { if (live) setD(j) })
      .catch(e => { if (live) setErr(String(e)) })
    return () => { live = false }
  }, [])

  if (err) return <Shell err={err} />
  if (!d) return <Shell loading />

  const H = d.headline
  const C = d.category_headline
  const L = d.lunenburg_denominator
  const S = d.standing
  const T = S.target
  const lun = d.decomposition.find(r => r.is_lunenburg)!
  const lunAtOld = d.decomposition.find(r => r.is_lunenburg)!
  const sortedAtOld = [...d.decomposition].sort((a, b) => b.at_old_enrolment - a.at_old_enrolment)
  const lastAtOld = sortedAtOld[sortedAtOld.length - 1]
  const spendPcts = d.decomposition.map(r => r.spend_pct)
  const spendLow = d.decomposition.find(r => r.spend_pct === Math.min(...spendPcts))!
  const spendHigh = d.decomposition.find(r => r.spend_pct === Math.max(...spendPcts))!
  const lunTeach = d.teachers.find(r => r.is_lunenburg)!
  const salaryOrder = [...d.teachers].sort((a, b) => b.average_salary - a.average_salary)
  const ratioOrder = [...d.teachers].sort((a, b) => b.per_hundred - a.per_hundred)
  const swBottom = d.statewide_categories.filter(c => c.in_bottom_quarter)
  const swTop = d.statewide_categories[d.statewide_categories.length - 1]
  const swWorst = d.statewide_categories[0]
  const swSecond = d.statewide_categories[1]
  const lunDemo = d.demographics.find(r => r.is_lunenburg)!
  const lowInc = d.demographics.map(r => r.low_income)
  const mcasLast = d.mcas.filter(r => r.fy === d.mcas_meta.last_fy)
  // Lunenburg's NEIGHBOUR in the order, derived from where it actually sits rather than
  // assumed to be last. It has been fifth in nine of the seventeen years and sixth in the
  // other eight, and a page that hardcodes "last" is wrong in nine of them.
  const lunLast = d.last_year.find(r => r.lea === '01620000')!
  const lunIdx = d.last_year.indexOf(lunLast)
  const nextLowest = d.last_year[lunIdx === d.last_year.length - 1 ? lunIdx - 1 : lunIdx + 1]
  const sw = d.statewide[d.statewide.length - 1]
  const swFirst = d.statewide[0]
  const bene = d.categories.find(c => c.code === 'BENE')!

  return (
    <Shell standfirst={<>
        What DESE says each Massachusetts district spends for each pupil &mdash;{' '}
        {fy(d.first_fy)} to {fy(d.last_fy)}, all funds.
      </>}
    >

      {/* ---------------------------------------------------------- 1. WHAT IT ESTABLISHES */}
      <div className="grid gap-6 mt-9"
        style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 15rem), 1fr))' }}>
        <Stat value={money(H.per_pupil)} tone={OURS}>
          Lunenburg in {fy(H.fy)}, per FTE pupil. <strong>All funds</strong> &mdash; not the
          school appropriation and not what a household pays
        </Stat>
        <Stat value={money(H.statewide_median)}>
          the median Massachusetts district in the same year. Lunenburg is{' '}
          {money(H.statewide_below_median)} below it
        </Stat>
        <Stat value={`${H.statewide_rank} of ${H.statewide_of}`}>
          Lunenburg&rsquo;s rank, highest first. {H.statewide_spend_less} districts spend
          less
        </Stat>
        <Stat value={`${H.bottom_quarter_years} of ${H.bottom_quarter_of}`}>
          years below the statewide first quartile &mdash;{' '}
          {H.bottom_quarter_unbroken ? 'every year DESE publishes here' : 'of the years published'}
        </Stat>
      </div>

      <H2 id="findings">What this page establishes</H2>
      <div className="grid gap-4 mt-6"
        style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 21rem), 1fr))' }}>
        <Insight n={1} headline={
          <>Lunenburg is in the bottom quarter of Massachusetts districts by per-pupil
            spending, and has been in every year the state publishes here.</>}>
          {money(H.per_pupil)} in {fy(H.fy)}, against a statewide median of{' '}
          {money(H.statewide_median)} and a middle half running{' '}
          {money(H.statewide_p25)}&ndash;{money(H.statewide_p75)}. Rank{' '}
          {H.statewide_rank} of {H.statewide_of}, so {H.statewide_spend_less} districts
          spend less. It has been below the first quartile in{' '}
          {H.bottom_quarter_years} of {H.bottom_quarter_of} years, {fy(swFirst.fy)} to{' '}
          {fy(sw.fy)}.
        </Insight>
        <Insight n={2} headline={
          <>Against the five comparison districts it has never been higher than{' '}
            {H.best_rank}th of {H.of} &mdash; and &ldquo;last&rdquo; in {fy(H.fy)} is a
            margin of {money(Math.abs(lunLast.per_pupil - nextLowest.per_pupil))}.</>}>
          {shortName(nextLowest.district)} is {money(nextLowest.per_pupil)} and Lunenburg is{' '}
          {money(lunLast.per_pupil)} &mdash;{' '}
          {pct1(Math.abs(lunLast.per_pupil / nextLowest.per_pupil - 1))} apart. Over{' '}
          {d.years} years Lunenburg&rsquo;s place in this set is {H.best_rank}th or{' '}
          {H.worst_rank}th and nothing else. The durable fact is the <em>quarter</em>, not
          the position.
        </Insight>
        <Insight n={3} headline={
          <>Most of the spread between these six is the denominator. Spending grew within a
            narrow band; enrolment did not.</>}>
          {fy(d.first_comparable_fy)} to {fy(d.last_fy)}: every district increased spending
          between {signedPct(spendLow.spend_pct)} ({shortName(spendLow.district)}) and{' '}
          {signedPct(spendHigh.spend_pct)} ({shortName(spendHigh.district)}).
          Lunenburg&rsquo;s was {signedPct(lun.spend_pct)}. Pupils are what separates them:{' '}
          {signedPct(lun.pupils_pct)} here against{' '}
          {signedPct(Math.min(...d.decomposition.map(r => r.pupils_pct)))} at the other end.
          Give {fy(d.last_fy)}&rsquo;s money to each district&rsquo;s{' '}
          {fy(d.first_comparable_fy)} pupil count and Lunenburg is{' '}
          {money(lunAtOld.at_old_enrolment)}, {lunAtOld.rank_at_old_enrolment} of{' '}
          {d.decomposition.length}, and {shortName(lastAtOld.district)} is last.
        </Insight>
        <Insight n={4} headline={
          <>The gap is concentrated in six lines, and reversed in three.</>}>
          Lunenburg&rsquo;s in-district spending is {money(C.lunenburg)} a pupil against{' '}
          {money(C.peer)} for {shortName(C.median_peer)}, the median district in the set
          &mdash; {money(Math.abs(C.gap))} a pupil, or{' '}
          {money(Math.abs(C.gap_in_dollars))} across {C.fte_in_district.toLocaleString()}{' '}
          in-district FTE pupils. It decomposes exactly across DESE&rsquo;s{' '}
          {d.categories.length} function categories, and the six largest negative lines are
          below.
        </Insight>
        <Insight n={5} headline={
          <>Against the whole state the two smallest lines are the extreme ones.</>}>
          {swWorst.desc} is {money(swWorst.lunenburg)} a pupil against a statewide median of{' '}
          {money(swWorst.median)} &mdash; {pct1(swWorst.share_of_median ?? 0)} of it, with{' '}
          {swWorst.spend_less} of {swWorst.districts} districts below.{' '}
          {swSecond.desc} is {money(swSecond.lunenburg)} against{' '}
          {money(swSecond.median)}. Lunenburg is in the bottom quarter of the state in{' '}
          {swBottom.length} of the {d.statewide_categories.length} categories DESE prints a
          per-pupil figure for. The exception is {swTop.desc}, at{' '}
          {money(swTop.lunenburg)} against {money(swTop.median)} &mdash; rank{' '}
          {swTop.rank} of {swTop.districts}.
        </Insight>
        <Insight n={6} headline={
          <>Lunenburg pays near the top of this set for teachers and employs the fewest of
            them per pupil.</>}>
          Average teacher salary {money(lunTeach.average_salary)},{' '}
          {salaryOrder.findIndex(r => r.is_lunenburg) + 1} of {d.teachers.length}, behind{' '}
          {shortName(salaryOrder[0].district)}&rsquo;s {money(salaryOrder[0].average_salary)}.
          Teachers per 100 in-district FTE pupils {lunTeach.per_hundred.toFixed(2)},{' '}
          {ratioOrder.findIndex(r => r.is_lunenburg) + 1} of {d.teachers.length}, against{' '}
          {ratioOrder[0].per_hundred.toFixed(2)} at the other end.
        </Insight>
        <Insight n={7} headline={
          <>Two Chapter 70 standings look like a contradiction, and one of them is a
            phase-in rather than a judgement.</>}>
          In {fy(S.fy)} the state requires Lunenburg to fund {pct1(S.rlc.lunenburg)} of its
          foundation budget against a median district&rsquo;s {pct1(S.rlc.median)}, and the
          town and state together put in {S.nss.lunenburg.toFixed(4)}&times; the minimum
          against a median of {S.nss.median.toFixed(4)}&times;. Both are &ldquo;less&rdquo;,
          from different starting points. The requirement is low because the formula&rsquo;s
          own <em>target</em> for Lunenburg is {pct1(T.target_local_share)} and the
          requirement is {T.points_below_target.toFixed(2)} points below it &mdash; a{' '}
          {money(T.shortfall)} shortfall still being phased in. It does not say the state
          judges the town poor. Which of the two the reader should care about depends on
          what they are trying to decide, and this page does not decide for them.
        </Insight>
        <Insight n={8} headline={
          <>A tenth of what DESE counts here is not general-fund money &mdash; and that is
            the smallest share in the set.</>}>
          Of {money(H.total)} in {fy(H.fy)}, {money(H.grants_revolving)} &mdash;{' '}
          {pct1(H.grant_share)} &mdash; came from grants and revolving funds.{' '}
          {shortName([...d.last_year].sort((a, b) => b.grant_share - a.grant_share)[0].district)}
          &rsquo;s share is{' '}
          {pct1([...d.last_year].sort((a, b) => b.grant_share - a.grant_share)[0].grant_share)}.
          Nothing above is the town&rsquo;s appropriation.
        </Insight>
      </div>

      <div className="card p-5 mt-6 max-w-3xl"
        style={{ borderLeft: '4px solid var(--status-warning)' }}>
        <p className="text-[15px] font-bold mb-1">This is not the town&rsquo;s bill</p>
        <p className="text-[14px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
          {d.not_this_page} The insurance and retirement line alone is{' '}
          {money(bene.lunenburg)} a pupil for Lunenburg in {fy(C.fy)}, and the school
          department does not carry it.
        </p>
      </div>

      <div className="card p-5 mt-4 max-w-3xl">
        <p className="text-[15px] font-bold mb-1">This is not a scorecard</p>
        <p className="text-[14px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
          Spending less than a neighbour is not a failure and spending more is not a
          success. Every figure here is a measurement; not one of them is a verdict, and no
          colour on this page means good or bad. The page does not argue that Lunenburg
          should spend more, and it does not argue that it is doing well on less &mdash;
          both of those are arguments residents are already making, in the documents quoted
          further down, and the data supports neither on its own. What it can do is put a
          checkable number under whichever one somebody is making.
        </p>
      </div>

      {/* ------------------------------------------------------- 2. THE ORGANISED DATA */}
      <H2 id="statewide">Lunenburg inside the whole state</H2>
      <Body>
        Every district in Massachusetts, as a distribution, with Lunenburg drawn through it.
      </Body>
      <Statewide rows={d.statewide} />
      <Span>
        {d.statewide.length} fiscal years &mdash; {fy(swFirst.fy)} to {fy(sw.fy)}.{' '}
        {sw.districts} districts in the latest year.
      </Span>
      <TableTwin
        caption="the same figures"
        head={['Year', 'Lunenburg', 'State median', 'Lower quartile', 'Upper quartile',
          'Rank', 'Spend less']}
        rows={d.statewide.map(r => [
          fy(r.fy), money(r.lunenburg), money(r.median), money(r.p25), money(r.p75),
          `${r.rank} of ${r.districts}`, r.spend_less])}
        note={<>Rank is highest first, DESE&rsquo;s own convention. The number of districts
          moves year to year because it counts those with a published figure, not those
          that exist.</>} />
      <NotShown>
        Where a district sits in this distribution says nothing about why. A district can be
        low because it is small, because it is not spending, because its costs are low, or
        because a large share of its spending is not in this collection at all. The
        distribution ranks; it does not explain.
      </NotShown>

      <H2 id="six">The six districts, {fy(H.fy)}</H2>
      <Body>
        Lunenburg and the five this project compares it to.
      </Body>
      <OneYear rows={d.last_year} median={
        [...d.last_year].map(r => r.per_pupil).sort((a, b) => a - b)[2]} />
      <Span>
        one fiscal year &mdash; {fy(H.fy)}. The dashed line is the median of these six, not
        the state&rsquo;s.
      </Span>
      <TableTwin
        caption="the same figures"
        head={['District', 'Per pupil', 'Total spending', 'General fund',
          'Grants and revolving', 'Share', 'FTE pupils']}
        rows={d.last_year.map(r => [
          r.district, money(r.per_pupil), money(r.total), money(r.gen_fund),
          money(r.grants_revolving), pct1(r.grant_share), r.fte_total.toLocaleString()])}
        mark={r => r[0] === 'Lunenburg'} />
      <Body>
        <strong>The set is ours, not DESE&rsquo;s.</strong> DESE&rsquo;s RADAR workbook
        covers all 421 Massachusetts districts; this archive extracts{' '}
        {d.districts.length} because the whole file takes the published database past a
        hosting limit. No document here records the criterion by which these were chosen,
        and a peer set is an argument &mdash; whoever picks one has already made a claim
        about what a town is comparable to. That is why every headline above is stated
        against the statewide distribution instead. The workbook itself is in the archive,
        so any other district can be checked against the same file.
      </Body>
      <Body>
        It is six in every year and not the <em>same</em> six throughout. Ayer and Shirley
        regionalised into Ayer Shirley for {fy(d.regionalisation.ayer_shirley_first_fy)}, so{' '}
        {fy(d.first_fy)}&ndash;{fy(d.regionalisation.ayer_last_fy)} hold Ayer instead. Every
        cross-district comparison below starts at {fy(d.first_comparable_fy)}.
      </Body>

      <H2 id="denominator">Money against pupils</H2>
      <Body>
        A per-pupil figure is a ratio, and between {fy(d.first_comparable_fy)} and{' '}
        {fy(d.last_fy)} the two halves moved very differently across these six districts.
      </Body>
      <MoneyAgainstPupils rows={d.decomposition} />
      <Span>
        {d.last_fy - d.first_comparable_fy} fiscal years &mdash;{' '}
        {fy(d.first_comparable_fy)} to {fy(d.last_fy)}.
      </Span>
      <TableTwin
        caption="the same figures, and the arithmetic"
        head={['District', 'Spending', 'FTE pupils', 'Per pupil',
          `${fy(d.last_fy)} money at ${fy(d.first_comparable_fy)} pupils`, 'Rank if so']}
        rows={d.decomposition.map(r => [
          r.district, signedPct(r.spend_pct), signedPct(r.pupils_pct),
          signedPct(r.per_pupil_pct), money(r.at_old_enrolment),
          `${r.rank_at_old_enrolment} of ${d.decomposition.length}`])}
        mark={r => r[0] === 'Lunenburg'}
        note={<>The identity is exact: (1 + spending growth) &divide; (1 + pupil growth) =
          (1 + per-pupil growth), checked for every district on every build. The fifth
          column is the same arithmetic run once more &mdash; {fy(d.last_fy)}&rsquo;s
          dollars over {fy(d.first_comparable_fy)}&rsquo;s pupils.</>} />
      <H3>Lunenburg alone, over its whole published series</H3>
      <Body>
        {fy(L.from_fy)} to {fy(L.to_fy)}: spending {signedPct(L.spend_pct)}, from{' '}
        {money(L.spend_from)} to {money(L.spend_to)}. FTE pupils{' '}
        {signedPct(L.pupils_pct)}, from {L.pupils_from.toLocaleString()} to{' '}
        {L.pupils_to.toLocaleString()}. Per pupil {money(L.per_pupil_from)} to{' '}
        {money(L.per_pupil_to)}. Hold the pupil count at its{' '}
        {fy(L.from_fy)} level and the same {fy(L.to_fy)} money is{' '}
        {money(L.at_old_enrolment)} a pupil &mdash; so {pct1(L.denominator_share)} of the
        rise in the ratio is the denominator rather than the money.
      </Body>
      <NotShown>
        That the fifth column is what would have happened. It is not a forecast and it is
        not a counterfactual: it is one year&rsquo;s money divided by an older year&rsquo;s
        pupil count, and a district with more pupils would not have spent the same amount.
        It is here to show how much of a per-pupil <em>difference</em> is arithmetic on the
        denominator, and nothing more. Nor does any of it say why enrolment fell, which is
        a question about births, housing and school choice and not about budgets.
      </NotShown>

      <H2 id="categories">Where the difference sits</H2>
      <Body>
        Lunenburg&rsquo;s in-district spending per pupil against {shortName(C.median_peer)}
        &rsquo;s, line by line. {shortName(C.median_peer)} because its in-district figure is
        the median of the five comparison districts.
      </Body>
      <CategoryGap rows={d.categories} peer={C.median_peer} />
      <Span>one fiscal year &mdash; {fy(C.fy)}. Per in-district FTE pupil.</Span>
      <TableTwin
        caption="every category, every district"
        head={['Category', 'Lunenburg', shortName(C.median_peer), 'Gap', 'Rank of 6',
          'Lowest of the five', 'Highest of the five']}
        rows={d.categories.map(r => [
          r.desc, money(r.lunenburg), money(r.median_peer), signedUsd(r.gap),
          `${r.rank} of ${r.of}`, money(r.peer_low), money(r.peer_high)])}
        note={<>Against one district rather than a category-by-category median, because a
          median of medians does not add up: these eleven per-category medians sum to{' '}
          {money(C.peer_median_of_categories)} while the median district&rsquo;s total is{' '}
          {money(C.peer)}, a difference of {money(C.why_not_category_medians)}. Against{' '}
          {shortName(C.median_peer)} the eleven gaps sum to {money(C.gap)} exactly, and the
          build fails if they stop doing so.</>} />

      <Body>
        Two of the eleven read the other way and are worth saying out loud, because a table
        of negatives invites a reader to fill in the positives themselves. Administration is{' '}
        {money(d.categories.find(c => c.code === 'ADMN')!.lunenburg)} a pupil, second
        highest of the six &mdash; and{' '}
        {money(d.statewide_categories.find(c => c.code === 'ADMN')!.median)} is the
        statewide median, so the same figure is rank{' '}
        {d.statewide_categories.find(c => c.code === 'ADMN')!.rank} of{' '}
        {d.statewide_categories.find(c => c.code === 'ADMN')!.districts} against the state.
        High in a small set and low in a large one is not a contradiction; it is what a set
        of six does, and it is the reason nothing on this page is concluded from the six
        alone.
      </Body>
      <H3>The same lines against all {sw.districts} districts</H3>
      <TableTwin
        caption={`${fy(C.fy)}, statewide`}
        head={['Category', 'Lunenburg', 'State median', 'Share of median', 'Rank',
          'Spend less']}
        rows={d.statewide_categories.map(r => [
          r.desc, money(r.lunenburg), money(r.median),
          r.share_of_median === null ? '—' : pct1(r.share_of_median),
          `${r.rank} of ${r.districts}`, r.spend_less])}
        note={<>Out-of-district transportation is absent because DESE publishes no
          per-pupil figure against its out-of-district rows. The district count differs by
          category because it counts districts with a published figure for that
          line.</>} />
      <NotShown>
        What any of these lines buys. A Teachers figure is not a class size; an
        Instructional Materials figure is not a textbook count; a Pupil Services figure is
        not a number of counsellors or nurses. These are dollars over a pupil count, and the
        step from a dollar to a service is exactly the step this archive cannot take.
        Registered as a gap rather than guessed at.
      </NotShown>

      <H2 id="teachers">Teachers: what they are paid, and how many there are</H2>
      <TeacherSplit rows={d.teachers} />
      <Span>one fiscal year &mdash; {fy(d.teachers_meta.fy)}.</Span>
      <TableTwin
        caption="the same figures"
        head={['District', 'Average teacher salary', 'Teacher FTE',
          'Per 100 in-district pupils', 'Teachers line, per pupil',
          'Paraprofessional FTE']}
        rows={[...d.teachers].sort((a, b) => b.per_pupil - a.per_pupil).map(r => [
          r.district, money(r.average_salary), r.teacher_fte.toLocaleString(),
          r.per_hundred.toFixed(2), money(r.per_pupil), r.para_fte.toLocaleString()])}
        mark={r => r[0] === 'Lunenburg'} />
      <Body>
        <strong>The multiplication is DESE&rsquo;s own construction, not a finding.</strong>{' '}
        The Teachers function&rsquo;s spending divided by teacher FTE equals DESE&rsquo;s
        published average teacher salary to within {pct1(d.teachers_meta.worst_gap)} in the
        worst of the six, so &ldquo;salary times ratio equals per-pupil cost&rdquo; is close
        to restating a definition. What it is <em>for</em> is that it says which half moves:
        on this measure Lunenburg&rsquo;s teacher spending is low because of how many
        teachers there are, not because of what they are paid.
      </Body>
      <NotShown>
        That fewer teachers per pupil means larger classes. A teacher FTE is not a section
        and not a class; a district with more grade levels, more schools or more
        single-section subjects needs a different number of teachers for the same class
        size. DESE publishes no class size here at all. Nor does a paraprofessional FTE
        count people: it is full-time equivalents, and it does not say which fund pays for
        any of them.
      </NotShown>

      <H2 id="funds">Whose money it is</H2>
      <Body>
        Every figure above is computed over this total, and a tenth of Lunenburg&rsquo;s is
        money the town never appropriated.
      </Body>
      <FundSplit rows={d.last_year} />
      <Span>one fiscal year &mdash; {fy(H.fy)}.</Span>
      <TableTwin
        caption="the same figures"
        head={['District', 'General fund', 'Grants and revolving', 'Total',
          'Not general fund']}
        rows={[...d.last_year].sort((a, b) => b.grant_share - a.grant_share).map(r => [
          r.district, money(r.gen_fund), money(r.grants_revolving), money(r.total),
          pct1(r.grant_share)])}
        mark={r => r[0] === 'Lunenburg'} />
      <NotShown>
        Which grant paid for what. DESE publishes one grants-and-revolving column and does
        not break it down, so a district whose share fell may have lost a federal programme,
        stopped collecting a fee, or moved a cost onto the town &mdash; and all three look
        identical here. That is the same wall{' '}
        <a className="underline" style={{ color: 'var(--series-cost)' }}
          href={abs('/when-grants-end')}>/when-grants-end</a> runs into, from the other
        side.
      </NotShown>

      {/* ------------------------------------------------- 3. THE TWO STANDINGS */}
      <H2 id="standing">Two measures that look like a contradiction</H2>
      <Body>
        DESE publishes two Chapter 70 standings for Lunenburg against every district in the
        state. In {fy(S.fy)} they appear to point in opposite directions.
      </Body>
      <div className="grid gap-6 mt-6"
        style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 17rem), 1fr))' }}>
        <div className="card p-5">
          <div className="text-3xl font-bold tracking-tight tnum" style={{ color: OURS }}>
            {pct1(S.rlc.lunenburg)}
          </div>
          <p className="text-[13.5px] leading-snug mt-1"
            style={{ color: 'var(--text-secondary)' }}>
            of its foundation budget is what the state <strong>requires</strong> Lunenburg
            to contribute. The median district is at {pct1(S.rlc.median)}. Rank{' '}
            {S.rlc.rank} of {S.rlc.districts} &mdash; {S.rlc.above} districts are required
            to fund a larger share.
          </p>
        </div>
        <div className="card p-5">
          <div className="text-3xl font-bold tracking-tight tnum" style={{ color: OURS }}>
            {S.nss.lunenburg.toFixed(4)}&times;
          </div>
          <p className="text-[13.5px] leading-snug mt-1"
            style={{ color: 'var(--text-secondary)' }}>
            of the minimum is what the town and state together actually put in. The median
            district is at {S.nss.median.toFixed(4)}&times;. Rank {S.nss.rank} of{' '}
            {S.nss.districts} &mdash; {S.nss.above} districts spend a larger multiple.
            Stage: <strong>{S.nss.stage}</strong>.
          </p>
        </div>
      </div>
      <Body>
        Read carelessly that is <em>the state asks Lunenburg for less than most towns, and
        Lunenburg still puts in less above the minimum than most towns.</em> Read carefully
        it is two different denominators, and one of them is not what it looks like.
      </Body>
      <H3>The required share is a phase-in position, not a judgement that the town is poor</H3>
      <Body>
        The formula&rsquo;s own <strong>target</strong> local share for Lunenburg in{' '}
        {fy(S.fy)} is {pct1(T.target_local_share)} &mdash; DESE sets the target{' '}
        <em>aid</em> share at {T.target_aid_pct.toFixed(1)}%, against{' '}
        {T.statewide_target_aid_pct.toFixed(0)}% statewide, which means the formula treats
        Lunenburg as comparatively <em>wealthy</em>. The requirement of{' '}
        {pct1(T.actual_local_share)} sits {T.points_below_target.toFixed(2)} percentage
        points below that target: a shortfall of {money(T.shortfall)}, of which{' '}
        {fy(S.fy)} closes {money(T.dollar_increment)}. So the low required share does not
        say the state thinks Lunenburg cannot afford more. It says the formula has not
        finished asking.
      </Body>
      <TableTwin
        caption={`the six districts on both measures, ${fy(S.fy)}`}
        head={['District', 'Foundation budget', 'Required contribution', 'Share of it',
          'Chapter 70 aid', 'Net school spending', 'Of required']}
        rows={[...S.peers].sort((a, b) => b.pct_of_required - a.pct_of_required).map(r => [
          shortName(r.district), money(r.foundation_budget),
          money(r.required_local_contribution), pct1(r.rlc_share), money(r.ch70_aid),
          money(r.net_school_spending), `${r.pct_of_required.toFixed(4)}×`])}
        mark={r => r[0] === 'Lunenburg'}
        note={<>Every net school spending figure here is at the same stage &mdash;{' '}
          <strong>{S.peers[0].stage}</strong> &mdash; and the build refuses to write if
          they are not. See below.</>} />
      <div className="card p-4 mt-5 max-w-2xl"
        style={{ borderLeft: '4px solid var(--status-warning)' }}>
        <p className="text-[11px] font-semibold uppercase tracking-widest mb-1.5"
          style={{ color: 'var(--text-muted)' }}>Rule 1, and it is load-bearing here</p>
        <p className="text-[14px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
          The net school spending measure carries a <em>stage</em> in DESE&rsquo;s own
          basis column &mdash;{' '}
          {Object.entries(S.stages).map(([k, v]) => `${v} year${v === 1 ? '' : 's'} ${k}`)
            .join(', ')}{' '}
          &mdash; and the two are different quantities under one name. Nothing here is
          differenced across it. The {fy(S.fy)} Chapter 70 figures and the {fy(H.fy)}{' '}
          spending figures are also never subtracted from one another: one is a budgeted
          formula calculation, the other is what districts reported after a year closed.
        </p>
      </div>
      <NotShown>
        Whether the smaller margin above the minimum is a town choosing to spend less or a
        town unable to raise more. The levy limit, two failed overrides, the district&rsquo;s
        proposed budget and Town Meeting&rsquo;s vote all resolve into one number, and the
        number is the outcome of all of them at once. Nothing published separates them, and
        the two readings imply opposite remedies. It is a registered gap, not a conclusion
        withheld. See{' '}
        <a className="underline" style={{ color: 'var(--series-cost)' }}
          href={abs('/why-we-only-get-minimum-aid')}>/why-we-only-get-minimum-aid</a> for
        the formula term by term.
      </NotShown>

      <H2 id="planning">What this changes for planning</H2>
      <Body>
        Rule 8: a finding arrives as what it means for planning, never as what somebody got
        wrong. Four things follow from the arithmetic above, and none of them is a
        recommendation about how much to spend.
      </Body>
      <div className="grid gap-4 mt-6"
        style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 21rem), 1fr))' }}>
        <div className="card p-5">
          <p className="text-[15px] font-bold leading-snug">
            A per-pupil comparison is always at least a year behind the budget being voted
          </p>
          <p className="text-[14px] leading-relaxed mt-2"
            style={{ color: 'var(--text-secondary)' }}>
            <em>What would you have had to see, and when?</em> These figures are
            DESE&rsquo;s end-of-year collection, reported after a fiscal year closes. The
            latest here is {fy(H.fy)}, and the Chapter 70 figures below are for{' '}
            {fy(S.fy)}. A board voting a budget today is looking at a comparison of years
            that have already closed, and every district in it has since moved.
            The comparison is a description of where a town has been, not an input to a
            budget, and quoting it as though it described the year being voted is the
            single easiest mistake to make with it.
          </p>
        </div>
        <div className="card p-5">
          <p className="text-[15px] font-bold leading-snug">
            Enrolment moves this number as hard as money does, and it moves on its own
          </p>
          <p className="text-[14px] leading-relaxed mt-2"
            style={{ color: 'var(--text-secondary)' }}>
            {pct1(L.denominator_share)} of the rise in Lunenburg&rsquo;s own per-pupil
            figure since {fy(L.from_fy)} is the denominator. A district that loses pupils
            without cutting proportionally will climb this table without deciding anything,
            and a district that holds its enrolment will fall down it while spending more
            every year. Neither movement is a budget decision, and a plan built on the
            ratio rather than on the two halves is planning against an artefact.
          </p>
        </div>
        <div className="card p-5">
          <p className="text-[15px] font-bold leading-snug">
            The lines furthest below the state are the ones grants are already covering
          </p>
          <p className="text-[14px] leading-relaxed mt-2"
            style={{ color: 'var(--text-secondary)' }}>
            Professional development and instructional materials are the two categories
            furthest below the statewide median, and they are also what the
            Superintendent&rsquo;s own reports describe grant and earmark money buying
            &mdash; quoted below, in the district&rsquo;s words. {pct1(H.grant_share)} of
            everything counted on this page is grant and revolving money. Which means a
            plan that treats the general-fund line as the whole of either category is
            planning against a fraction, in both directions: the service is larger than the
            line, and it is also less secure than the line, because a grant ends and an
            appropriation is voted again.
          </p>
        </div>
        <div className="card p-5">
          <p className="text-[15px] font-bold leading-snug">
            Where the district is visibly doing the sensible thing, it is not in this data
          </p>
          <p className="text-[14px] leading-relaxed mt-2"
            style={{ color: 'var(--text-secondary)' }}>
            A district spending {money(swWorst.lunenburg)} a pupil on professional
            development that is sharing it with a neighbouring district is a different fact
            from one that is not, and DESE&rsquo;s figure cannot tell the two apart. The
            Superintendent reported exactly that arrangement with North Middlesex on{' '}
            {d.said.find(q => q.key === 'sharing-pd')?.date}. It is in the minutes and it is
            nowhere in the numbers, which is worth knowing before anybody quotes{' '}
            {money(swWorst.lunenburg)} at a meeting.
          </p>
        </div>
      </div>

      {/* ------------------------------------------------------ 4. WHAT PEOPLE SAID */}
      <H2 id="said">What people in Lunenburg have already said about this</H2>
      <Body>
        Residents have been making this comparison at School Committee for years, in both
        directions. These are the documents.
      </Body>
      <div className="grid gap-4 mt-6"
        style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 22rem), 1fr))' }}>
        {d.said.map(q => <Quote key={q.key} q={q} />)}
      </div>
      <Body>
        The search covered <strong>{d.minutes.searchable.toLocaleString()}</strong> of the{' '}
        {d.minutes.held.toLocaleString()} meeting documents this archive holds &mdash;{' '}
        {pct1(d.minutes.searchable_share)}. The other{' '}
        {d.minutes.unsearchable.toLocaleString()} carry no searchable text at all, almost
        all of them image scans awaiting OCR. An empty result would not have meant nobody
        said it.
      </Body>
      <TableTwin
        caption="what was searched, and how many documents contain each term"
        head={['Term', 'Documents']}
        rows={d.searched.map(t => [t.term, t.documents])} />

      {/* ------------------------------------------------------------- 5. MCAS */}
      <H2 id="mcas">MCAS &mdash; and nothing here tests any relation to spending</H2>
      <Body>
        Printed because residents argue about it in both directions on the same page as the
        spending, and for no other reason. <strong>Nothing on this page establishes any
        relation between what a district spends and how its students score, and nothing in
        this archive could.</strong>
      </Body>
      <TableTwin
        caption={`${fy(d.mcas_meta.last_fy)} — per cent meeting or exceeding expectations`}
        head={['District', ...d.mcas_meta.measures.map(m => m.replace(' % Meets or Exceeds', ''))]}
        rows={[...mcasLast]
          .sort((a, b) => (b[d.mcas_meta.measures[1]] as number)
            - (a[d.mcas_meta.measures[1]] as number))
          .map(r => [r.district, ...d.mcas_meta.measures.map(
            m => pct1(r[m] as number))])}
        mark={r => r[0] === 'Lunenburg'} />
      <Span>
        {d.mcas_meta.years.length} fiscal years are in the data &mdash;{' '}
        {fy(d.mcas_meta.first_fy)} to {fy(d.mcas_meta.last_fy)}. One is shown.
      </Span>
      <NotShown>
        Anything at all about spending and results. Six districts, one year, no control for
        anything: the low-income share across these six runs from{' '}
        {pct1(Math.min(...lowInc))} to {pct1(Math.max(...lowInc))} of students, which is a
        wider spread than the spending. The two districts above Lunenburg on every measure
        are the two with the lowest low-income share in the set, and that is offered as a
        reason <strong>not</strong> to read the table as a spending result rather than as an
        alternative explanation for one. And this archive holds no statewide distribution of
        MCAS, so no state percentile can be computed for any of these figures &mdash; which
        is why the performance half of the claim quoted above cannot be checked here while
        the spending half can.
      </NotShown>
      <H3>Who the students are, {fy(H.fy)}</H3>
      <TableTwin
        head={['District', 'Headcount', 'Low-income', 'Students with disabilities',
          'English learners']}
        rows={[...d.demographics].sort((a, b) => b.low_income - a.low_income).map(r => [
          r.district, r.headcount.toLocaleString(), pct1(r.low_income), pct1(r.swd),
          pct1(r.el)])}
        mark={r => r[0] === 'Lunenburg'}
        note={<>Lunenburg&rsquo;s low-income share is {pct1(lunDemo.low_income)} and its
          students-with-disabilities share {pct1(lunDemo.swd)}. Headcount is a count of
          students; the per-pupil figures above are over FTE pupils, which is a different
          quantity, and the two are never divided into one another here.</>} />

      {/* --------------------------------------------------- 6. THE RAW AND THE CAVEATS */}
      <H2 id="not-established">What this page does not establish</H2>
      <div className="grid gap-3 mt-5"
        style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 22rem), 1fr))' }}>
        {d.not_established.map((n, i) => (
          <div key={i} className="card p-4 text-[14px] leading-relaxed"
            style={{ color: 'var(--text-secondary)' }}>{n}</div>
        ))}
      </div>

      <H2 id="gaps">The limits, registered</H2>
      <Body>
        Every one of these is a row in{' '}
        <a className="underline" style={{ color: 'var(--series-cost)' }}
          href={abs('/data/money_gaps.json')}>the gap register</a> rather than a sentence on
        this page alone, so that the next person to hit the same wall finds it named. They
        render at{' '}
        <a className="underline" style={{ color: 'var(--series-cost)' }}
          href={abs('/what-we-cannot-answer')}>/what-we-cannot-answer</a>.
      </Body>
      <div className="grid gap-4 mt-6"
        style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 22rem), 1fr))' }}>
        {d.gaps.map(g => (
          <div key={g.what} className="card p-4">
            <p className="text-[15px] font-bold leading-snug">{g.what}</p>
            <p className="text-[13.5px] leading-relaxed mt-2"
              style={{ color: 'var(--text-secondary)' }}>{g.why}</p>
            {g.closes && (
              <p className="text-[13px] leading-relaxed mt-2.5">
                <span className="text-[11px] font-semibold uppercase tracking-widest mr-1.5"
                  style={{ color: 'var(--text-muted)' }}>closes</span>
                <span style={{ color: 'var(--text-secondary)' }}>{g.closes}</span>
              </p>
            )}
          </div>
        ))}
      </div>

      <H2 id="instrument">A note on the instrument</H2>
      <Body>
        DESE prints one column headed per-pupil and computes it over <strong>two different
        denominators</strong>: the district total over <strong>total</strong> FTE pupils,
        and every other row &mdash; the in-district rollup and all{' '}
        {d.categories.length} categories &mdash; over <strong>in-district</strong> FTE
        pupils. That is verified against DESE&rsquo;s own dollar totals on{' '}
        {d.denominators.rows_tested.toLocaleString()} rows, every build, to the dollar, with
        no exceptions.
      </Body>
      <Body>
        This archive&rsquo;s own derived table carries a basis column reading{' '}
        &ldquo;{d.denominators.label_in_our_table}&rdquo; on every row, and on the
        district-total row that is wrong &mdash; {d.denominators.label_is_wrong_on} Nothing
        on this page quotes it; the basis is asserted from the arithmetic instead. It is
        recorded rather than quietly corrected because it is the exact shape of the defect
        this project keeps finding: something derived written down, and then quoted as
        though it had been observed.
      </Body>

      <H2 id="sources">Where every figure comes from</H2>
      <div className="grid gap-4 mt-6"
        style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 22rem), 1fr))' }}>
        {d.documents.map(doc => (
          <div key={doc.key} className="card p-4">
            <p className="text-[15px] font-bold leading-snug">
              <a className="underline" style={{ color: 'var(--series-cost)' }}
                href={abs(doc.docs_url)}>{doc.filename}</a>
            </p>
            <p className="text-[13.5px] leading-relaxed mt-2"
              style={{ color: 'var(--text-secondary)' }}>{doc.what}</p>
            <p className="text-[13px] leading-relaxed mt-2"
              style={{ color: 'var(--text-secondary)' }}>
              <strong>Stage:</strong> {doc.stage}
            </p>
            <p className="text-[11.5px] mt-2 break-all" style={{ color: 'var(--text-muted)' }}>
              {doc.publisher} &middot; {kb(doc.bytes)} &middot;{' '}
              <a className="underline" href={doc.url}>the publisher&rsquo;s copy</a>
              <br />sha256 {doc.sha256}
            </p>
          </div>
        ))}
      </div>
      <Body>
        The rows behind every chart are published at{' '}
        <a className="underline" style={{ color: 'var(--series-cost)' }}
          href={abs('/data/peer-spending.json')}>/data/peer-spending.json</a>, written by{' '}
        <code>scripts/build_peer_spending.py</code>, which refuses to write if any
        assertion in it stops holding. The long-form analysis is at{' '}
        <a className="underline" style={{ color: 'var(--series-cost)' }}
          href={abs('/docs/analyses/per-pupil-spending.md')}>
          /docs/analyses/per-pupil-spending.md</a>.
      </Body>
      <Legend items={[
        { hue: OURS, label: 'Lunenburg, throughout' },
        { hue: FIELD, label: 'every other district — a field, not a ranking' },
      ]} />
    </Shell>
  )
}
