import type { Tab } from '../routes'
import { useEffect, useState } from 'react'
import { abs } from '../lib/abs'
import {
  AssessmentSeries, CAPITAL, Forecast, Legend, MINIMUM, Parts, SOFT, SOLID, Shares, Span,
  Students, TRANSPORT, TableTwin, fy, money, pct1, pct2, signedPct,
  type ForecastRow, type PartRow, type SeriesRow, type ShareRow, type StudentRow,
} from '../components/MontyTechCharts'
import {
  Conclusions,
  Body, H2, H3, Insight, NotShown, Quote, Stat,
  ReportShell,
} from '../components/report'
import type { Conclusion } from '../components/report'

const TAB: Tab = 'montytech'
const DATA = '/data/monty-tech.json'

/** What Lunenburg is assessed for Montachusett Regional Vocational Technical, what sets
 *  that figure, and what neither the town nor the district publishes about it.
 *
 *  WHY THIS PAGE IS DIFFERENT FROM EVERY OTHER SPENDING PAGE HERE. Every other line this
 *  site measures is something Lunenburg appropriates. This one is an ASSESSMENT on a
 *  member town of a regional district, and about 95% of it is the Chapter 70 minimum
 *  required local contribution — computed by the state from the town's property value and
 *  resident income, and apportioned between the town's two school districts by foundation
 *  budget share. No Lunenburg vote sets it. The page leads with that, because a reader who
 *  does not know it will read every number below as a decision somebody made.
 *
 *  RULE 13 GOVERNS THE CENTRAL CHART. Eleven of the twelve annual-report figures for this
 *  line carry `check failed` or `no check`, and CLAUDE.md forbids aggregating across
 *  `status`. They are drawn hollow and unjoined, they are labelled candidates in the
 *  legend and in the table's own status column, and the established series they are drawn
 *  against is a different derivation entirely.
 *
 *  RULE 11 IS A SECTION, NOT A FOOTNOTE. The assessment is what the town is BILLED. Monty
 *  Tech's Chapter 70 aid is paid to the district directly and pays for more than half of
 *  what it spends; the bill and the cost are different quantities and the page says which
 *  one it holds.
 *
 *  RULE 7. The arithmetic here is exact — a four-part identity that sums, a share identity
 *  that reproduces to a tenth of a basis point, five figures matching public statements to
 *  the dollar. Every explanation for any of it is a hypothesis and is labelled one.
 *
 *  RULE 8. Not an audit. A forecast that missed by a third is a line governed by something
 *  other than inflation, not a failure by anybody; the district publishes its own
 *  apportionment in full and the page says so.
 *
 *  RULE 7b. Conclusions, then the organised categories, then the raw and the caveats.
 *  RULE 7a within each: the thing first, the note about how to read it after.
 *
 *  RULE 2. Not one figure is typed into this file. Everything arrives from
 *  /data/monty-tech.json, written by scripts/build_monty_tech.py.
 *
 *  NO D1 AT PAGE LOAD. One static file. */

type Said = {
  key: string; board: string; date: string; kind: string; quote: string; why: string
  who: string; cite: string; town: string
}

type Figure = {
  key: string; title: string; what: string; basis: string; line: number; lines: number
  row: string; text: string; path: string; docs_url: string; text_url: string
  filename: string; sha256: string; bytes: number; url: string
  values: Record<string, number>
}

type ReqRow = {
  fy: number
  town_fe: number; lps_fe: number; mt_fe: number
  town_fb: number; lps_fb: number; mt_fb: number
  town_rlc: number; lps_rlc: number; mt_rlc: number
  rlc_share: number; fb_share: number; fe_share: number
  mt_fb_per_pupil: number; lps_fb_per_pupil: number; wealth_bound: boolean
}

type Candidate = {
  fy: number; edition: string; page: string; value: number | null
  available: number | null; expended: number | null
  status: string; column_meaning: string; columns_established: boolean
  ruler_spanned: boolean; n_values: number; unparsed: string; usable: boolean
  required: number | null; over: number | null; over_pct: number | null
  document: string; publisher_label: string; sha256: string; upstream: string
  docs_url: string
}

type Assessed = {
  fy: number; required: number | null; transport: number | null; capital: number | null
  total: number; foundation_budget: number | null; foundation_enrollment: number | null
  source: string; kind: string; note: string; identity: number | null
  required_share?: number; above_minimum?: number
}

type Payload = {
  conclusions: Conclusion[]
  about: string
  ledger_fy: number; first_fy: number; last_fy: number
  headline: {
    ledger_fy: number; assessment: number; expended: number; account: string
    required: number; discretionary: number; required_share: number
    students: number; foundation: number; per_student: number; school_choice: number
    larger_than_choice: boolean
    rlc_share: number; fe_share: number; fb_share: number
    mt_fb_per_pupil: number; lps_fb_per_pupil: number; foundation_ratio: number
    from_fy: number; to_fy: number
    required_from: number; required_to: number; required_pct: number
    students_from: number; students_to: number; students_pct: number
    town_rlc_from: number; town_rlc_to: number; town_rlc_pct: number; lps_rlc_pct: number
    rise_years: number; of_years: number
    longest_rise: number; longest_rise_from: number; longest_rise_to: number
    low_fy: number; low: number; since_low_pct: number
    count_gap_min: number; count_gap_max: number
    transport: number; capital: number; above_minimum: number
    next_fy: number; next_total: number; next_pct: number
    district_budget: number; district_ch70: number; district_ch70_share: number
    district_assessments: number; district_assessment_share: number
    of_district_budget: number; of_all_assessments: number; of_members: number
    members_fe: number; district_per_pupil: number
    students_prev?: number
  }
  required: ReqRow[]
  apportionment: {
    years: number; exact: number; tolerance: number
    off: { fy: number; gap_pp: number }[]
    worst_fy: number | null; worst_gap_pp: number | null
  }
  wealth: {
    years: number; wealth_bound_years: number; cap_pct: number
    first_fy: number; last_fy: number
  }
  corroboration: {
    fy: number; field: string; stated: number; derived: number; who: string
    what: string; board: string; date: string; cite: string; town: string
  }[]
  printed_apportionment: {
    fy: number; fields: number; printed_share_pct: number; derived_share_pct: number
  }
  ledger: {
    doc_id: string; fy: number; period: string; fund: string; dept: string; org: string
    object: string; account: string; name: string
    original: number; revised: number; expended: number; available: number
    pct_used: string
  }
  candidates: Candidate[]
  candidates_meta: {
    n: number; first_fy: number; last_fy: number; below: number[]; in_band: number
    min_pct: number; max_pct: number; outlier_fy: number; outlier_pct: number
    ledger_fy: number; ledger_over_pct: number
  }
  assessment: Assessed[]
  assessment_meta: {
    fy27_district: number; fy27_town: number; fy27_gap: number
    fy25_budgeted: number; fy25_actual: number; fy25_gap: number
    fy24_district: number; fy24_town: number; fy24_gap: number
    fy26_ties: boolean; district_per_pupil: number; district_per_pupil_fy27: number
  }
  district: {
    fy: number; budget: number; ch70: number; all_assessments: number
    all_required: number; all_transport: number; all_capital: number
    ch70_share: number; assessment_share: number; other_share: number
    lunenburg: number; lunenburg_of_assessments: number; lunenburg_of_budget: number
    lunenburg_fe: number; members_fe: number; lunenburg_fe_share: number
  }[]
  students: {
    fy: number; monty_tech: number; school_choice: number; charter: number
    in_lunenburg: number; all_resident: number; mt_share: number | null
  }[]
  students_meta: { district_names: string[]; lea: string; first_fy: number; last_fy: number }
  counts: { fy: number; headcount: number; foundation: number; difference: number }[]
  forecast: {
    board: string; date: string; cite: string; town: string; rate: number; quote: string
    series: { fy: number; projected: number; required: number | null }[]
    base_fy: number; base: number; actual_fy: number; actual: number; projected: number
    miss: number; miss_pct: number; required_cagr: number
  }
  report_monty_tech: { rows: number; editions: string[] }
  figures: Record<string, Figure>
  said: Said[]
  searched: { term: string; documents: number }[]
  minutes: {
    held: number; searchable: number; unsearchable: number; image_scan: number
    searchable_share: number
  }
  documents: {
    key: string; what: string; publisher: string; stage: string; path: string
    sha256: string; bytes: number; url: string; docs_url: string; filename: string
  }[]
  gaps: { side: string; what: string; why: string; closes: string | null }[]
  not_established: string[]
}

const TITLE = 'Monty Tech — the school bill nobody here votes on'

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
const cash = (n: number) => `$${n.toLocaleString('en-US', {
  minimumFractionDigits: 2, maximumFractionDigits: 2,
})}`

export function MontyTech() {
  const [d, setD] = useState<Payload | null>(null)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    let live = true
    fetch('/data/monty-tech.json')
      .then(r => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then(j => { if (live) setD(j) })
      .catch(e => { if (live) setErr(String(e)) })
    return () => { live = false }
  }, [])

  if (err) return <Shell err={err} />
  if (!d) return <Shell loading />

  const H = d.headline
  const M = d.assessment_meta
  const F = d.forecast
  const A = d.apportionment
  const W = d.wealth
  const CM = d.candidates_meta
  const last = d.required[d.required.length - 1]
  const first = d.required.find(r => r.fy === H.from_fy)!
  const dist = d.district[0]
  const latestStu = d.students[d.students.length - 1]
  const firstStu = d.students[0]
  const latestCount = d.counts[d.counts.length - 1]
  const usable = d.candidates.filter(c => c.usable)
  const notUsable = d.candidates.filter(c => !c.usable)
  const outlier = usable.find(c => c.fy === CM.outlier_fy)!
  const parts = d.assessment.filter(a => a.transport !== null) as
    (Assessed & { transport: number; required: number; capital: number })[]
  const fy26 = d.assessment.find(a => a.fy === d.ledger_fy)!
  const methodFig = d.figures.method
  const opFig = d.figures['method-operating']
  const capFig = d.figures['method-capital']
  const partsFig = d.figures['parts-fy26-fy27']
  const distFig = d.figures['district-budget']

  const said = (k: string) => d.said.find(q => q.key === k)

  // The central series: one row per fiscal year, with each figure in its own field so the
  // chart can draw an established point and a candidate point differently. Built here
  // rather than in the payload because it is a presentation shape, not a finding.
  const series: SeriesRow[] = (() => {
    const yrs = new Set<number>([
      ...d.required.map(r => r.fy),
      ...d.candidates.map(c => c.fy),
      ...d.assessment.map(a => a.fy),
    ])
    return [...yrs].sort((a, b) => a - b).map(y => {
      const req = d.required.find(r => r.fy === y)
      const cand = d.candidates.find(c => c.fy === y && c.usable)
      const doc = d.assessment.find(a => a.fy === y)
      return {
        fy: y,
        required: req ? req.mt_rlc : null,
        documented: doc && y !== d.ledger_fy ? doc.total : null,
        ledger: y === d.ledger_fy ? d.ledger.original : null,
        candidate: cand ? cand.value : null,
        status: cand ? cand.status : '',
      }
    })
  })()

  const shareRows: ShareRow[] = d.required.map(r => ({
    fy: r.fy, rlc_share: r.rlc_share, fe_share: r.fe_share,
  }))

  const partRows: PartRow[] = parts.map(p => ({
    fy: p.fy, required: p.required, transport: p.transport, capital: p.capital,
    total: p.total,
  }))

  const studentRows: StudentRow[] = d.students.map(s => ({
    fy: s.fy, monty_tech: s.monty_tech, school_choice: s.school_choice,
    charter: s.charter,
  }))

  const forecastRows: ForecastRow[] = [
    { fy: F.base_fy, projected: F.base, required: null, actual: null },
    ...F.series.map(s => ({
      fy: s.fy, projected: s.projected, required: s.required,
      actual: s.fy === F.actual_fy ? F.actual : null,
    })),
  ]

  return (
    <Shell standfirst={<>
        Lunenburg is a member town of the Montachusett Regional Vocational Technical
        district. It is assessed, not billed a tuition &mdash; and most of the assessment
        is a figure the state calculates.
      </>}
    >

      {/* ------------------------------------------------------- 1. WHAT IT ESTABLISHES */}
      <div className="grid gap-6 mt-9"
        style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 15rem), 1fr))' }}>
        <Stat value={money(H.assessment)} tone={SOLID}>
          the FY{String(H.ledger_fy).slice(2)} assessment, out of the town&rsquo;s own
          ledger. Appropriated and expended in full
        </Stat>
        <Stat value={pct1(H.required_share)} tone={MINIMUM}>
          of it is the Chapter&nbsp;70 minimum required local contribution, computed by the
          state. <strong>No Lunenburg vote sets it</strong>
        </Stat>
        <Stat value={money(H.above_minimum)}>
          is everything else &mdash; transportation and capital, apportioned by the
          district among its member towns
        </Stat>
        <Stat value={`${H.students} / ${H.school_choice}`}>
          Lunenburg residents at Monty Tech against school choice. The larger outflow, and
          the one the town cannot decline
        </Stat>
      </div>

      {/* ------------------------------------------------ 1. CONCLUSIONS (rule 7b) */}
      {/* NOT WRITTEN HERE. Every word and every figure comes out of this report's own
          payload, computed by the generator that computed the figures -- see
          scripts/conclusions.py. The same rows appear on /what-it-all-adds-up-to, read
          from the same file, so the two cannot drift apart. */}
      <H2 id="conclusions">If you read nothing else</H2>
      <Conclusions rows={d.conclusions} />

      <H2 id="findings">What this page establishes</H2>
      <div className="grid gap-4 mt-6"
        style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 21rem), 1fr))' }}>
        <Insight n={1} headline={
          <>The town paid {money(H.assessment)} in FY{String(H.ledger_fy).slice(2)}, and{' '}
            {pct1(H.required_share)} of that was a figure the state calculated.</>}>
          The Town&rsquo;s accounting system carries it in full: department{' '}
          {d.ledger.dept}, account <code className="text-[12.5px]">{d.ledger.account}</code>,
          appropriated {money(d.ledger.original)} and expended{' '}
          {money(d.ledger.expended)} at period {d.ledger.period}. The district&rsquo;s own
          book splits the same figure into a required minimum contribution of{' '}
          {money(fy26.required!)}, transportation and other operating of{' '}
          {money(fy26.transport!)}, and capital of {money(fy26.capital!)}. Those three sum
          to the total exactly.
        </Insight>
        <Insight n={2} headline={
          <>It is not apportioned among member towns by enrollment. It is Chapter&nbsp;70&rsquo;s
            local contribution, split between the town&rsquo;s two districts by foundation
            budget.</>}>
          DESE publishes both halves and the district reprinted DESE&rsquo;s own
          apportionment sheet: FY{String(d.ledger_fy).slice(2)} foundation enrollment{' '}
          {last.lps_fe.toLocaleString()} for Lunenburg Public Schools and {last.mt_fe} for
          Montachusett, foundation budgets {money(last.lps_fb)} and {money(last.mt_fb)},
          each district&rsquo;s share of the town&rsquo;s foundation{' '}
          {pct2(1 - last.fb_share)} and {pct2(last.fb_share)}, required contribution{' '}
          {money(last.lps_rlc)} and {money(last.mt_rlc)}.
        </Insight>
        <Insight n={3} headline={
          <>So a child moving to Monty Tech does not raise the town&rsquo;s obligation. It
            moves part of it from one line to the other.</>}>
          The town&rsquo;s total required contribution is the lesser of its combined effort
          yield &mdash; property wealth and resident income &mdash; and a statutory cap on
          the local share of its foundation budget. The wealth figure is the lower one, and
          therefore the binding one, in all {W.years} years DESE publishes. Enrollment never
          enters the town-wide total. What it changes is the split: Monty Tech&rsquo;s share
          went from {pct2(first.rlc_share)} in {fy(first.fy)} to {pct2(last.rlc_share)}.
        </Insight>
        <Insight n={4} headline={
          <>A Monty Tech pupil carries about half again the foundation budget of a
            Lunenburg one, which is why the money share runs ahead of the head share.</>}>
          In {fy(last.fy)} the state&rsquo;s foundation budget is{' '}
          {money(last.mt_fb_per_pupil)} for each Lunenburg pupil at Monty Tech and{' '}
          {money(last.lps_fb_per_pupil)} for each one in Lunenburg&rsquo;s own schools
          &mdash; a ratio of {H.foundation_ratio.toFixed(2)}. Monty Tech is{' '}
          {pct2(last.fe_share)} of the town&rsquo;s foundation enrollment and{' '}
          {pct2(last.fb_share)} of its foundation budget and of its bill.
        </Insight>
        <Insight n={5} headline={
          <>The town&rsquo;s own five-year forecast of this line missed{' '}
            {fy(F.actual_fy)} by {money(F.miss)}.</>}>
          A {F.board} packet in {F.date} projected the assessment forward at{' '}
          {pct1(F.rate)} a year, reaching {cash(F.projected)} in {fy(F.actual_fy)}. The
          actual figure is {money(F.actual)} &mdash; {pct1(F.miss_pct)} higher. The line
          was being forecast as an ordinary cost escalator; the thing driving it is a state
          contribution formula, which over the same span compounded at{' '}
          {pct1(F.required_cagr)} a year.
        </Insight>
        <Insight n={6} headline={
          <>What the town is billed is not what the district spends, and the gap is
            Chapter&nbsp;70.</>}>
          Monty Tech&rsquo;s {fy(dist.fy)} budget is {money(dist.budget)}. Chapter 70 aid
          paid directly to the district covers {pct1(dist.ch70_share)} of it; assessments on
          all eighteen member towns together cover {pct1(dist.assessment_share)}.
          Lunenburg&rsquo;s {money(dist.lunenburg)} is {pct2(dist.lunenburg_of_budget)} of
          the district&rsquo;s budget while Lunenburg is{' '}
          {pct2(dist.lunenburg_fe_share)} of its foundation enrollment.
        </Insight>
      </div>

      {/* --------------------------------------------------------- 2. THE BILL, IN PARTS */}
      <H2 id="parts">The bill, and the four parts it is made of</H2>
      <Parts rows={partRows} />
      <Span>
        {partRows.length} years &mdash; every year in this archive where the split is
        published. Bonds are zero in all of them.
      </Span>
      <TableTwin
        caption="the assessment, year by year"
        head={['FY', 'required minimum', 'transport & operating', 'capital', 'total',
               'above the minimum', 'state-set share']}
        mark={r => r[0] === fy(d.ledger_fy)}
        rows={d.assessment.map(a => [
          fy(a.fy),
          a.required === null ? '—' : money(a.required),
          a.transport === null ? 'not stated' : money(a.transport),
          a.capital === null ? 'not stated' : money(a.capital),
          money(a.total),
          a.above_minimum === undefined ? '—' : money(a.above_minimum),
          a.required_share === undefined ? '—' : pct1(a.required_share),
        ])}
        note={<>
          {fy(d.ledger_fy)} is bold because it is the one row that comes out of an
          accounting system. Rows marked &ldquo;not stated&rdquo; are years where only the
          total is on the record.
        </>}
      />
      <Body>
        Three years here have two documents behind them and the page prints both.{' '}
        {fy(2024)}: the district assessed {money(M.fy24_district)} and the Town&rsquo;s
        budget book records {cash(M.fy24_town)} expended. {fy(d.ledger_fy)}: the
        district&rsquo;s book, the Town&rsquo;s budget book and the Town&rsquo;s MUNIS
        ledger all say {money(d.ledger.original)}, to the cent. {fy(H.next_fy)}: the
        district says {money(M.fy27_district)} and the Town&rsquo;s budget book says{' '}
        {money(M.fy27_town)} in all three of its scenarios &mdash; {money(M.fy27_gap)}{' '}
        apart, with neither document acknowledging the other. The {fy(2025)} line was
        appropriated at {money(M.fy25_budgeted)} and came in at {money(M.fy25_actual)},{' '}
        {money(-M.fy25_gap)} under.
      </Body>
      <NotShown>
        The {fy(2025)} split, or the split in any of the {CM.n} annual-report years. Only
        three years in this archive publish the four parts and one more states them in
        prose at a meeting. For every other year the{' '}
        {pct1(CM.min_pct)}&ndash;{pct1(CM.max_pct)} sitting above the state minimum cannot
        be attributed to transportation, to capital or to debt &mdash; and those three
        behave nothing alike, since one tracks a busing contract, one is voted annually and
        one is fixed until it ends.
      </NotShown>

      {/* --------------------------------------------------------- 3. HOW IT IS BUILT */}
      <H2 id="how">How the assessment is built</H2>
      <Body>
        The district states its own method and Lunenburg printed it, in the{' '}
        {methodFig.title}:
      </Body>
      <div className="card p-4 mt-4 max-w-2xl">
        <p className="text-[14.5px] leading-relaxed whitespace-pre-line font-mono">
          {methodFig.row.split(' · ').join('\n')}
        </p>
        <p className="text-[12px] mt-3" style={{ color: 'var(--text-muted)' }}>
          {methodFig.text.split('/').pop()} line {methodFig.line} &middot;{' '}
          <a className="underline" style={{ color: 'var(--series-cost)' }}
            href={abs(methodFig.docs_url)}>the document</a>
        </p>
      </div>
      <Body>
        and the two ratios, on the same page: the operating ratio is{' '}
        <em>{opFig.row.split(' · ').pop()}</em> The capital ratio is{' '}
        <em>{capFig.row.split(' · ').pop()}</em>
      </Body>
      <Body>
        So two of the four parts <em>are</em> apportioned among member towns by enrollment
        share &mdash; but they are the small two. The large one is the state&rsquo;s.
      </Body>
      <Body>
        The district also publishes the split, in full, for every one of its eighteen
        member towns and in the same book every year: foundation enrollment, foundation
        budget, required minimum contribution, transportation, capital and bonds, beside
        the prior year&rsquo;s figure. That is why this page can decompose the bill at all,
        and it is more than the town&rsquo;s own budget documents show about any other
        assessment they carry.
      </Body>

      <H3>The money share against the head share</H3>
      <Shares rows={shareRows} />
      <Span>
        {d.required.length} years, {fy(d.first_fy)} to {fy(d.last_fy)}
      </Span>
      <TableTwin
        caption="Lunenburg's required contribution, split between its two districts"
        head={['FY', 'Monty Tech pupils', 'foundation budget', 'required contribution',
               'share of the bill', 'share of the pupils', 'foundation per pupil']}
        mark={r => r[0] === fy(d.ledger_fy)}
        rows={d.required.map(r => [
          fy(r.fy), r.mt_fe, money(r.mt_fb), money(r.mt_rlc),
          pct2(r.rlc_share), pct2(r.fe_share), money(r.mt_fb_per_pupil),
        ])}
        note={<>
          Every figure in this table is a subtraction: the town&rsquo;s column in
          DESE&rsquo;s Chapter&nbsp;70 workbook, minus the Lunenburg school district&rsquo;s.
          It is checked below.
        </>}
      />

      <H3>Why the subtraction can be trusted</H3>
      <Body>
        The required-contribution series is derived rather than published, so it is checked
        rather than asserted. Two ways.
      </Body>
      <Body>
        <strong>Against DESE&rsquo;s own apportionment sheet</strong>, which the district
        reprinted in its {partsFig.title}: {d.printed_apportionment.fields} published
        fields for FY{String(d.printed_apportionment.fy).slice(2)} &mdash; enrollment,
        foundation budget, share and required contribution, for both districts and the town
        &mdash; and every one agrees with the subtraction to the dollar. The sheet prints
        the share as {d.printed_apportionment.printed_share_pct.toFixed(2)}%; the
        subtraction gives {d.printed_apportionment.derived_share_pct.toFixed(2)}%.
      </Body>
      <TableTwin
        caption="and against what was said at public meetings"
        head={['FY', 'what was stated', 'stated', 'derived here', 'where']}
        rows={d.corroboration.map(c => [
          fy(c.fy), c.what,
          c.field === 'mt_fe' ? String(c.stated) : money(c.stated),
          c.field === 'mt_fe' ? String(c.derived) : money(c.derived),
          `${c.board}, ${c.date}`,
        ])}
        note={<>
          Five figures, three meetings, three fiscal years, all matching to the dollar. The
          build fails if one stops.
        </>}
      />
      <Body>
        The share identity is measured rather than assumed: Monty Tech&rsquo;s share of the
        town&rsquo;s required contribution equals its share of the town&rsquo;s foundation
        budget to a tenth of a basis point in {A.exact} of the {A.years} years published.
        The exception is {fy(A.worst_fy ?? 0)}, off by{' '}
        {Math.abs(A.worst_gap_pp ?? 0).toFixed(2)} points. And that the town&rsquo;s total
        is wealth-bound rather than enrollment-bound is measured too: DESE&rsquo;s target
        local contribution equals its combined effort yield in every one of those{' '}
        {W.years} years, meaning the statutory cap never binds.
      </Body>
      <NotShown>
        <strong>What the regional agreement says.</strong> A budget book states current
        practice; the agreement is what binds it, and it is not in this archive. It is the
        document that would say whether those ratios can be changed, how bonds are
        apportioned and over what term, and what withdrawing from the district would
        involve. Asked at the Finance Committee whether the agreement was indefinite or
        could be renegotiated, the Superintendent-Director said he believed it was ongoing
        and that amendments were very rare &mdash; quoted below. A recollection at a meeting
        is not the instrument.
      </NotShown>

      {/* ------------------------------------------------------------- 4. THE LONG SERIES */}
      <H2 id="series">The long series, and which parts of it are established</H2>
      <AssessmentSeries rows={series} />
      <Span>
        {series.length} years, {fy(series[0].fy)} to {fy(series[series.length - 1].fy)}
        {' '}&mdash; one established line, {parts.length + 1} documented totals, and{' '}
        {CM.n} figures that fail their own reconciliation
      </Span>
      <TableTwin
        caption="the annual town reports, against the derived state minimum"
        head={['FY', 'annual report', 'state minimum, derived', 'above it', 'status',
               'edition, page']}
        rows={usable.map(c => [
          fy(c.fy), money(c.value!), money(c.required!),
          signedPct(c.over_pct!), c.status, `${c.edition} p${c.page}`,
        ])}
        note={<>
          Every one of these carries <code>{usable[0].status}</code> or{' '}
          <code>no check</code>: the extractor&rsquo;s own reconciliation, against the
          report&rsquo;s printed totals, failing. CLAUDE.md forbids aggregating across{' '}
          <code>status</code>, so these are candidates and not established figures.
        </>}
      />
      <Body>
        <strong>What this cross-check is and is not.</strong> Every candidate sits above an
        independently derived figure by a margin consistent with the transportation and
        capital assessments &mdash; the same band the documented years show, and the{' '}
        {fy(d.ledger_fy)} ledger figure sits {pct1(CM.ledger_over_pct)} above its own
        minimum. That is evidence about the <em>shape</em> of the series. It is not evidence
        that any individual value is right, and it cannot be: two wrong numbers can stand in
        the same ratio as two right ones.
      </Body>
      <Body>
        The {fy(outlier.fy)} outlier &mdash; {signedPct(outlier.over_pct!)}, where every
        other year is at least {pct1(Math.min(...usable.filter(c => c.fy !== outlier.fy)
          .map(c => c.over_pct!)))} &mdash; has a documented cause and it is not a defect in
        the extract. A Special Town Meeting reduced the assessment mid-year, and the Town
        Manager told the Finance Committee so at the time. A certified assessment can move
        downward after Town Meeting votes it.
      </Body>
      {notUsable.length > 0 && (
        <Body>
          {notUsable.map(c => fy(c.fy)).join(', ')} is not read here at all. Its row exists
          and its page <strong>states no identity that fixes which printed column is
          which</strong>, so <code>v1</code> there is an ordinal rather than a column name.
          The {fy(notUsable[0].fy)} figure in the table above comes from the district&rsquo;s
          own budget book instead.
        </Body>
      )}
      <Body>
        <code>report_monty_tech</code> is not used on this page at all. Its{' '}
        {d.report_monty_tech.rows} rows are Monty Tech&rsquo;s own budget reprinted inside
        the {d.report_monty_tech.editions.join(', ')} annual town report; its{' '}
        <code>column_meaning</code> is empty and its <code>status</code> is{' '}
        <code>no check</code>, so <code>v1</code> there is the first column of that page
        that held figures and not a column name. Its label column has also absorbed the
        first printed figure. The generator refuses to run if that table ever silently
        acquires a column meaning.
      </Body>

      {/* ------------------------------------------------------------- 5. THE FORECAST */}
      <H2 id="forecast">What the town expected this line to do</H2>
      <Forecast rows={forecastRows} rate={F.rate} />
      <Span>
        {F.series.length} projected years from a {F.board} packet dated {F.date}, against
        what the state formula actually did
      </Span>
      <TableTwin
        caption="the projection, and the figure that was driving the line"
        head={['FY', 'projected at ' + pct1(F.rate) + ' a year', 'state minimum, actual',
               'difference']}
        mark={r => r[0] === fy(F.actual_fy)}
        rows={F.series.map(s => [
          fy(s.fy), cash(s.projected),
          s.required === null ? '—' : money(s.required),
          s.required === null ? '—' : money(s.required - s.projected),
        ])}
        note={<>
          The projected column is quoted from the packet itself:{' '}
          <a className="underline" style={{ color: 'var(--series-cost)' }}
            href={abs(F.cite)}>our copy</a> &middot;{' '}
          <a className="underline" style={{ color: 'var(--series-cost)' }}
            href={F.town}>the town&rsquo;s</a>. By {fy(F.actual_fy)} the state minimum
          alone had passed the projected total.
        </>}
      />
      <H3>What would you have had to see, and when</H3>
      <Body>
        DESE publishes the apportionment sheet this page derives &mdash; foundation
        enrollment, foundation budget and required contribution for each of a town&rsquo;s
        districts &mdash; in the same workbook and at the same time as the Chapter&nbsp;70
        aid figure the town already reads every January. The line that would have shown this
        coming is the town&rsquo;s required local contribution against the school
        district&rsquo;s: the difference between them <em>is</em> the Monty Tech minimum,
        and it grew at {pct1(F.required_cagr)} a year over the span the packet projected at{' '}
        {pct1(F.rate)}. Nothing had to be requested from anybody.
      </Body>
      <NotShown>
        That the projection was wrong to use {pct1(F.rate)}. It is the same assumption the
        town applied to its own school department in that packet, and for a line the town
        appropriates it is a reasonable one. What the arithmetic shows is that this line is
        not that kind of line &mdash; not that anybody should have known it was not.
      </NotShown>

      {/* ------------------------------------------------------------- 6. THE STUDENTS */}
      <H2 id="students">Where the town&rsquo;s children actually are</H2>
      <Students rows={studentRows} />
      <Span>
        {d.students.length} years, {fy(d.students_meta.first_fy)} to{' '}
        {fy(d.students_meta.last_fy)} &mdash; DESE&rsquo;s October headcount of Lunenburg
        residents, by the district they attend
      </Span>
      <TableTwin
        caption="Lunenburg residents, by where they go"
        head={['FY', 'Monty Tech', 'school choice', 'charter', 'in Lunenburg',
               'all resident', 'Monty Tech share']}
        mark={r => r[0] === fy(latestStu.fy)}
        rows={d.students.map(s => [
          fy(s.fy), s.monty_tech, s.school_choice, s.charter,
          s.in_lunenburg.toLocaleString(), s.all_resident.toLocaleString(),
          s.mt_share === null ? '—' : pct2(s.mt_share),
        ])}
      />
      <Body>
        Monty Tech is the larger of the two routes out of Lunenburg&rsquo;s own schools and{' '}
        <strong>it is not a departure</strong>. These children are reported by DESE as{' '}
        <code>Resident/Member</code> &mdash; resident members of a district Lunenburg
        belongs to. No Lunenburg vote admits or refuses any of them, and the town is
        assessed for them whether the count rises or falls. That is the opposite of school
        choice, where the receiving district opens the seats and a family applies for one.
        The count has risen in {H.rise_years} of the {H.of_years} years DESE publishes here,
        from {H.students_from} in {fy(firstStu.fy)} to {H.students_to}; the longest unbroken
        run is the {H.longest_rise} years {fy(H.longest_rise_from)} to{' '}
        {fy(H.longest_rise_to)}.
      </Body>

      <H3>Two counts of the same children, and they disagree in every year</H3>
      <Body>
        DESE publishes an October headcount of Lunenburg residents attending Montachusett,
        and a Chapter&nbsp;70 <em>foundation enrollment</em> used to compute the assessment.
        For {fy(latestCount.fy)} they are {latestCount.headcount} and{' '}
        {latestCount.foundation}. Across the overlapping years the difference runs from{' '}
        {Math.abs(H.count_gap_min)} below to {H.count_gap_max} above, with no consistent
        sign. One documented mechanism puts children into the assessment who are not at
        Monty Tech: the district&rsquo;s business director told the Finance Committee in
        March 2022 that four Lunenburg students attending trade programmes at Leominster and
        Nashoba become part of the Monty Tech assessment. That explains a difference in one
        direction and not the years running the other way.
      </Body>
      <TableTwin
        caption="the two counts"
        head={['FY', 'October headcount', 'foundation enrollment', 'difference']}
        mark={r => r[0] === fy(latestCount.fy)}
        rows={d.counts.map(c => [
          fy(c.fy), c.headcount, c.foundation,
          c.difference > 0 ? `+${c.difference}` : String(c.difference),
        ])}
      />
      <Body>
        <strong>So every per-student figure has to name its denominator.</strong> The
        district&rsquo;s own budget book prints {money(M.district_per_pupil)} for{' '}
        {fy(d.ledger_fy)}, dividing the assessment by the foundation enrollment of{' '}
        {H.foundation}. Dividing by DESE&rsquo;s October headcount of {H.students} gives{' '}
        {money(H.per_student)}. Both are correct arithmetic on different counts.
      </Body>
      <NotShown>
        <p>
          <strong>Why the count has risen.</strong> A count is the outcome of families
          applying <em>and</em> of Monty Tech admitting, and the lottery exists precisely
          because more apply than there are places. Asked at the Finance Committee how many
          Lunenburg students had been turned away, the district&rsquo;s business manager
          said she was unsure of the exact number.
        </p>
        <p className="mt-3">
          <strong>And do not subtract these per-pupil figures from Lunenburg&rsquo;s own.</strong>{' '}
          {money(M.district_per_pupil)} and {money(H.per_student)} are what the town is
          billed for a child. The per-pupil figure on{' '}
          <a className="underline" style={{ color: 'var(--series-cost)' }}
            href="/what-other-districts-spend">what other districts spend</a> is what DESE
          reports Lunenburg Public Schools spending per pupil from <em>all funds</em> &mdash;
          grants, revolving funds, school choice receipts, and town-paid insurance and
          retirement attributed to the schools. The difference between the two is two
          definitions, not a saving: the assessment has no grants and no direct
          Chapter&nbsp;70 in it, because those are on Monty Tech&rsquo;s revenue side.
        </p>
      </NotShown>

      {/* ---------------------------------------------------- 7. RULE 11 — BILL VS COST */}
      <H2 id="cost">The bill is not the cost</H2>
      <Body>
        The assessment is what Lunenburg is <strong>billed</strong>. It is not what
        educating those children costs, and the difference is mostly Chapter&nbsp;70 aid
        paid to the regional district directly &mdash; money that never touches a Lunenburg
        budget line and never appears in a Lunenburg vote.
      </Body>
      <TableTwin
        caption="Monty Tech's own budget, and what pays for it"
        head={['FY', 'district budget', 'Chapter 70', 'all 18 assessments', 'everything else',
               'Lunenburg’s assessment', 'of the budget', 'of the pupils']}
        mark={r => r[0] === fy(dist.fy)}
        rows={d.district.map(r => [
          fy(r.fy), money(r.budget),
          `${money(r.ch70)} (${pct1(r.ch70_share)})`,
          `${money(r.all_assessments)} (${pct1(r.assessment_share)})`,
          pct1(r.other_share),
          money(r.lunenburg), pct2(r.lunenburg_of_budget), pct2(r.lunenburg_fe_share),
        ])}
        note={<>
          Read from {distFig.title}, line {distFig.line}. The three assessment components
          the district prints sum to the total it prints, and the build fails if they stop.
        </>}
      />
      <Body>
        Lunenburg is {pct2(dist.lunenburg_fe_share)} of the district&rsquo;s foundation
        enrollment and pays {pct2(dist.lunenburg_of_budget)} of its budget. Both are true and
        neither is a discount: the assessment is a share of what is left after
        Chapter&nbsp;70 and the district&rsquo;s other revenue, and it is apportioned by a
        wealth formula rather than by heads.
      </Body>
      <NotShown>
        What the district spends over time, or what a Lunenburg place there costs. This
        archive holds two of the district&rsquo;s own budget books &mdash;{' '}
        {fy(2024)} and {fy(H.next_fy)} &mdash; and no series, no year before {fy(2024)},
        and no all-funds figure reported after a year closed. So the bill can be tracked
        and the cost cannot.
      </NotShown>

      {/* ---------------------------------------------------------- 8. WHAT WAS SAID */}
      <H2 id="said">What was said about this, in public</H2>
      <Body>
        The Finance Committee takes a Monty Tech budget presentation in March in almost
        every year, and those meetings are where most of what is known about this line comes
        from.
      </Body>
      <div className="grid gap-4 mt-6"
        style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 22rem), 1fr))' }}>
        {d.said.map(q => <Quote key={q.key} q={q} />)}
      </div>
      <H3>What was searched, and what that covers</H3>
      <TableTwin
        caption="terms searched across the meeting archive"
        head={['term', 'documents matching']}
        rows={d.searched.map(t => [t.term, t.documents.toLocaleString()])}
        note={<>
          <strong>{d.minutes.searchable.toLocaleString()} of the{' '}
          {d.minutes.held.toLocaleString()} meeting documents this archive holds are
          searchable &mdash; {pct1(d.minutes.searchable_share)}.</strong> The rest are image
          scans awaiting OCR and a handful that hold no text at all. An empty result is
          therefore <em>unproven</em>, not disproven. Search them yourself at{' '}
          <a className="underline" style={{ color: 'var(--series-cost)' }}
            href={abs('/minutes/find/')}>/minutes/find/</a>.
        </>}
      />

      {/* ------------------------------------------------- 9. WHAT IS NOT ESTABLISHED */}
      <H2 id="not-established">What this page does not establish</H2>
      <ul className="mt-5 space-y-3 max-w-3xl">
        {d.not_established.map(t => (
          <li key={t} className="text-[14.5px] leading-relaxed pl-4"
            style={{ color: 'var(--text-secondary)', borderLeft: '3px solid var(--axis)' }}>
            {t}
          </li>
        ))}
      </ul>

      <H2 id="gaps">What we cannot answer, and the document that would</H2>
      <Body>
        Each of these is a row in the register at{' '}
        <a className="underline" style={{ color: 'var(--series-cost)' }}
          href={abs('/what-we-cannot-answer')}>/what-we-cannot-answer</a>, so it is visible
        to anybody who never reads this page.
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

      {/* ------------------------------------------------------------- 10. THE SOURCES */}
      <H2 id="sources">Where every figure comes from</H2>
      <Body>
        Three data sources, and six figures read off a printed page. The second kind carries
        its coordinate &mdash; the file, the line, and the row as printed &mdash; because a
        figure quoted without one is a rendering being passed off as an observation.
      </Body>
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
              {doc.publisher} &middot; {kb(doc.bytes)}
              {doc.url && <> &middot;{' '}
                <a className="underline" href={doc.url}>the publisher&rsquo;s copy</a></>}
              <br />sha256 {doc.sha256}
            </p>
          </div>
        ))}
      </div>
      <H3>Figures read off a printed page, with their coordinates</H3>
      <div className="grid gap-4 mt-5"
        style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 26rem), 1fr))' }}>
        {Object.values(d.figures).map(f => (
          <div key={f.key} className="card p-4">
            <p className="text-[15px] font-bold leading-snug">{f.title}</p>
            <p className="text-[13.5px] leading-relaxed mt-2"
              style={{ color: 'var(--text-secondary)' }}>{f.what}</p>
            <p className="text-[12.5px] leading-relaxed mt-2.5 font-mono break-words"
              style={{ color: 'var(--text-primary)' }}>{f.row}</p>
            <p className="text-[12px] mt-2.5" style={{ color: 'var(--text-muted)' }}>
              <strong>What kind of document:</strong> {f.basis}
            </p>
            <p className="text-[11.5px] mt-2 break-all" style={{ color: 'var(--text-muted)' }}>
              line {f.line}{f.lines > 1 ? `–${f.line + f.lines - 1}` : ''} of{' '}
              <a className="underline" style={{ color: 'var(--series-cost)' }}
                href={abs(f.text_url)}>{f.text.split('/').pop()}</a> &middot;{' '}
              <a className="underline" style={{ color: 'var(--series-cost)' }}
                href={abs(f.docs_url)}>the document</a> &middot; {kb(f.bytes)}
              <br />sha256 {f.sha256}
            </p>
          </div>
        ))}
      </div>
      <Body>
        The rows behind every chart are published at{' '}
        <a className="underline" style={{ color: 'var(--series-cost)' }}
          href={abs('/data/monty-tech.json')}>/data/monty-tech.json</a>, written by{' '}
        <code>scripts/build_monty_tech.py</code>, which refuses to write if any assertion in
        it stops holding. The long-form analysis is at{' '}
        <a className="underline" style={{ color: 'var(--series-cost)' }}
          href={abs('/docs/analyses/monty-tech.md')}>/docs/analyses/monty-tech.md</a>. Where
        the town&rsquo;s children actually are, counted rather than costed, is at{' '}
        <a className="underline" style={{ color: 'var(--series-cost)' }}
          href="/where-students-go-instead">where students go instead</a>, and the formula
        that sets {pct1(H.required_share)} of this bill is at{' '}
        <a className="underline" style={{ color: 'var(--series-cost)' }}
          href="/why-we-only-get-minimum-aid">why we only get minimum aid</a>.
      </Body>
      <Legend items={[
        { hue: SOLID, label: 'an established figure, throughout' },
        { hue: SOFT, label: 'a candidate off a check-failed extract', hollow: true },
        { hue: MINIMUM, label: 'the state-set minimum contribution' },
        { hue: TRANSPORT, label: 'transportation and other operating' },
        { hue: CAPITAL, label: 'capital' },
      ]} />
      <p className="text-[12.5px] mt-6 max-w-2xl" style={{ color: 'var(--text-muted)' }}>
        {said('aligned') ? '' : ''}
        Nothing on this page is typed into it. {d.about}
      </p>
    </Shell>
  )
}
