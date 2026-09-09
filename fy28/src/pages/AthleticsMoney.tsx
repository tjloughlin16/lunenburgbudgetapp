import type { Tab } from '../routes'
import { abs } from '../lib/abs'
import { Basis, type Level } from '../components/Basis'
import { useEffect, useState } from 'react'
import { usd } from '../model/engine'
import {
  BothSides, TransportSwap, Coaching, CostByCategory, CostPerSport, Participation,
  WhoPays, FundCash, FeeLadder, fy, share, FUND, NEUTRAL,
  type SideRow, type TransportRow, type CoachRow, type CatRow, type SportRow,
  type PartRow, type MixRow, type FlowRow, type FeeRow,
} from '../components/AthleticsCharts'
import {
  Conclusions,
  Body, H2, NotShown,
  ReportShell,
} from '../components/report'
import type { Conclusion } from '../components/report'

/** The frame this report is drawn in. See components/report.tsx.
 *  TITLE is the report's NAME, used before the payload arrives; the h1 the
 *  reader lands on is the finding, which needs the data to state. */
const TAB: Tab = 'sportsmoney'
const DATA = '/data/athletics.json'
const TITLE = 'Athletics, both sides of the money'

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
  conclusions: Conclusion[]
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
  counted: {
    fy: number; function: string; period: string; doc: string
    accounts: {
      account: string; name: string; program: string; book_line: string
      appropriated: number; transfers: number; revised: number; expended: number
    }[]
    appropriated: number; revised: number; expended: number
    budget_book: number; ties: boolean
    equipment: {
      accounts: { name: string; revised: number; expended: number }[]
      revised: number; expended: number
      said: {
        board: string; date: string; speaker: string; url: string; town_url: string
        quotes: { text: string; line: number }[]
      }
    }
    workbook_fy: number
    not_in_workbook: { item: string; amount: number }[]; not_in_workbook_total: number
    facility: { code: string; name: string; amount: number; accounts: number }[]
    facility_total: number; facility_attributed: number
    said: {
      board: string; date: string; speaker: string; url: string; town_url: string
      quotes: { text: string; line: number }[]
    }
  }
  compare: {
    fy: number
    rows: { category: string; workbook: number; general: number; outside: number }[]
    workbook_total: number; general_total: number; share: number
    unmatched: { item: string; amount: number }[]; unmatched_total: number
  }
  three_way: {
    fy: number
    workbook: number; fund_paid: number; general: number
    two_pots: number; over_workbook: number; over_workbook_share: number
    sources: { who: string; amount: number; level: Level; what: string; table: string }[]
  }
  disclaimer: {
    board: string; date: string; speaker: string
    doc: string; url: string; town_url: string
    quotes: { text: string; line: number }[]
    reduction: { line: string; fy: number; amount: number; quoted: string; matches: boolean }
  }
  attribution: {
    years: number[]; disbursements: number; named_vendor: number
    warrant_disbursements: number; warrant_disbursements_referenced: number
    fields_searched: string[]; sport_terms: string[]; sports: number
    sport_mentions: number
    sport_hits: { fy: number; journal: string; amount: number; terms: string[] }[]
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

/** The gap register writes emphasis as `**like this**`, because it is a CSV read by the
 *  API and by the request letter as well as by this page. Rendered here by splitting on
 *  the marker rather than by setting HTML: the field is data, and data does not get to
 *  choose what tags a page emits. */
function Marked({ text }: { text: string }) {
  return (
    <>{text.split(/\*\*(.+?)\*\*/g).map((part, i) => (
      i % 2 ? <strong key={i}>{part}</strong> : <span key={i}>{part}</span>
    ))}</>
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

  if (err) return <ReportShell tab={TAB} title={TITLE} dataUrl={DATA} err={err} />

  if (!d) return <ReportShell tab={TAB} title={TITLE} dataUrl={DATA} loading />

  const fy26 = d.both_sides[d.both_sides.length - 1]
  const t24 = d.transport.find(r => r.fy === 2024)!
  const t25 = d.transport.find(r => r.fy === 2025)!
  const partLast = d.participation_totals[d.participation_totals.length - 1]
  const unpublished = d.both_sides.filter(r => r.revolving_state === 'not published')
  const costYearFee = d.fee_headline
    .find(r => r.level === 'HS' && r.fy === d.coverage.cost_years[d.coverage.cost_years.length - 1])
  const perPart = d.participation_totals.filter(r => r.per_participation !== null)
  const wideSport = [...d.by_sport]
    .filter(r => r.fy === d.coverage.cost_years[d.coverage.cost_years.length - 1] && r.per_athlete)
    .sort((a, b) => (b.per_athlete ?? 0) - (a.per_athlete ?? 0))
  const dearest = wideSport[0], cheapest = wideSport[wideSport.length - 1]

  return (
    <ReportShell tab={TAB} dataUrl={DATA}
      title={<>
        The only programme where you can see both sides of the money.
      </>}
      standfirst={<>
        The town appropriates. Families pay a fee into a separate fund. That fund spends.
        For every other line in the budget you can see the first of those three and
        nothing else &mdash; which is why what athletics shows about the gap between an
        appropriation and a cost matters far beyond athletics.
      </>}
    >

      {/* ===================================================== WHAT THIS COUNTS, FIRST
        *
        * TJ: *"I am not clear if you are factoring in some other costs that the school
        * does, like the athletic director, trainer, facility costs, etc"*. The answer
        * existed and lived in a comment in the generator, which is the same as not
        * existing. It is the FIRST thing on the page now, because a reader cannot judge
        * any figure below without it — and it is the report's GRAIN, which every report
        * on this site states above the fold.
        *
        * IT IS NOT OUR DEFINITION OF ATHLETICS. The town's accounting system codes every
        * school account to a function, and function 3510 is Athletics — the same code
        * DESE uses. So the box is the bookkeeping's, not ours, and the build refuses to
        * publish this if the ledger and the district's budget book stop agreeing on what
        * is in it. The detail sits behind a disclosure: the answer is two sentences and
        * the twelve account numbers are for whoever wants them. */}
      <div className="card p-5 sm:p-6 mt-9" style={{ borderLeft: '4px solid var(--fund-school)' }}>
        <p className="text-[11px] font-semibold uppercase tracking-widest"
          style={{ color: 'var(--text-muted)' }}>What this page counts</p>

        <div className="grid gap-6 mt-4 sm:grid-cols-2">
          <div>
            <p className="text-2xl font-bold tnum">{usd(d.counted.appropriated)}</p>
            <p className="text-[14px] leading-snug mt-1.5">
              <strong>Everything the town&rsquo;s books call athletics</strong> in{' '}
              {fy(d.counted.fy)} &mdash; {d.counted.accounts.length} accounts under
              function {d.counted.function}, including the athletic director, the trainer,
              the secretary, the police details and the insurance.
            </p>
          </div>
          <div>
            <p className="text-2xl font-bold tnum" style={{ color: 'var(--text-muted)' }}>
              {usd(d.counted.facility_total)}
            </p>
            <p className="text-[14px] leading-snug mt-1.5">
              <strong>The buildings and grounds, which cannot be split.</strong> Custodians,
              heat, utilities, grounds and building maintenance across the whole school
              department. Not one of those accounts carries the athletics code, so no share
              of it is counted anywhere &mdash; here or in any published figure.
            </p>
          </div>
        </div>

        <p className="text-[14px] leading-relaxed mt-5 max-w-2xl">
          So every athletics total on this page, and every one the district publishes, is a{' '}
          <strong>floor rather than a total</strong>. The fields are still mown and the gym
          is still lit.
        </p>

        <details className="mt-4">
          <summary className="cursor-pointer list-none inline-flex items-center gap-1.5
                              text-[12.5px] font-semibold"
            style={{ color: 'var(--text-muted)' }}>
            <span className="conc-chev inline-block transition-transform"
              aria-hidden="true">&#9656;</span>
            The {d.counted.accounts.length} accounts, and the {d.counted.facility.length}{' '}
            functions that hold the buildings
          </summary>

          <div className="overflow-x-auto mt-4">
            <table className="stack w-full text-[12.5px] tnum max-w-3xl">
              <caption className="sr-only">
                Every {fy(d.counted.fy)} account the town&rsquo;s ledger codes to function{' '}
                {d.counted.function}, athletics
              </caption>
              <thead>
                <tr className="text-left" style={{ color: 'var(--text-muted)' }}>
                  <th className="font-semibold py-1.5">Ledger account</th>
                  <th className="font-semibold py-1.5">The budget book&rsquo;s name for it</th>
                  <th className="font-semibold py-1.5 text-right">Appropriated</th>
                  <th className="font-semibold py-1.5 text-right">After transfers</th>
                </tr>
              </thead>
              <tbody>
                {d.counted.accounts.map(a => (
                  <tr key={a.account} className="border-t" style={{ borderColor: 'var(--grid)' }}>
                    <td className="rowhead py-1.5 font-semibold">
                      <code>{a.name}</code>
                      <span className="block text-[10.5px] font-normal break-all"
                        style={{ color: 'var(--text-muted)' }}>{a.account}</span>
                    </td>
                    <td data-label="Budget book" className="py-1.5"
                      style={{ color: 'var(--text-secondary)' }}>
                      {a.book_line || <span style={{ color: 'var(--text-muted)' }}>
                        &mdash; the amounts do not tie, so nothing is claimed
                      </span>}
                    </td>
                    <td data-label="Appropriated" className="py-1.5 text-right">
                      {usd(a.appropriated)}
                    </td>
                    <td data-label="After transfers" className="py-1.5 text-right">
                      {usd(a.revised)}
                    </td>
                  </tr>
                ))}
                <tr className="border-t-2" style={{ borderColor: 'var(--axis)' }}>
                  <td className="rowhead py-1.5 font-bold">Total</td>
                  <td className="py-1.5 text-[12px]" style={{ color: 'var(--text-secondary)' }}>
                    the district&rsquo;s budget book states {usd(d.counted.budget_book)}
                  </td>
                  <td data-label="Appropriated" className="py-1.5 text-right font-bold">
                    {usd(d.counted.appropriated)}
                  </td>
                  <td data-label="After transfers" className="py-1.5 text-right font-bold">
                    {usd(d.counted.revised)}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <p className="text-[12.5px] leading-relaxed mt-3 max-w-2xl"
            style={{ color: 'var(--text-secondary)' }}>
            <Basis level="cross-checked" />{' '}
            <span className="ml-1">
              The account names are the ten characters MUNIS prints, not ours. The ledger and
              the budget book state the same total to the cent, and the build refuses to
              publish this block if they stop doing so &mdash; a printout from the books
              confirming a sheet somebody assembled. Period {d.counted.period} of{' '}
              {fy(d.counted.fy)}, from <code>{d.counted.doc.split('/').pop()}</code>.
            </span>
          </p>

          {/* STEP 3 OF notes/process/PERSONAS.md, which is the step a verifier cannot do.
              For every category that shows underspending, search the archive for what
              somebody concretely asked for in the same year. The two athletics equipment
              accounts are above; the football boosters' president asked this committee for
              five helmets in the same year, at the same meeting this page already quotes.
              The report held both halves and had not put them together.

              AND WHAT IT MUST NOT SAY. That the money was there and was withheld. Three
              things cut against it and all three are stated: the ledger stops at period 12
              rather than a closed year, reconditioning is not buying, and nothing here
              dates the request against the order window. */}
          <div className="mt-5 pt-4 border-t" style={{ borderColor: 'var(--grid)' }}>
            <p className="text-[11px] font-semibold uppercase tracking-widest mb-2"
              style={{ color: 'var(--text-muted)' }}>
              The equipment lines, and what somebody asked for in the same year
            </p>
            <p className="text-[13.5px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
              The two equipment accounts above carried {usd(d.counted.equipment.revised)}{' '}
              after transfers in {fy(d.counted.fy)} and had spent{' '}
              {usd(d.counted.equipment.expended)} of it by period {d.counted.period}.
            </p>
            {d.counted.equipment.said.quotes.map(qt => (
              <blockquote key={qt.line} className="text-[14px] leading-relaxed pl-3.5 my-2.5"
                style={{ borderLeft: '3px solid var(--axis)' }}>
                &ldquo;{qt.text}&rdquo;{' '}
                <span className="text-[11.5px]" style={{ color: 'var(--text-muted)' }}>
                  line {qt.line}
                </span>
              </blockquote>
            ))}
            <p className="text-[12.5px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
              {d.counted.equipment.said.speaker}, president of the football boosters, to the{' '}
              {d.counted.equipment.said.board} on {d.counted.equipment.said.date} &mdash;{' '}
              <a className="underline" style={{ color: 'var(--series-cost)' }}
                href={abs(d.counted.equipment.said.url)}>our copy</a> &middot;{' '}
              <a className="underline" style={{ color: 'var(--series-cost)' }}
                href={d.counted.equipment.said.town_url}>the town&rsquo;s</a>, checked on
              every build. <strong>These two facts are set side by side and nothing here
              connects them.</strong> Period {d.counted.period} is not a closed year, so a
              line that has not spent is not a line that will not; reconditioning helmets
              and buying them are different accounts; and nothing published dates the
              request against the ordering window. What the minutes establish is that the
              request was made and that no answer had been given by that meeting.
            </p>
          </div>

          <div className="overflow-x-auto mt-5">
            <table className="stack w-full text-[12.5px] tnum max-w-2xl">
              <caption className="sr-only">
                The school department&rsquo;s operations and maintenance functions in{' '}
                {fy(d.counted.fy)}, none of them coded to athletics
              </caption>
              <thead>
                <tr className="text-left" style={{ color: 'var(--text-muted)' }}>
                  <th className="font-semibold py-1.5">Function</th>
                  <th className="font-semibold py-1.5 text-right">Whole school department</th>
                  <th className="font-semibold py-1.5 text-right">Coded to athletics</th>
                </tr>
              </thead>
              <tbody>
                {d.counted.facility.map(f => (
                  <tr key={f.code} className="border-t" style={{ borderColor: 'var(--grid)' }}>
                    <td className="rowhead py-1.5 font-semibold">
                      {f.name} <span style={{ color: 'var(--text-muted)' }}>{f.code}</span>
                    </td>
                    <td data-label="Whole department" className="py-1.5 text-right">
                      {usd(f.amount)}
                    </td>
                    <td data-label="Coded to athletics" className="py-1.5 text-right"
                      style={{ color: 'var(--text-muted)' }}>{usd(0)}</td>
                  </tr>
                ))}
                <tr className="border-t-2" style={{ borderColor: 'var(--axis)' }}>
                  <td className="rowhead py-1.5 font-bold">Total</td>
                  <td data-label="Whole department" className="py-1.5 text-right font-bold">
                    {usd(d.counted.facility_total)}
                  </td>
                  <td data-label="Coded to athletics" className="py-1.5 text-right font-bold">
                    {usd(d.counted.facility_attributed)}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <p className="text-[12.5px] leading-relaxed mt-3 max-w-2xl"
            style={{ color: 'var(--text-secondary)' }}>
            The right-hand column is not an estimate of zero. It is the count of accounts in
            those functions carrying the athletics programme code, and the build stops if it
            ever stops being none &mdash; because on that day a share <em>would</em> be
            attributable and this page would have to say so. The fund&rsquo;s cashbook does
            not help either: no posting in it names a field, a light or a custodian.{' '}
            <a className="underline" style={{ color: 'var(--series-cost)' }}
              href={abs('/what-we-cannot-answer')}>Registered as a gap</a>, with the
            document that would close it.
          </p>

          {/* RULE 15a. An ABSENCE is the hardest thing to publish honestly, so the
              corroboration is a town official asking in public for the document this page
              says does not exist. Asserted against the minutes file on every build, with
              the line it starts on. */}
          <div className="mt-5 pt-4 border-t" style={{ borderColor: 'var(--grid)' }}>
            <p className="text-[11px] font-semibold uppercase tracking-widest mb-2"
              style={{ color: 'var(--text-muted)' }}>
              A town board asked for this document and did not get one
            </p>
            {d.counted.said.quotes.map(qt => (
              <blockquote key={qt.line} className="text-[14px] leading-relaxed pl-3.5 mb-2"
                style={{ borderLeft: '3px solid var(--axis)' }}>
                &ldquo;{qt.text}&rdquo;{' '}
                <span className="text-[11.5px]" style={{ color: 'var(--text-muted)' }}>
                  line {qt.line}
                </span>
              </blockquote>
            ))}
            <p className="text-[12.5px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
              {d.counted.said.board}, {d.counted.said.date}, in the town&rsquo;s own
              minutes &mdash;{' '}
              <a className="underline" style={{ color: 'var(--series-cost)' }}
                href={abs(d.counted.said.url)}>our copy</a> &middot;{' '}
              <a className="underline" style={{ color: 'var(--series-cost)' }}
                href={d.counted.said.town_url}>the town&rsquo;s</a>. The quote is checked
              against that file every time this page is built.{' '}
              <strong>What it establishes</strong> is that the question was asked and
              referred onward. <strong>What it does not establish</strong> is that no plan
              exists &mdash; only that none was produced then, and that none has reached
              this archive since.
            </p>
          </div>
        </details>
      </div>

      {/* ------------------------------------------------ 1. CONCLUSIONS (rule 7b) */}
      {/* NOT WRITTEN HERE. Every word and every figure comes out of this report's own
          payload, computed by the generator that computed the figures -- see
          scripts/conclusions.py. The same rows appear on /what-it-all-adds-up-to, read
          from the same file, so the two cannot drift apart.

          THREE, AND NOT MORE, ON PURPOSE. Rule 4: athletics is 1.7% of what the town
          spends and its growth does not exceed the levy cap, so it is not a driver of the
          gap and a page about it must not carry the weight of one. What earns its place is
          only what generalises -- the disagreement between documents, what an
          appropriation does and does not contain, and one bill visibly moving between
          funds. A fourth card computing a cost per participation was cut for the opposite
          reason: it is the most quotable figure here and the least decision-relevant, and
          a participation is not a child. */}
      <H2 id="conclusions">If you read nothing else</H2>
      <Conclusions rows={d.conclusions} />

      {/* ================================== THE DISAGREEMENT, WHICH IS THE FIRST FINDING
        *
        * Rule 7a says a page opens with the thing and makes one exception, for a warning
        * that changes whether a reader should trust what follows. This is that warning,
        * and it sits directly under the conclusion that states it rather than above
        * everything: three documents, three figures, one year, drawn.
        *
        * Rule 15a: the quotes are asserted against the minutes file on every build by
        * scripts/build_athletics_charts.py, with the line each one starts on. They are
        * behind a disclosure because the table is the finding and the minutes are the
        * evidence that it is contested in public -- and a reader meets evidence better
        * after the thing it is evidence about. */}
      <H2 id="three-documents">
        Three documents say what athletics cost in {fy(d.three_way.fy)}. No two agree
      </H2>
      <div className="card p-5 mt-5" style={{ borderLeft: '4px solid var(--status-warning)' }}>
        <div className="overflow-x-auto">
          <table className="stack w-full text-[13px] tnum max-w-2xl">
            <caption className="sr-only">
              Three figures for what athletics cost in {fy(d.three_way.fy)}, with how
              confirmed each one is
            </caption>
            <tbody>
              {d.three_way.sources.map(r => (
                <tr key={r.who} className="border-t" style={{ borderColor: 'var(--grid)' }}>
                  <td className="rowhead py-2 pr-4 font-semibold leading-snug">{r.who}</td>
                  <td data-label="Amount"
                    className="py-2 pr-4 text-right font-bold whitespace-nowrap">
                    {usd(r.amount)}
                  </td>
                  <td data-label="How confirmed" className="py-2">
                    <Basis level={r.level}>{r.what}</Basis>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <p className="text-[14px] leading-relaxed mt-4 max-w-2xl"
          style={{ color: 'var(--text-secondary)' }}>
          The second and third are money that really left two different pots, so they add:{' '}
          <strong style={{ color: 'var(--status-bad)' }}>{usd(d.three_way.two_pots)}</strong>{' '}
          &mdash; {usd(d.three_way.over_workbook)} more than the workbook says the whole
          programme cost. The first is a claim about total cost and may not be added to
          either. <strong>The disagreement is the finding</strong>, and it is worth more
          than any one of the three figures.
        </p>

        <p className="text-[13px] leading-relaxed mt-3 max-w-2xl"
          style={{ color: 'var(--text-muted)' }}>
          <strong>What this does not show.</strong> Which of the three is right, or that
          any of them is wrong. Three readings fit equally: the workbook may count a
          narrower programme than the two funds paid for; the fund and the appropriation may
          both be paying for things the workbook never tracked; or the workbook may simply
          be a plan and the other two the money. Nothing in these documents separates them.
        </p>

        <details className="mt-4">
          <summary className="cursor-pointer list-none inline-flex items-center gap-1.5
                              text-[12.5px] font-semibold"
            style={{ color: 'var(--text-muted)' }}>
            <span className="conc-chev inline-block transition-transform"
              aria-hidden="true">&#9656;</span>
            These figures are contested in public, on the record
          </summary>
          {d.disclaimer.quotes.slice(0, 2).map(qt => (
            <blockquote key={qt.line} className="text-[14.5px] leading-relaxed pl-3.5 mb-2.5 mt-3"
              style={{ borderLeft: '3px solid var(--status-warning)' }}>
              &ldquo;{qt.text}&rdquo;{' '}
              <span className="text-[11.5px]" style={{ color: 'var(--text-muted)' }}>
                line {qt.line}
              </span>
            </blockquote>
          ))}
          <p className="text-[13px] leading-relaxed mt-3" style={{ color: 'var(--text-secondary)' }}>
            {d.disclaimer.speaker}, in public comment to the {d.disclaimer.board} on{' '}
            {d.disclaimer.date}, recorded in the town&rsquo;s own minutes. Both quotes are
            checked against{' '}
            <a className="underline" style={{ color: 'var(--series-cost)' }}
              href={abs(d.disclaimer.url)}>the minutes we serve</a> every time this page is
            built, at the lines given &mdash; and{' '}
            <a className="underline" style={{ color: 'var(--series-cost)' }}
              href={d.disclaimer.town_url}>the town&rsquo;s own copy</a> is the address to
            ask for if that one ever moves.
          </p>
          <p className="text-[13px] leading-relaxed mt-2.5" style={{ color: 'var(--text-secondary)' }}>
            <strong>What the minutes establish</strong> is that the question was asked in
            public and that the answers given were described, on the record, as
            inconsistent &mdash; and that no reconciliation has been published since.{' '}
            <strong>What they do not establish</strong> is a cost. This is a resident
            speaking, not the district conceding a figure, and a statement that answers were
            inconsistent does not say which of them was wrong.
          </p>
          <p className="text-[13px] leading-relaxed mt-2.5" style={{ color: 'var(--text-secondary)' }}>
            One figure in the same statement <em>can</em> be checked, and it holds:{' '}
            <Basis level="cross-checked" />{' '}
            <span className="ml-1">
              &ldquo;{d.disclaimer.reduction.quoted}&rdquo; &mdash; and the district&rsquo;s
              own budget carries {usd(d.disclaimer.reduction.amount)} against{' '}
              <em>{d.disclaimer.reduction.line}</em> in {fy(d.disclaimer.reduction.fy)} &mdash;
              the most recent year the measured series carries that line at all. The build
              refuses to publish this sentence if the two stop matching. It confirms the
              size of the reduction, and it does not confirm anything about the cost.
            </span>
          </p>
        </details>
      </div>

      {/* ------------------------------------------------ where we differ from the prose */}
      <div className="card p-5 mt-6" style={{ borderLeft: '4px solid var(--status-warning)' }}>
        <p className="text-[14.5px] font-bold mb-1">
          Where this page differs from the written analyses, these are the recomputed
          figures.
        </p>
        <ul className="space-y-3 mt-3">
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
      <p className="mt-1"><Basis level="stated">
        one document &mdash; the district&rsquo;s own workbook &mdash; and it is the
        document whose figures are contested above
      </Basis></p>
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
      <p className="mt-1"><Basis level="stated">
        one document, disclaimed by its own author &mdash; kept, because a bounded answer
        with its basis attached beats a refusal
      </Basis></p>
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

      {/* ------------------------ why nothing independent can check a per-sport figure */}
      <div className="card p-5 mt-6 max-w-3xl" style={{ borderLeft: '4px solid var(--status-warning)' }}>
        <p className="text-[14.5px] font-bold mb-1">
          The only independent record of athletics money cannot be put against a sport.
        </p>
        <p className="text-[13.5px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
          The revolving fund&rsquo;s cashbook is the one place in this archive where an
          athletics payment is a transaction rather than a claim &mdash;{' '}
          <Basis level="traced to a payment" />. It could corroborate the bars above, and it
          cannot, because of what a row does not carry.{' '}
          <strong>{d.attribution.warrant_disbursements_referenced} of{' '}
            {d.attribution.warrant_disbursements}</strong> warrant disbursements carry a
          warrant reference and nothing else &mdash; no vendor, no description &mdash; and a
          vendor name appears on {d.attribution.named_vendor} of all{' '}
          {d.attribution.disbursements} disbursements across{' '}
          {fy(d.attribution.years[0])}&ndash;{fy(d.attribution.years[d.attribution.years.length - 1])}.
        </p>
        <p className="text-[13.5px] leading-relaxed mt-3" style={{ color: 'var(--text-secondary)' }}>
          <strong>The check, so it is not taken on trust.</strong> Every one of those{' '}
          {d.attribution.disbursements} rows was searched across{' '}
          {d.attribution.fields_searched.length} fields &mdash;{' '}
          {d.attribution.fields_searched.map(f => <code key={f} className="mr-1.5">{f}</code>)}{' '}
          &mdash; for any of the {d.attribution.sport_terms.length} words in the
          workbook&rsquo;s own names for its {d.attribution.sports} sports, whole words only.
          Hits:{' '}
          <strong style={{
            color: d.attribution.sport_mentions === 0 ? 'var(--status-bad)' : 'var(--text-primary)',
          }}>{d.attribution.sport_mentions}</strong>.
          {d.attribution.sport_mentions === 0
            ? ' Not one payment out of that fund, in three years, names a sport.'
            : ` ${d.attribution.sport_hits.map(h => `${fy(h.fy)} journal ${h.journal}`).join(', ')}.`}
          {' '}The vocabulary is read off <code>athletics_by_sport</code> rather than typed,
          so a sport the district adds next year is searched for without anybody remembering
          to add it, and the generator refuses to publish this paragraph if that list comes
          back empty &mdash; a zero found by looking for nothing is not a finding.
        </p>
        <p className="text-[13px] leading-relaxed mt-3" style={{ color: 'var(--text-muted)' }}>
          <strong>What this does not show.</strong> That the information does not exist. The
          warrants themselves name a vendor and a description, and the town&rsquo;s
          accounting system holds the accounts-payable detail behind every one of these
          references. It is not published, which is a different thing from not being
          recorded &mdash; and it is the single document that would let anybody say what a
          sport costs.
        </p>
      </div>

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
        {d.negatives.length} rows in the workbook are <em>negative</em> &mdash;
        out-of-district athletes subtracted back out, {d.negatives.reduce((a, n) => a + n.athletes, 0)}{' '}
        across the three years, all of them in{' '}
        {[...new Set(d.negatives.map(n => n.season))].join(' and ')}. They are counted the
        way the sheet counts them, which means a season total is a net figure and not a
        headcount of bodies.
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
                style={{ color: 'var(--text-secondary)' }}><Marked text={why.trim()} /></p>
              {closes ? (
                <p className="text-[13px] leading-relaxed mt-2 pt-2 border-t"
                  style={{ borderColor: 'var(--grid)', color: 'var(--text-secondary)' }}>
                  <span className="font-semibold" style={{ color: 'var(--text-primary)' }}>
                    Closed by:
                  </span>{' '}<Marked text={closes.trim()} />
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
          <a className="underline" style={{ color: 'var(--series-cost)' }} href={abs('/data/athletics.json')}>
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
          <a key={r.id} href={abs(r.url)} className="card p-5 block">
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
    </ReportShell>
  )
}
