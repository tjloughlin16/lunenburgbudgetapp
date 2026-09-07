import { useEffect, useState } from 'react'
import { usd } from '../model/engine'
import {
  BothSides, TransportSwap, Coaching, CostByCategory, CostPerSport, Participation,
  WhoPays, FundCash, FeeLadder, fy, share, FUND, CAT_COLOUR, NEUTRAL,
  type SideRow, type TransportRow, type CoachRow, type CatRow, type SportRow,
  type PartRow, type MixRow, type FlowRow, type FeeRow,
} from '../components/AthleticsCharts'

/** Athletics, drilled in: both sides of the money, charted.
 *
 *  WHAT THIS PAGE IS. `sources/analyses/athletics.md` (7,300 words) and
 *  `sources/analyses/athletics-ledger.md` (4,300) did this reasoning first and at length.
 *  This is the same material with the series drawn. It neither redoes the argument nor
 *  contradicts it — but every figure on it is RECOMPUTED from the database at build time
 *  by `scripts/build_athletics_charts.py`, and where a recomputation differs from a
 *  sentence in either report the difference is shown, with which one is which. Three
 *  differ. They are in `d.recomputed` and rendered, not buried.
 *
 *  WHY ATHLETICS, WHEN IT IS 1.7% OF THE BUDGET. By rule 4 it is not a driver of the gap
 *  and never will be. It is here because it is the ONE programme where both sides of the
 *  money are visible: the town appropriates, the fee-funded revolving fund takes in fees,
 *  and the fund spends. So rule 11 — a budget line is net, and it is not what the thing
 *  costs — can be MEASURED here rather than described. It is also the control case on the
 *  traceability ladder: `fund_1301_cash_journal` is the only transaction-level data in
 *  the archive, 277 postings out of 61 funds.
 *
 *  THREE QUANTITIES, NEVER ADDED. An appropriation, the fund's spending and the fund's
 *  revenue are three different things. A published figure of "$335,856 through the
 *  revolving fund" was once the second plus the third. The generator refuses to write if
 *  a revenue row reaches a spending total, and no chart here stacks revenue on spending.
 *
 *  RULE 7A. The page opens with what it establishes. The method, the caveats and the
 *  registry of what cannot be answered come after the reader has seen the thing.
 *
 *  RULE 7. A figure computed from the data is a fact; an explanation for why it moved is
 *  a hypothesis. Both halves are written on every section, and the second is labelled.
 *
 *  NO D1 AT PAGE LOAD. One static file. */

type Payload = {
  generated_by: string
  source: string
  coverage: {
    history_years: number[]; cost_years: number[]; part_years: number[]
    mix_years: number[]; fund_years: number[]
    postings: number; sports: number; fee_rows: number
    disbursements: number; disbursements_named: number
  }
  both_sides: SideRow[]
  transport: TransportRow[]
  coaching: (CoachRow & { fund: number | null })[]
  categories: CatRow[]
  category_order: string[]
  by_sport: SportRow[]
  participation: PartRow[]
  participation_totals: {
    fy: number; total: number; hs: number; ms: number
    cost: number | null; per_participation: number | null
  }[]
  negatives: { fy: number; season: string; level: string; sport: string; athletes: number }[]
  fee_mix: MixRow[]
  count_columns: string[]
  fees: {
    fy: number; school_year: string; level: string; item: string; amount: number
    set_on: string; source: string; source_ref: string; verified: string
  }[]
  fee_headline: FeeRow[]
  fee_check: {
    level: string; net: number; participations: number; per_participation: number
    stated_fee: number | null; under_top_tier: boolean
  }[]
  fund_flow: FlowRow[]
  fund_sources: { fy: number; src: string; meaning: string; amount: number; postings: number }[]
  memo_entries: {
    fy: number; eff: string; post: string; journal: string; ref1: string
    reference: string; amount: number; comments: string
  }[]
  memo_total: number
  compare: {
    fy: number
    rows: { category: string; workbook: number; general: number; outside: number }[]
    workbook_total: number; general_total: number; share: number
    unmatched: { item: string; amount: number }[]; unmatched_total: number
  }
  fy26_fund: { revenue: number; spending: number; appropriation: number; all_in: number }
  recomputed: {
    what: string; ours: number | null; published: number | null; boolean?: boolean
    where: string; why: string
  }[]
  gaps: { side: string; what: string; why: string }[]
  related: {
    id: string; title: string; why: string; words: number; updated: string
    url: string; pdf: string | null
  }[]
}

function H2({ id, children }: { id?: string; children: React.ReactNode }) {
  return (
    <h2 id={id} className="text-2xl font-bold tracking-tight mt-14 mb-3 max-w-3xl
                           scroll-mt-[calc(var(--header-h)+1rem)]">{children}</h2>
  )
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
      <div className="text-3xl font-bold tracking-tight" style={tone ? { color: tone } : undefined}>
        {value}
      </div>
      <div className="text-[13px] leading-snug mt-1 max-w-[15rem]"
        style={{ color: 'var(--text-secondary)' }}>{children}</div>
    </div>
  )
}

/** The half of a section that says what the data does NOT establish. A distinct shape on
 *  purpose: here the limit is as load-bearing as the finding, and a caveat set in the same
 *  grey as the paragraph above it gets skimmed. */
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

/** An insight, in the shape rule 7b asks for: a claim a reader could repeat, the figure
 *  it rests on, and the query that produced it. */
function Insight({ n, claim, figure, tone, children }: {
  n: number; claim: React.ReactNode; figure: string; tone?: string; children: React.ReactNode
}) {
  return (
    <div className="card p-5">
      <div className="flex items-baseline gap-3">
        <span className="text-[11px] font-bold tabular-nums"
          style={{ color: 'var(--text-muted)' }}>{String(n).padStart(2, '0')}</span>
        <span className="text-2xl font-bold tracking-tight tnum"
          style={tone ? { color: tone } : undefined}>{figure}</span>
      </div>
      <p className="text-[15.5px] font-semibold leading-snug mt-2">{claim}</p>
      <div className="text-[13.5px] leading-relaxed mt-2"
        style={{ color: 'var(--text-secondary)' }}>{children}</div>
    </div>
  )
}

export function AthleticsMoney() {
  const [d, setD] = useState<Payload | null>(null)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    let live = true
    fetch('/data/athletics.json')
      .then(r => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then(j => { if (live) setD(j) })
      .catch(e => { if (live) setErr(String(e)) })
    return () => { live = false }
  }, [])

  if (err) {
    return (
      <div className="mx-auto max-w-6xl px-5 pt-14 pb-16">
        <h1 className="text-3xl font-bold tracking-tight">Athletics, both sides of the money</h1>
        <div className="card p-5 mt-8" style={{ borderLeft: '4px solid var(--status-warning)' }}>
          <p className="text-[15px] font-bold mb-1">The series did not load</p>
          <p className="text-[13.5px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
            {err}. Nothing on this page is typed into it, so with the file missing there is
            nothing to show rather than something stale. The written analyses are at{' '}
            <a className="underline" style={{ color: 'var(--series-cost)' }}
              href="/docs/analyses/athletics.md">/docs/analyses/athletics.md</a> and{' '}
            <a className="underline" style={{ color: 'var(--series-cost)' }}
              href="/docs/analyses/athletics-ledger.md">/docs/analyses/athletics-ledger.md</a>.
          </p>
        </div>
      </div>
    )
  }

  if (!d) {
    return (
      <div className="mx-auto max-w-6xl px-5 pt-14 pb-16">
        <h1 className="text-3xl font-bold tracking-tight">Athletics, both sides of the money</h1>
        <p className="mt-4 text-[15px]" style={{ color: 'var(--text-muted)' }}>
          Loading the measured series&hellip;
        </p>
      </div>
    )
  }

  const fy26 = d.both_sides[d.both_sides.length - 1]
  const t24 = d.transport.find(r => r.fy === 2024)!
  const t25 = d.transport.find(r => r.fy === 2025)!
  const t26 = d.transport.find(r => r.fy === 2026)!
  const flow25 = d.fund_flow.find(r => r.fy === 2025)!
  const partFirst = d.participation_totals[0]
  const partLast = d.participation_totals[d.participation_totals.length - 1]
  const partChange = (partLast.total - partFirst.total) / partFirst.total
  const hsFees = d.fee_headline.filter(r => r.level === 'HS').sort((a, b) => a.fy - b.fy)
  /** The fee series is measured over EXACTLY the years participation is measured over.
   *  It runs a year further — FY27's rate is published — and comparing a three-year
   *  headcount to a four-year price is the kind of mismatched span this project keeps
   *  catching in its own prose. The later year is stated separately, with its provenance. */
  const feeFirst = hsFees.find(r => r.fy === partFirst.fy)!
  const feeLast = hsFees.find(r => r.fy === partLast.fy)!
  const feeAhead = hsFees.filter(r => r.fy > partLast.fy)
  const feeChange = (feeLast.amount - feeFirst.amount) / feeFirst.amount
  const memoShare = d.memo_entries
    .filter(r => r.fy === 2025).reduce((a, r) => a + r.amount, 0) / flow25.receipts
  const unpublished = d.both_sides.filter(r => r.revolving_state === 'not published')
  const costYearFee = d.fee_headline
    .find(r => r.level === 'HS' && r.fy === d.coverage.cost_years[d.coverage.cost_years.length - 1])
  const perPart = d.participation_totals.filter(r => r.per_participation !== null)
  const wideSport = [...d.by_sport]
    .filter(r => r.fy === d.coverage.cost_years[d.coverage.cost_years.length - 1] && r.per_athlete)
    .sort((a, b) => (b.per_athlete ?? 0) - (a.per_athlete ?? 0))
  const dearest = wideSport[0], cheapest = wideSport[wideSport.length - 1]

  return (
    <div className="mx-auto max-w-6xl px-5 pt-14 pb-16">
      <p className="text-xs font-semibold uppercase tracking-widest mb-3"
        style={{ color: 'var(--text-muted)' }}>The money</p>
      <h1 className="text-4xl sm:text-5xl font-bold tracking-tight leading-[1.05] max-w-3xl">
        The only programme where you can see both sides of the money.
      </h1>
      <p className="mt-5 text-lg leading-relaxed max-w-2xl"
        style={{ color: 'var(--text-secondary)' }}>
        The town appropriates. Families pay a fee into a separate fund. That fund spends.
        For every other line in the budget you can see the first of those three and
        nothing else &mdash; which is why what athletics shows about the gap between an
        appropriation and a cost matters far beyond athletics.
      </p>

      <div className="mt-10 flex flex-wrap gap-x-12 gap-y-6">
        <Stat value={share(d.compare.share)} tone={FUND}>
          of what the district&rsquo;s own workbook says the sports cost was covered by the
          town&rsquo;s comparable budget lines in {fy(d.compare.fy)}
        </Stat>
        <Stat value={usd(fy26.all_in ?? 0)}>
          the whole {fy(fy26.fy)} athletics programme &mdash; {usd(fy26.general)} appropriated
          and {usd(fy26.revolving ?? 0)} spent by the fee-funded fund
        </Stat>
        <Stat value={usd(d.memo_total)} tone={CAT_COLOUR.Officials}>
          moved into the fund across {fy(d.memo_entries[0].fy)}&ndash;
          {fy(d.memo_entries[d.memo_entries.length - 1].fy)} on{' '}
          {d.memo_entries.length} journal entries whose whole description is{' '}
          <em>per memo</em>. We hold none of the memos
        </Stat>
        <Stat value={`${partLast.total}`}>
          participations in {fy(partLast.fy)}, from {partFirst.total} in {fy(partFirst.fy)}.
          One child in three seasons is three of these
        </Stat>
      </div>

      {/* ==================================================== 1. WHAT THIS ESTABLISHES */}
      <H2 id="insights">What this establishes</H2>
      <Body>
        Four claims a resident could repeat at a meeting. Each is recomputed from the
        database when this page is built, and each names the table it came out of.
      </Body>

      <div className="grid gap-4 mt-6 sm:grid-cols-2">
        <Insight n={1} figure={share(d.compare.share)} tone={FUND}
          claim={<>An athletics appropriation is not what athletics costs &mdash; and
            here that is a measurement, not a warning.</>}>
          In {fy(d.compare.fy)} the town&rsquo;s comparable athletics lines came to{' '}
          {usd(d.compare.general_total)} against {usd(d.compare.workbook_total)} that the
          district&rsquo;s own sport-by-sport workbook totals for the same categories.
          A further {usd(d.compare.unmatched_total)} sat on general fund lines the workbook
          does not track at all.{' '}
          <span style={{ color: 'var(--text-muted)' }}>
            <code>athletics_history</code> joined to <code>athletics_by_sport</code> on
            comparable categories, {fy(d.compare.fy)} only.
          </span>
        </Insight>

        <Insight n={2} figure={share(t24.fund_share ?? 0)} tone={CAT_COLOUR.Transportation}
          claim={<>Two-thirds of the bus bill was paid outside the town&rsquo;s budget in{' '}
            {fy(2024)}. A year later it was {share(t25.fund_share ?? 0)}.</>}>
          Athletic transportation cost {usd(t24.cost ?? 0)} in {fy(2024)}, of which the
          town&rsquo;s line carried {usd(t24.general ?? 0)}. In {fy(2025)} the cost fell to{' '}
          {usd(t25.cost ?? 0)} and the town&rsquo;s line rose to {usd(t25.general ?? 0)}.
          The {fy(2026)} line is {usd(t26.general ?? 0)}.{' '}
          <span style={{ color: 'var(--text-muted)' }}>
            <code>athletics_history</code> both sides, checked against{' '}
            <code>athletics_by_sport</code>&rsquo;s own transportation total &mdash; the two
            budget sides sum to it exactly in both years.
          </span>
        </Insight>

        <Insight n={3} figure={share(memoShare)} tone={CAT_COLOUR.Officials}
          claim={<>Most of what came into the fund in {fy(2025)} was four journal entries
            nobody outside Town Hall can read.</>}>
          {usd(d.memo_entries.filter(r => r.fy === 2025).reduce((a, r) => a + r.amount, 0))}{' '}
          of {usd(flow25.receipts)} arrived as general-journal entries described only as an
          expense adjustment made per a memo. Take them out and the year closes at{' '}
          <strong style={{ color: 'var(--status-bad)' }}>{usd(flow25.without_journals)}</strong>.
          That is arithmetic on the town&rsquo;s own rows, not a balance the town reported.{' '}
          <span style={{ color: 'var(--text-muted)' }}>
            <code>fund_1301_cash_journal</code>, <code>src = &lsquo;GEN&rsquo;</code>.
          </span>
        </Insight>

        <Insight n={4}
          figure={`${partChange >= 0 ? '+' : '−'}${Math.abs(partChange * 100).toFixed(1)}%`}
          claim={<>Participation is roughly flat over three years while the fee it pays has
            risen {Math.round(feeChange * 100)}%.</>}>
          {partFirst.total} participations in {fy(partFirst.fy)}, {partLast.total} in{' '}
          {fy(partLast.fy)}. Over exactly those years the high-school fee a first child
          pays went from {usd(feeFirst.amount)} to {usd(feeLast.amount)}
          {feeAhead.length
            ? `, and is ${usd(feeAhead[feeAhead.length - 1].amount)} in ${fy(feeAhead[feeAhead.length - 1].fy)} on a source we do not hold a copy of`
            : ''}.{' '}
          <strong>These are two measurements side by side and nothing here connects them</strong>{' '}
          &mdash; three years is not enough to see a response to a price, and the fee rose
          after most of the fall.{' '}
          <span style={{ color: 'var(--text-muted)' }}>
            <code>athletics_by_sport</code> where <code>metric = &lsquo;Total
            Athletes&rsquo;</code>, and <code>athletic_fee_schedule</code>.
          </span>
        </Insight>
      </div>

      {/* ------------------------------------------------ where we differ from the prose */}
      <div className="card p-5 mt-6" style={{ borderLeft: '4px solid var(--status-warning)' }}>
        <p className="text-[14.5px] font-bold mb-1">
          Three figures here differ from the written analyses. These are the recomputed ones.
        </p>
        <p className="text-[13.5px] leading-relaxed mb-3" style={{ color: 'var(--text-secondary)' }}>
          Every number on this page is derived from the database at build time. The reports
          are prose, and prose was true on the day it was written. Where they disagree, this
          is what the data now says &mdash; and what moved underneath it.
        </p>
        <ul className="space-y-3">
          {d.recomputed.map(r => (
            <li key={r.what} className="text-[13.5px] leading-relaxed">
              <span className="font-semibold">{r.what}.</span>{' '}
              {r.boolean || r.ours === null || r.published === null ? null : (
                <span className="tnum">
                  <strong>{r.ours < 1 ? share(r.ours) : usd(r.ours)}</strong> here,{' '}
                  {r.published < 1 ? share(r.published) : usd(r.published)} in{' '}
                  <span style={{ color: 'var(--text-muted)' }}>{r.where}</span>.{' '}
                </span>
              )}
              {r.boolean ? (
                <span style={{ color: 'var(--text-muted)' }}>{r.where}. </span>
              ) : null}
              <span style={{ color: 'var(--text-secondary)' }}>{r.why}</span>
            </li>
          ))}
        </ul>
      </div>

      {/* ============================================ 2. THE ORGANISED CATEGORICAL DATA */}
      <H2 id="both-sides">Both sides, every year either one is visible</H2>
      <Body>
        The town&rsquo;s appropriation and what the fee-funded revolving fund spent, added
        only in the years both were published. {unpublished.length} of{' '}
        {d.both_sides.length} years show no fund side at all &mdash; and that is a gap in
        the record, not a fund that spent nothing.
      </Body>
      <div className="mt-6"><BothSides rows={d.both_sides} /></div>
      <p className="text-[12px] mt-3 max-w-2xl" style={{ color: 'var(--text-muted)' }}>
        {fy(unpublished[0].fy)}&ndash;{fy(unpublished[unpublished.length - 1].fy)} is blank
        on the fund side because no document published one. {fy(2024)} and {fy(2025)} carry
        two lines only, drawn paler, and the fund certainly paid for more than two things in
        those years. So the whole-programme figure is a floor wherever it is marked{' '}
        &ldquo;&ge;&rdquo;. The fund&rsquo;s REVENUE is not on this chart at any height:
        it is a third quantity, and a published figure of &ldquo;$335,856 through the
        revolving fund&rdquo; was once revenue and spending added together.
      </p>
      <NotShown>
        <p>
          <strong>Whether the fund&rsquo;s share is stable.</strong> It is{' '}
          {share(d.both_sides.find(r => r.fy === 2019)?.fund_share ?? 0)} in {fy(2019)} and{' '}
          {share(fy26.fund_share ?? 0)} in {fy(fy26.fy)} &mdash; but there is nothing in the
          archive between them on the fund side, and <strong>two points cannot show a
          line</strong>. What did change is the composition: coaches and supplies early,
          transportation throughout, officials and uniforms by {fy(fy26.fy)}.
        </p>
      </NotShown>

      <H2 id="transport">One bill, two funds, and the year it moved</H2>
      <Body>
        Athletic transportation is the clearest case on the page, because for two years we
        can see the whole cost and how it was split. In {fy(2024)} the town&rsquo;s line was{' '}
        {usd(t24.general ?? 0)} against a {usd(t24.cost ?? 0)} bill. In {fy(2025)} the
        fund&rsquo;s share fell to {usd(t25.fund ?? 0)}.
      </Body>
      <div className="mt-6"><TransportSwap rows={d.transport} /></div>
      <NotShown>
        <p>
          <strong>Why the fund stopped paying.</strong> Three orderings fit the same rows:
          the town took the cost on because the fund could not carry it; the fund was
          relieved of it as policy and the cash consequence followed; or both follow from a
          third decision recorded in the memos. Nothing in these files distinguishes them.
        </p>
        <p className="mt-2">
          <strong>That the {fy(2026)} fund paid nothing for buses.</strong> The fund&rsquo;s
          own year-end report bundles transportation inside one line reading{' '}
          <em>purchase of service (officials, uniforms, transportation, ice time, dues)</em>,
          so the {fy(2026)} fund bar here is <em>not published separately</em> rather than
          zero.
        </p>
      </NotShown>

      <H2 id="cost">What the money actually buys</H2>
      <Body>
        The district&rsquo;s own sport-by-sport workbook is the only document that puts a
        cost against a category. Its columns sum to its own printed total to the cent in
        both years &mdash; the generator refuses to publish this chart if they stop doing
        so, because then the split would be ours rather than the document&rsquo;s.
      </Body>
      <div className="mt-6"><CostByCategory rows={d.categories} order={d.category_order} /></div>
      <p className="text-[12px] mt-3 max-w-2xl" style={{ color: 'var(--text-muted)' }}>
        Two years, {fy(d.coverage.cost_years[0])} and{' '}
        {fy(d.coverage.cost_years[d.coverage.cost_years.length - 1])} &mdash; the only years
        the workbook observes. Its two later columns are the prior year escalated 6.5% and
        are model output, not data, so they are not drawn.
      </p>

      <H2 id="coaching">Coaching, which is the biggest single thing athletics buys</H2>
      <Body>
        Three different measurements, on one axis and never added: the coaching lines in
        the town&rsquo;s budget, coaching paid by the fund in the years the fund reported
        it, and what the district&rsquo;s workbook says coaching cost.
      </Body>
      <div className="mt-6">
        <Coaching rows={d.coaching}
          workbook={d.categories.map(r => ({ fy: r.fy, amount: r.Coaches }))} />
      </div>
      <NotShown>
        <p>
          <strong>Who was on the fund&rsquo;s payroll.</strong> The cashbook shows{' '}
          {usd(Math.abs(d.fund_sources.find(r => r.fy === 2024 && r.src === 'PRJ')?.amount ?? 0))}{' '}
          of payroll run through the fund in {fy(2024)} and carries <em>no name, no
          position and no object code</em> on a payroll row. The workbook attributes{' '}
          {usd(d.categories.find(r => r.fy === 2024)?.Coaches ?? 0)} of coaching cost to the
          same year, and the general fund also carried coaching lines that year. The two do
          not add up and the ledger cannot say why.
        </p>
        <p className="mt-2">
          <strong>That a line moving means people.</strong> A budget line is dollars. It is
          never a count of coaches, and the town publishes no coaching headcount.
        </p>
      </NotShown>

      <H2 id="per-sport">What a season costs, per player</H2>
      <Body>
        The workbook prints a cost for each sport and prints a headcount beside it, and
        never divides one by the other. <strong>This division is ours.</strong> In{' '}
        {fy(dearest.fy)} it runs from {usd(dearest.per_athlete ?? 0)} a participation for{' '}
        {dearest.sport} down to {usd(cheapest.per_athlete ?? 0)} for {cheapest.sport}, against
        a first-child fee of {usd(costYearFee?.amount ?? 0)}. Across the whole programme it
        is {perPart.map(p => `${usd(p.per_participation ?? 0)} in ${fy(p.fy)}`).join(' and ')}.
      </Body>
      <div className="mt-6">
        <CostPerSport rows={d.by_sport} years={d.coverage.cost_years}
          feeLine={costYearFee?.amount ?? 0} />
      </div>
      <NotShown>
        <p>
          <strong>That the fee is meant to cover a sport&rsquo;s cost.</strong> It is not,
          and never has been: the fund pays for some categories and the town pays for
          others, and which is which has changed twice. A sport above the dashed rule is
          not a sport being subsidised more than one below it &mdash; the rule is a fee, and
          the bar is a cost, and no document maps one onto the other per sport.
        </p>
        <p className="mt-2">
          <strong>Cost per student.</strong> These are participations. One child playing
          three seasons appears three times, so nothing here divides by a number of
          children, and the town publishes no unduplicated athlete count.
        </p>
      </NotShown>

      {/* ------------------------------------------------ participation, its own subject */}
      <H2 id="participation">Who plays &mdash; on its own terms, not as a budget input</H2>
      <Body>
        Participations by season and level, for the three years the district&rsquo;s
        workbook covers. Three years is short. It is also more forward visibility than the
        boards in this town currently use, so it is drawn &mdash; with the span on the
        chart.
      </Body>
      <div className="mt-6">
        <Participation rows={d.participation} totals={d.participation_totals} />
      </div>
      <p className="text-[12px] mt-3 max-w-2xl" style={{ color: 'var(--text-muted)' }}>
        {d.negatives.length} rows in the workbook are <em>negative</em> &mdash; out-of-district
        athletes subtracted back out, {d.negatives.map(n => `${n.athletes} in ${fy(n.fy)}`).join(', ')}.
        They are counted the way the sheet counts them, which means a season total is a net
        figure and not a headcount of bodies.
      </p>
      <NotShown>
        <p>
          <strong>How many children play sports.</strong> Two town documents give 593 and{' '}
          {partLast.total} for the same year and count different things &mdash; one counts
          fee categories, the other counts participations by sport. They do not reconcile
          and must not be added. Neither publishes distinct students.
        </p>
      </NotShown>

      <H2 id="who-pays">Who pays, and who does not</H2>
      <Body>
        Every participation in the workbook falls into a fee category. These counts are
        summed from its rows: the sheet&rsquo;s own printed totals for these columns are
        dollars rather than counts, so the row sum is the only reading that means what the
        column heading says.
      </Body>
      <div className="mt-6"><WhoPays rows={d.fee_mix} columns={d.count_columns} /></div>
      <p className="text-[12px] mt-3 max-w-2xl" style={{ color: 'var(--text-muted)' }}>
        The reduced-fee columns are deliberately absent. <code>HS Red Fee</code> totals 213
        in {fy(2024)} and 662.5 in {fy(2025)} &mdash; it is dollars in one year and something
        else in the other, and a column whose meaning cannot be stated is not a column that
        may be summed. That is what the grey residual is: participations in none of the four
        countable columns.
      </p>

      <H2 id="fees">What a family pays, and when it was set</H2>
      <Body>
        The first-child fee by level and season, each figure carrying the document that set
        it. {fy(2026)}&rsquo;s high-school rate was priced at the previous year&rsquo;s
        figure on this site for months, because the source stated rates and never stated a
        year &mdash; which is why the register records the date a rate was set beside the
        rate.
      </Body>
      <div className="mt-6"><FeeLadder rows={d.fee_headline} /></div>

      <div className="card p-5 mt-6 max-w-3xl">
        <p className="text-[11px] font-semibold uppercase tracking-widest mb-2"
          style={{ color: 'var(--text-muted)' }}>What a participation actually paid, {fy(2026)}</p>
        <div className="grid gap-4 sm:grid-cols-2">
          {d.fee_check.map(f => (
            <div key={f.level}>
              <p className="text-2xl font-bold tnum">{usd(f.per_participation)}</p>
              <p className="text-[13px] leading-snug mt-1" style={{ color: 'var(--text-secondary)' }}>
                {f.level.toLowerCase()} &mdash; {usd(f.net)} of net user fees over{' '}
                {f.participations} participations, against a stated first-child fee of{' '}
                {usd(f.stated_fee ?? 0)}.{' '}
                {f.under_top_tier
                  ? 'Below the top tier, which is what a blend of full pay, reduced fees and waivers has to be.'
                  : 'ABOVE the top tier, which a blended rate cannot be — something is miscounted.'}
              </p>
            </div>
          ))}
        </div>
        <p className="text-[12px] leading-relaxed mt-4" style={{ color: 'var(--text-muted)' }}>
          Rule 11, pointing the other way. What the fund banked is already net of the
          payment processor&rsquo;s charge, so a fee model calibrated on it is not a model
          of what families were asked for.
        </p>
      </div>

      <H2 id="cashbook">The fund&rsquo;s own cashbook &mdash; the only ledger in the archive</H2>
      <Body>
        {d.coverage.postings} postings across {d.coverage.fund_years.length} years, with
        dates, warrant numbers and the clerk&rsquo;s own comments. Every other fund in the
        town &mdash; and the whole school general fund &mdash; is visible to this project
        only as a budget document restating itself. That is why this one page is the control
        case for how far the money can be followed anywhere.
      </Body>
      <div className="mt-6"><FundCash rows={d.fund_flow} /></div>
      <p className="text-[12px] mt-3 max-w-2xl" style={{ color: 'var(--text-muted)' }}>
        The chain is the town&rsquo;s, not ours: each year&rsquo;s closing cash is checked
        against the opening balance the town printed for the next, and it ties to the cent
        in all {d.coverage.fund_years.length} years. {fy(2026)} stops on 12 June and carries
        no year-end entries, so it is not a closed year.
      </p>

      <div className="card p-5 mt-6">
        <p className="text-[11px] font-semibold uppercase tracking-widest mb-3"
          style={{ color: 'var(--text-muted)' }}>
          The {d.memo_entries.length} entries, exactly as the ledger writes them
        </p>
        <div className="overflow-x-auto -mx-2 px-2">
          <table className="w-full text-[12px] tnum whitespace-nowrap">
            <thead>
              <tr style={{ color: 'var(--text-muted)' }}>
                <th className="text-left font-bold uppercase tracking-widest text-[10px] pb-1 pr-3">effective</th>
                <th className="text-left font-bold uppercase tracking-widest text-[10px] pb-1 pr-3">posted</th>
                <th className="text-left font-bold uppercase tracking-widest text-[10px] pb-1 pr-3">journal</th>
                <th className="text-left font-bold uppercase tracking-widest text-[10px] pb-1 pr-3">reference</th>
                <th className="text-right font-bold uppercase tracking-widest text-[10px] pb-1 pr-3">amount</th>
                <th className="text-left font-bold uppercase tracking-widest text-[10px] pb-1">comments</th>
              </tr>
            </thead>
            <tbody>
              {d.memo_entries.map(r => (
                <tr key={r.journal + r.eff} className="border-t" style={{ borderColor: 'var(--grid)' }}>
                  <td className="py-1 pr-3">{r.eff}</td>
                  <td className="py-1 pr-3">{r.post}</td>
                  <td className="py-1 pr-3">{r.journal}</td>
                  <td className="py-1 pr-3"><code>{r.reference}</code></td>
                  <td className="py-1 pr-3 text-right font-semibold">{usd(r.amount)}</td>
                  <td className="py-1"><code>{r.comments}</code></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="text-[12.5px] leading-relaxed mt-4" style={{ color: 'var(--text-secondary)' }}>
          Journal 1339 is effective 30 June {2025} and was posted 27 August {2025} &mdash;
          after the fiscal year closed, and after the {fy(2026)} budget was voted. That is
          the general property worth carrying away from this page: when a budget document
          prints an &ldquo;actual&rdquo; for a prior year, that figure may have been adjusted
          by a memo months afterwards, and the document will not say so.
        </p>
      </div>
      <NotShown>
        <p>
          <strong>What the entries were for.</strong> An entry raising cash in a fund and
          labelled as an expense adjustment fits at least three readings: expenses charged
          here and later moved elsewhere; a transfer in from another fund; a correction of
          charges posted to the wrong account. Those are different facts about the world and
          identical facts on the page.
        </p>
        <p className="mt-2">
          <strong>That the fund was overdrawn on any date.</strong> Ordering backdated rows
          by effective date puts it below zero for months, but that ordering is ours. MUNIS
          backdates, and rows sharing an effective date have no defined order.
        </p>
        <p className="mt-2">
          <strong>Who was paid.</strong> The vendor field is populated on receipts and empty
          on {d.coverage.disbursements - d.coverage.disbursements_named} of{' '}
          {d.coverage.disbursements} disbursement rows. Warrant numbers are there, so the
          warrants themselves would name the carriers.
        </p>
      </NotShown>

      {/* ============================================================= 3. RAW AND CONTEXT */}
      <H2 id="rule-11">{fy(d.compare.fy)}, category by category &mdash; rule 11 as a measurement</H2>
      <Body>
        The comparison the whole page turns on, taking only the categories the workbook and
        the budget both name. Everything outside them is reported separately rather than
        folded in.
      </Body>
      <div className="card p-5 mt-6">
        <table className="stack w-full text-xs tnum">
          <caption className="sr-only">
            {fy(d.compare.fy)} athletics: the district&rsquo;s workbook against the
            town&rsquo;s comparable budget lines
          </caption>
          <thead>
            <tr className="text-left" style={{ color: 'var(--text-muted)' }}>
              <th className="font-semibold py-1.5">Category</th>
              <th className="font-semibold py-1.5 text-right">Workbook cost</th>
              <th className="font-semibold py-1.5 text-right">Town budget</th>
              <th className="font-semibold py-1.5 text-right">Outside the town&rsquo;s budget</th>
            </tr>
          </thead>
          <tbody>
            {d.compare.rows.map(r => (
              <tr key={r.category} className="border-t" style={{ borderColor: 'var(--grid)' }}>
                <td className="rowhead py-1.5 font-semibold">{r.category}</td>
                <td data-label="Workbook cost" className="py-1.5 text-right">{usd(r.workbook)}</td>
                <td data-label="Town budget" className="py-1.5 text-right">{usd(r.general)}</td>
                <td data-label="Outside" className="py-1.5 text-right font-semibold"
                  style={{ color: r.outside > 0 ? FUND : NEUTRAL }}>{usd(r.outside)}</td>
              </tr>
            ))}
            <tr className="border-t-2" style={{ borderColor: 'var(--axis)' }}>
              <td className="rowhead py-1.5 font-bold">Total</td>
              <td data-label="Workbook cost" className="py-1.5 text-right font-bold">
                {usd(d.compare.workbook_total)}</td>
              <td data-label="Town budget" className="py-1.5 text-right font-bold">
                {usd(d.compare.general_total)}</td>
              <td data-label="Outside" className="py-1.5 text-right font-bold" style={{ color: FUND }}>
                {usd(d.compare.workbook_total - d.compare.general_total)}</td>
            </tr>
          </tbody>
        </table>
        <p className="text-[12.5px] leading-relaxed mt-4" style={{ color: 'var(--text-secondary)' }}>
          A further <strong>{usd(d.compare.unmatched_total)}</strong> sat on general fund
          athletics lines with no counterpart in the workbook at all &mdash;{' '}
          {d.compare.unmatched.map(u => `${u.item.replace(/^Athletic /, '').toLowerCase()} ${usd(u.amount)}`).join(', ')}.
          Adding those to one side of a comparison the other side cannot see is precisely
          the error this page is about, so they are named here instead.
        </p>
      </div>
      <NotShown>
        <p>
          <strong>That the district hid anything.</strong> The fund is a Chapter 658
          revolving fund; its purpose is to hold fee revenue and spend it, and the district
          described the arrangement in its own budget overview &mdash; beside athletics, in
          writing, as a line reduced &ldquo;with anticipation that athletic revolving may be
          enough to offset this reduction&rdquo;. Rule 11 is documented here, not suspected.
        </p>
        <p className="mt-2">
          <strong>That {share(d.compare.share)} generalises.</strong> One year, one
          programme, comparable categories only. Nothing here measures anybody else&rsquo;s
          share, and the workbook is a departmental operating record rather than a ledger.
        </p>
      </NotShown>

      {/* ------------------------------------------------------------------ the registry */}
      <H2 id="gaps">What this still cannot answer</H2>
      <Body>
        These are rows in the gap register, not observations made on this page. A limit
        written in one paragraph of one page is invisible to everybody who did not read it,
        so it lives in <code>money_gaps</code>, loads into the database and is published at{' '}
        <a className="underline" style={{ color: 'var(--series-cost)' }}
          href="/what-we-cannot-answer">/what-we-cannot-answer</a>.
      </Body>
      <div className="grid gap-3 mt-6 sm:grid-cols-2">
        {d.gaps.map(g => {
          const [why, closes] = g.why.split('— closes:')
          return (
            <div key={g.what} className="card p-4">
              <p className="text-[10px] font-bold uppercase tracking-widest"
                style={{ color: 'var(--text-muted)' }}>{g.side.replace('_', ' ')}</p>
              <p className="text-[14.5px] font-semibold leading-snug mt-1">{g.what}</p>
              <p className="text-[13px] leading-relaxed mt-1.5"
                style={{ color: 'var(--text-secondary)' }}>{why.trim()}</p>
              {closes ? (
                <p className="text-[13px] leading-relaxed mt-2 pt-2 border-t"
                  style={{ borderColor: 'var(--grid)', color: 'var(--text-secondary)' }}>
                  <span className="font-semibold" style={{ color: 'var(--text-primary)' }}>
                    Closed by:
                  </span>{' '}{closes.trim()}
                </p>
              ) : null}
            </div>
          )
        })}
      </div>

      {/* -------------------------------------------------------------------- the method */}
      <H2 id="method">Where every figure on this page came from</H2>
      <div className="card p-5 mt-4 max-w-3xl">
        <p className="text-[13.5px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
          Written by <code>{d.generated_by}</code> from <code>{d.source}</code>, at build
          time. It refuses to write at all unless four things hold: the workbook&rsquo;s
          cost columns sum to its own printed total for every year; the fund&rsquo;s cash
          chains from each year&rsquo;s closing to the next year&rsquo;s printed opening
          balance; every series has rows in it; and no revenue row reaches a spending total.
          A join that matches nothing looks exactly like data that is absent, which is why
          each of those is an assertion rather than a comment.
        </p>
        <dl className="grid gap-x-8 gap-y-2 mt-4 sm:grid-cols-2 text-[13px]">
          {[
            ['Both sides, by year', `athletics_history — ${d.coverage.history_years.length} years`],
            ['Costs and participation', `athletics_by_sport — ${d.coverage.sports} sports, ${d.coverage.part_years.length} years`],
            ['The fee schedule', `athletic_fee_schedule — ${d.coverage.fee_rows} rows`],
            ['The fund&rsquo;s cashbook', `fund_1301_cash_journal — ${d.coverage.postings} postings`],
          ].map(([k, v]) => (
            <div key={k}>
              <dt className="font-semibold" dangerouslySetInnerHTML={{ __html: k }} />
              <dd style={{ color: 'var(--text-secondary)' }}>{v}</dd>
            </div>
          ))}
        </dl>
        <p className="text-[13px] leading-relaxed mt-4" style={{ color: 'var(--text-secondary)' }}>
          Every table above is downloadable as itself:{' '}
          <a className="underline" style={{ color: 'var(--series-cost)' }} href="/data/athletics.json">
            /data/athletics.json</a> is exactly what this page reads.
        </p>
      </div>

      <H2 id="reports">The reasoning, at length</H2>
      <Body>
        This page draws two written analyses. It does not replace them: the argument, the
        sources, the sha256 of every document and the alternatives that fit the same data
        are there.
      </Body>
      <div className="grid gap-3 mt-6 sm:grid-cols-2">
        {d.related.map(r => (
          <a key={r.id} href={r.url} className="card p-5 block">
            <p className="text-[15px] font-bold leading-snug">{r.title}</p>
            <p className="text-[13px] leading-relaxed mt-2" style={{ color: 'var(--text-secondary)' }}>
              {r.why}
            </p>
            <p className="text-[11.5px] mt-3" style={{ color: 'var(--text-muted)' }}>
              {r.words.toLocaleString('en-US')} words &middot; updated {r.updated}
              {r.pdf ? <> &middot; <span className="underline">PDF</span></> : null}
            </p>
          </a>
        ))}
      </div>

      <div className="card p-4 mt-8 max-w-2xl" style={{ borderLeft: '4px solid var(--axis)' }}>
        <p className="text-[11px] font-semibold uppercase tracking-widest mb-1.5"
          style={{ color: 'var(--text-muted)' }}>Why a 1.7% programme has its own page</p>
        <p className="text-[13.5px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
          It is not a driver of the budget gap and never will be &mdash; a line matters in
          proportion to its share of spending times how far its growth exceeds the levy cap,
          and athletics fails that test on the first term. It is here because it is the only
          place the mechanism can be watched: a programme whose cost was more than twice its
          appropriation, costs moving between funds by a memo that appears in neither budget
          document, and the change landing after the year had closed. Every one of those
          could be true of a line that <em>does</em> drive the gap, and for those lines
          there is no cashbook to look at.
        </p>
      </div>

      <div className="mt-8 flex flex-wrap gap-x-5 gap-y-2 text-[13px]">
        <a className="underline" style={{ color: 'var(--series-cost)' }} href="/athletics">
          The athletics decision board &mdash; what each cut saves
        </a>
        <a className="underline" style={{ color: 'var(--series-cost)' }} href="/what-we-cannot-answer">
          Everything the records cannot answer
        </a>
        <a className="underline" style={{ color: 'var(--series-cost)' }} href="/rate-register">
          Every rate and fee, with the document that set it
        </a>
      </div>
    </div>
  )
}
