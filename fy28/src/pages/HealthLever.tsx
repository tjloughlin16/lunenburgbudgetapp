import type { Tab } from '../routes'
import { usd, usdShort } from '../model/engine'
import { GAP, GAPS, HEALTH, HEALTH_LEVERS, BENT_HEALTH, ATTRIBUTION } from '../model/answers'
import { DEFAULT_RATES, LEVY_CAP, INSURANCE_CASE, CANNOT_SKIP, decadeWorth } from '../model/rates'
import { ReportShell, ShortVersion, Insight, Stat, Grain, NotShown, H2, Body, MoreReports } from '../components/report'
import { FullVersion } from '../components/FullVersion'
import { WhoPays, DoesNot, Settles, LeverLinks, pct, n0 } from '../components/lever'

const TAB: Tab = 'healthlever'

/** WHAT CHANGING THE HEALTH PLAN DOES. TJ, 17 September 2026: "health insurance should
 *  go here ... make sure that page includes what adjusting health insurance looks like."
 *
 *  /health-insurance measures the COST -- what sits outside the school budget, how fast
 *  the town's insurance department grows. This page is the LEVER: what the rate is
 *  worth to the gap, what the routes to a lower rate actually are (a plan, a pool, an
 *  employee share), what each costs whom, and why it is the one line that changes the
 *  rate rather than the amount. Every figure is the model's (answers.ts, rates.ts). */
const AT_FOUR = decadeWorth({ ...DEFAULT_RATES, health: 0.04 })
const AT_CAP = decadeWorth({ ...DEFAULT_RATES, health: LEVY_CAP })
const H = ATTRIBUTION.health
const [today, better] = INSURANCE_CASE
const M = HEALTH_LEVERS.migration
const O = HEALTH_LEVERS.optOut

export function HealthLever() {
  return (
    <ReportShell tab={TAB} dataUrl="/data/model.json"
      title="Health insurance: what changing the plan does"
      standfirst={<>Health insurance is {pct(H.shareOfBudget, 0)} of the school budget and puts {pct(H.shareOfGap, 0)} of the gap into it, because it grows {pct(HEALTH.rise, 0)} a year against a levy capped at {pct(LEVY_CAP, 1)}. It is one of two lines that can change the <em>rate</em>. Nobody in town sets the premium; what the town can change is which plans it buys, who is in the pool, and who pays what share &mdash; and each of those lands on somebody.</>}>

      <Grain>
        A projection from the district&rsquo;s own rates and the town&rsquo;s own plan documents: what the gap does when the health line grows slower, and what the routes to slower actually are. Dollars of appropriation, not premiums paid. Every route here is priced; none is recommended.
      </Grain>

      <div className="mt-10 flex flex-wrap gap-x-12 gap-y-6">
        <Stat value={pct(H.shareOfGap, 0)} tone="var(--status-critical)">of the gap comes from health insurance, a line that is {pct(H.shareOfBudget, 0)} of the budget</Stat>
        <Stat value={usdShort(AT_FOUR.removed)}>taken out of the next ten years&rsquo; gaps if the line grew {pct(0.04, 0)} instead of {pct(HEALTH.rise, 0)}</Stat>
        <Stat value={usd(M.kept)}>kept by the town for each person moved from the broadest plan to the narrower one, after the employees&rsquo; share of the saving</Stat>
        <Stat value={`${better.buildings === null ? '—' : better.buildings.toFixed(0)} vs ${today.buildings === null ? '—' : today.buildings.toFixed(0)}`}>buildings a year of commercial growth to hold the line with insurance at {pct(0.04, 0)}, against at {pct(HEALTH.rise, 0)}</Stat>
      </div>

      <H2 id="conclusions">If you read nothing else</H2>
      <ShortVersion>
        <div className="grid gap-4 mt-5 md:grid-cols-2">
          <Insight n={1} figure={pct(H.shareOfGap, 0)} tone="var(--status-critical)"
            headline={<>The health plan is the largest single lever and not a solution on its own: {pct(H.shareOfGap, 0)} of next year&rsquo;s gap is this one line, from {pct(H.shareOfBudget, 0)} of the budget.</>}>
            Hold it to the levy cap and re-run the projection: {usdShort(GAP - Math.round(GAP * (1 - H.shareOfGap)))} of next year&rsquo;s {usdShort(GAP)} gap falls out. Salaries are {ATTRIBUTION.sizeRatio.toFixed(1)}&times; the size and contribute about the same, because they grow {pct(DEFAULT_RATES.salaries, 0)} and this grows {pct(HEALTH.rise, 0)}. Rule 4 on this site: weight times excess rate, not size.
          </Insight>
          <Insight n={2} figure={usdShort(AT_FOUR.removed)}
            headline={<>Held to {pct(0.04, 0)} instead of {pct(HEALTH.rise, 0)}, it takes {usdShort(AT_FOUR.removed)} out of the next ten years&rsquo; gaps for good &mdash; the FY{GAPS[GAPS.length - 1].fy} gap is {pct(AT_FOUR.smallerBy, 0)} smaller, not gone.</>}>
            That is a rate change, so it compounds the right way: {usdShort(AT_FOUR.firstYear)} in the first year, more every year after. At the levy cap itself it would be {usdShort(AT_CAP.removed)}. Neither closes the gap alone &mdash; salaries at {pct(DEFAULT_RATES.salaries, 0)} still outrun the cap &mdash; but it is the single largest rate move on the table, and it is the least painful column on <a className="underline" href="/what-solved-requires">the page that combines them</a>.
          </Insight>
          <Insight n={3} figure={usd(M.kept)}
            headline={<>Every route is bargained, not voted: moving one person off the broadest plan keeps the town {usd(M.kept)} a year, and {n0(M.onBroadest)} are on it.</>}>
            The broadest plan ({M.from}) to the narrower one ({M.to}) saves {usd(M.gross)} a person in premium; state law hands a quarter of the first year&rsquo;s saving back to employees, so the town keeps {usd(M.kept)}. Every enrollee moved: {usdShort(M.ifAll)} a year. The opt-out the committee voted in March 2026 pays {usd(O.incentive)} against a {usd(O.premium)} premium, netting {usd(O.net)} per person who takes it. And the employee share: each point of the premium shifted from the town to its staff is worth {usd(HEALTH.perPoint)} a year to the budget.
          </Insight>
        </div>
        <NotShown>
          Whether any of it is bargainable this year. Plan design goes through the insurance advisory committee and the unions under c.32B; the FY27 rate came in at {pct(HEALTH_LEVERS.actualFy27, 1)} against the {pct(HEALTH_LEVERS.assumed, 0)} assumed, and nothing here predicts next year&rsquo;s. This page prices the routes; it does not say which one the town should take.
        </NotShown>
      </ShortVersion>

      <FullVersion what="every route, priced">
        <H2 id="rate">What the rate is worth</H2>
        <Body>The projection holds every other line where it is and moves only health insurance. What the gap does is what the line is worth.</Body>
        <div className="overflow-x-auto mt-4">
          <table className="text-sm" style={{ minWidth: 520 }}>
            <thead><tr className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>
              <th className="text-left py-2 pr-6">health insurance grows at</th><th className="text-right py-2 pr-6">first year</th><th className="text-right py-2 pr-6">ten years</th><th className="text-right py-2">FY{GAPS[GAPS.length - 1].fy} gap smaller by</th></tr></thead>
            <tbody>
              {[HEALTH.rise, 0.06, 0.04, LEVY_CAP].map(r => { const d = decadeWorth({ ...DEFAULT_RATES, health: r }); return (
                <tr key={r} style={{ borderTop: '1px solid var(--grid)' }} className={r === HEALTH.rise ? undefined : 'tnum'}>
                  <td className="py-1.5 pr-6">{pct(r, 1)}{r === HEALTH.rise ? ' (assumed)' : r === LEVY_CAP ? ' (the levy cap)' : ''}</td>
                  <td className="py-1.5 pr-6 text-right tnum">{r === HEALTH.rise ? '—' : usd(d.firstYear)}</td>
                  <td className="py-1.5 pr-6 text-right tnum">{r === HEALTH.rise ? '—' : usd(d.removed)}</td>
                  <td className="py-1.5 text-right tnum">{r === HEALTH.rise ? '—' : pct(d.smallerBy, 0)}</td>
                </tr>) })}
            </tbody>
          </table>
        </div>
        <Body>Set beside {pct(BENT_HEALTH.to, 1)} &mdash; the cap plus a point and a half, the most a serious plan change has reached in comparable towns &mdash; the saving by FY2032 is {usdShort(BENT_HEALTH.savedByFy32)}.</Body>

        <H2 id="routes">The three routes, and what each costs whom</H2>
        <div className="overflow-x-auto mt-4">
          <table className="text-sm" style={{ minWidth: 640 }}>
            <thead><tr className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>
              <th className="text-left py-2 pr-6">route</th><th className="text-left py-2 pr-6">worth to the budget</th><th className="text-left py-2">who pays</th></tr></thead>
            <tbody>
              <tr style={{ borderTop: '1px solid var(--grid)' }}><td className="py-2 pr-6 align-top font-semibold">Plan design &mdash; a narrower network</td><td className="py-2 pr-6 align-top">{usd(M.kept)} a person a year; {usdShort(M.ifAll)} if all {n0(M.onBroadest)} on {M.from} moved to {M.to}</td><td className="py-2 align-top" style={{ color: 'var(--text-secondary)' }}>The employee: a family on the narrower plan pays {usd(M.familyGap)} a year less in premium and gives up {M.fromNetwork} for {M.toNetwork}. The highest-deductible plan on offer carries a {typeof HEALTH_LEVERS.highDeductible === 'number' ? usd(HEALTH_LEVERS.highDeductible) : HEALTH_LEVERS.highDeductible} deductible.</td></tr>
              <tr style={{ borderTop: '1px solid var(--grid)' }}><td className="py-2 pr-6 align-top font-semibold">The pool &mdash; the opt-out</td><td className="py-2 pr-6 align-top">{usd(O.net)} net per person who leaves the plan for a {usd(O.incentive)} payment</td><td className="py-2 align-top" style={{ color: 'var(--text-secondary)' }}>Nobody, directly: it pays people already covered elsewhere. The committee raised it from {usd(O.priorFamily)}/{usd(O.priorIndividual)} to {usd(O.family)}/{usd(O.individual)} in March 2026 and cut the wait from {O.priorWaitYears} years to {O.waitYears}.</td></tr>
              <tr style={{ borderTop: '1px solid var(--grid)' }}><td className="py-2 pr-6 align-top font-semibold">The share &mdash; employees pay more of the premium</td><td className="py-2 pr-6 align-top">{usd(HEALTH.perPoint)} a year for each point of the premium moved; closing the whole gap this way takes {HEALTH.pointsToClose.toFixed(0)} points, to a {pct(HEALTH.shareNeeded, 0)} employee share</td><td className="py-2 align-top" style={{ color: 'var(--text-secondary)' }}>Every employee: about {usd(HEALTH.costPerFamily)} a year on a family premium of {usd(HEALTH.familyPremium)} at that share. It is a pay cut in everything but name, and it is bargained.</td></tr>
            </tbody>
          </table>
        </div>

        <WhoPays>
          A narrower plan is paid by the person whose doctor is out of network. A higher deductible is paid by the person who gets sick. A higher share is paid by every employee, every month. The town&rsquo;s saving is the same money seen from the other side of the table; this page does not pretend otherwise.
        </WhoPays>
        <DoesNot>
          It does not close the gap by itself. With insurance at {pct(0.04, 0)} and every other line at the levy cap, salaries would still have to settle at {pct(better.salary, 1)} to hold &mdash; or the town would need {better.buildings === null ? 'more building than the model can find' : `${better.buildings.toFixed(0)} buildings a year`} of commercial growth. Leave insurance at {pct(HEALTH.rise, 0)} and the same job takes {today.buildings === null ? '—' : today.buildings.toFixed(0)}. It can be skipped, at about {today.buildings && better.buildings ? (today.buildings / better.buildings).toFixed(0) : '—'}&times; the building; it cannot be finished alone. {CANNOT_SKIP.health.consumes > 0 ? <>On its own it consumes {pct(CANNOT_SKIP.health.consumes, 2)} of the revenue rate.</> : null}
        </DoesNot>
        <Settles>the insurance advisory committee&rsquo;s plan-year rate letter for FY28 (the {pct(HEALTH_LEVERS.assumed, 0)} is an assumption; FY27&rsquo;s actual was {pct(HEALTH_LEVERS.actualFy27, 1)}), and the enrolment by plan after the March 2026 opt-out change &mdash; which would say whether the pool moved.</Settles>

        <LeverLinks measures="insurance" label="What health insurance costs" />
      </FullVersion>

      <MoreReports here={TAB} />
    </ReportShell>
  )
}
