import type { Tab } from '../routes'
import { usd, usdShort } from '../model/engine'
import { GAPS, CONTRACT, SETTLEMENT, COUNTERFACTUAL, ATTRIBUTION } from '../model/answers'
import { DEFAULT_RATES, LEVY_CAP, CANNOT_SKIP, COST_PER_FTE, HEADCOUNT, workforceShrink, decadeWorth } from '../model/rates'
import { ReportShell, ShortVersion, Insight, Stat, Grain, NotShown, H2, Body, MoreReports } from '../components/report'
import { FullVersion } from '../components/FullVersion'
import { WhoPays, DoesNot, Settles, LeverLinks, pct, n0 } from '../components/lever'

const TAB: Tab = 'salarylever'

/** WHAT THE CONTRACT DECIDES. The other line that changes the rate. Salaries are two
 *  thirds of the budget and bargained three years at a time; the current teachers'
 *  agreement expires at the end of FY27, so the successor settlement is the one large
 *  number in FY28 nobody has written down yet. This page prices it: what each half a
 *  point on the settlement is worth, what holding the line to the levy cap would mean
 *  in people if the scale still moved, and what the last three years' raises would have
 *  been worth had they been smaller. Rule 8: none of it says what teachers should be
 *  paid. It says what each number costs the gap, and whom it costs. */
const S = ATTRIBUTION.salaries
const AT_CAP = decadeWorth({ ...DEFAULT_RATES, salaries: LEVY_CAP })
const SHRINK = workforceShrink(LEVY_CAP, DEFAULT_RATES.salaries)
const CS = CANNOT_SKIP.salaries

export function SalaryLever() {
  return (
    <ReportShell tab={TAB} dataUrl="/data/model.json"
      title="What the contract decides"
      standfirst={<>Salaries are {pct(S.shareOfBudget, 0)} of the school budget, bargained three years at a time, and the teachers&rsquo; agreement runs out on {CONTRACT.expires} &mdash; in the middle of the budget this site is about. Each half a point on the next settlement is worth {usd(SETTLEMENT.perHalfPoint)} to next year&rsquo;s gap. Holding the line to the levy cap while the scale still moves is not a pay freeze; it is {SHRINK.positionsPerYear.toFixed(1)} fewer positions a year.</>}>

      <Grain>
        A projection from the district&rsquo;s salary lines and the union agreement as published: what the gap does at each settlement rate, and what a rate means in people at the catalogue&rsquo;s own cost per position. Dollars of appropriation and positions, not pay slips; the model does not know who is on which step.
      </Grain>

      <div className="mt-10 flex flex-wrap gap-x-12 gap-y-6">
        <Stat value={usd(SETTLEMENT.perHalfPoint)} tone="var(--status-critical)">on next year&rsquo;s gap for each half a percentage point on the settlement</Stat>
        <Stat value={pct(S.shareOfGap, 0)}>of the gap comes from salaries growing {pct(S.rate, 0)} against a {pct(LEVY_CAP, 1)} cap &mdash; from a line {pct(S.shareOfBudget, 0)} of the budget</Stat>
        <Stat value={`${SHRINK.positionsPerYear.toFixed(1)} FTE`}>a year the district would lose holding the line to the cap while the contract pays {pct(DEFAULT_RATES.salaries, 0)}</Stat>
        <Stat value={CONTRACT.expires}>when the teachers&rsquo; agreement expires; notice to reopen is due {CONTRACT.noticeBy}</Stat>
      </div>

      <H2 id="conclusions">If you read nothing else</H2>
      <ShortVersion>
        <div className="grid gap-4 mt-5 md:grid-cols-2">
          <Insight n={1} figure={usd(SETTLEMENT.perHalfPoint)} tone="var(--status-critical)"
            headline={<>The next settlement is the largest unwritten number in FY{GAPS[0].fy}: each half a point is {usd(SETTLEMENT.perHalfPoint)} on the gap, and it compounds.</>}>
            The projection assumes {pct(SETTLEMENT.assumed, 1)}, which costs {usd(SETTLEMENT.assumedCost)} next year on its own. At {pct(0.025, 1)} the FY{GAPS[0].fy} gap is {usd(SETTLEMENT.rates.find(r => r.rate === 0.025)!.gap)}; at {pct(0.05, 1)} it is {usd(SETTLEMENT.rates.find(r => r.rate === 0.05)!.gap)}. The last agreement moved the scale {pct(CONTRACT.compound, 2)} over three years ({CONTRACT.cola.map(c => pct(c.pct, 1)).join(', ')}), with steps of about {pct(CONTRACT.avgStep, 1)} on top for anyone not at the maximum.
          </Insight>
          <Insight n={2} figure={`${SHRINK.positionsPerYear.toFixed(1)} FTE`}
            headline={<>&ldquo;Hold salaries to the cap&rdquo; with the contract at {pct(DEFAULT_RATES.salaries, 0)} means {SHRINK.positionsPerYear.toFixed(1)} fewer positions every year &mdash; {pct(SHRINK.after10, 0)} of the staff in ten.</>}>
            A line can only grow slower than the pay on it by carrying fewer people. At the catalogue&rsquo;s {usd(COST_PER_FTE)} a position and roughly {n0(HEADCOUNT)} positions, the difference between {pct(DEFAULT_RATES.salaries, 0)} and {pct(LEVY_CAP, 1)} is {SHRINK.positionsPerYear.toFixed(1)} a year, for ever. The other way to the same line is a settlement at the cap with the staff intact &mdash; which is the table, not the budget.
          </Insight>
          <Insight n={3} figure={usdShort(COUNTERFACTUAL.atCap.fy28)}
            headline={<>Had the last three raises been {pct(LEVY_CAP, 1)} instead of {pct(CONTRACT.compound / 3, 1)} a year, next year&rsquo;s gap would be {usdShort(COUNTERFACTUAL.atCap.fy28)} rather than {usdShort(COUNTERFACTUAL.actual.fy28)} &mdash; and FY{GAPS[4].fy}&rsquo;s {usdShort(COUNTERFACTUAL.atCap.fy32)} rather than {usdShort(COUNTERFACTUAL.actual.fy32)}.</>}>
            A smaller settlement is a level shift, not a slope change: it lowers every year at once and slows nothing down. Health insurance still rises {pct(DEFAULT_RATES.health, 0)}, the levy is still capped at {pct(LEVY_CAP, 1)}, so the effect is dramatic next year and modest by FY{GAPS[4].fy}. The counterfactual is on {pct(COUNTERFACTUAL.shareOfSalaries, 0)} of the salary line &mdash; the {usdShort(COUNTERFACTUAL.payroll)} the teachers&rsquo; agreement covers &mdash; and a teacher at the middle of the scale ({CONTRACT.samples[1].label}, {usd(CONTRACT.samples[1].pay)}) would be paid {pct(COUNTERFACTUAL.atCap.perCent, 1)} less today.
          </Insight>
        </div>
        <NotShown>
          What teachers should be paid, or what the district can hire at. The model prices a rate; it does not know the market for a chemistry teacher in Worcester County. Nor does it model steps and lanes, which move the line whatever the scale does. Salaries at {pct(DEFAULT_RATES.salaries, 0)} alone consume {pct(CS.consumes, 2)} of the revenue rate &mdash; the whole of it &mdash; so every other line at the cap still leaves the blend at {pct(CS.blendedOthersAtCap, 2)}: this line cannot be left out of any answer, and it cannot be the whole of one.
        </NotShown>
      </ShortVersion>

      <FullVersion what="the settlement, rate by rate">
        <H2 id="settlement">The gap at each settlement</H2>
        <Body>Everything else held where the projection has it; only the salary rate moves.</Body>
        <div className="overflow-x-auto mt-4">
          <table className="text-sm" style={{ minWidth: 460 }}>
            <thead><tr className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>
              <th className="text-left py-2 pr-6">settlement</th><th className="text-right py-2 pr-6">FY{GAPS[0].fy} gap</th><th className="text-right py-2">FY{GAPS[4].fy} gap</th></tr></thead>
            <tbody>{SETTLEMENT.rates.map(r => (
              <tr key={r.rate} style={{ borderTop: '1px solid var(--grid)' }} className={r.rate === SETTLEMENT.assumed ? 'font-semibold' : undefined}>
                <td className="py-1.5 pr-6 tnum">{pct(r.rate, 1)}{r.rate === SETTLEMENT.assumed ? ' (assumed)' : r.rate === LEVY_CAP ? ' (the levy cap)' : r.rate === 0 ? ' (a freeze)' : ''}</td>
                <td className="py-1.5 pr-6 text-right tnum">{usd(r.gap)}</td><td className="py-1.5 text-right tnum">{usd(r.fy32)}</td>
              </tr>))}</tbody>
          </table>
        </div>

        <H2 id="people">The same line, in people</H2>
        <Body>Holding the salary line to a rate below the contract&rsquo;s means fewer people on it. At {pct(DEFAULT_RATES.salaries, 0)} pay and a {pct(LEVY_CAP, 1)} line: {SHRINK.positionsPerYear.toFixed(1)} positions a year; {pct(SHRINK.after10, 0)} of the staff gone in ten years, {pct(SHRINK.after20, 0)} in twenty. Held to the cap for ten years the line takes {usdShort(AT_CAP.removed)} out of the decade&rsquo;s gaps &mdash; the same figure whether it is done at the table or by attrition, which is the whole choice.</Body>

        <H2 id="looking-back">If the last three raises had been smaller</H2>
        <div className="overflow-x-auto mt-4">
          <table className="text-sm" style={{ minWidth: 560 }}>
            <thead><tr className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>
              <th className="text-left py-2 pr-6">raises had been</th><th className="text-right py-2 pr-6">payroll lower by</th><th className="text-right py-2 pr-6">FY{GAPS[0].fy} gap</th><th className="text-right py-2">FY{GAPS[4].fy} gap</th></tr></thead>
            <tbody>
              <tr style={{ borderTop: '1px solid var(--grid)' }} className="font-semibold"><td className="py-1.5 pr-6">as agreed ({CONTRACT.cola.map(c => pct(c.pct, 1)).join(', ')})</td><td className="py-1.5 pr-6 text-right tnum">—</td><td className="py-1.5 pr-6 text-right tnum">{usd(COUNTERFACTUAL.actual.fy28)}</td><td className="py-1.5 text-right tnum">{usd(COUNTERFACTUAL.actual.fy32)}</td></tr>
              {COUNTERFACTUAL.scenarios.map(s => (
                <tr key={s.rate} style={{ borderTop: '1px solid var(--grid)' }}>
                  <td className="py-1.5 pr-6 tnum">{pct(s.rate, 1)} a year</td><td className="py-1.5 pr-6 text-right tnum">{usd(s.lower)} ({pct(s.perCent, 1)})</td><td className="py-1.5 pr-6 text-right tnum">{usd(s.fy28)}</td><td className="py-1.5 text-right tnum">{usd(s.fy32)}</td>
                </tr>))}
            </tbody>
          </table>
        </div>
        <Body>Read the last column against the first: the counterfactual that halves next year&rsquo;s gap leaves FY{GAPS[4].fy}&rsquo;s most of what it was. That is what &ldquo;a level shift, not a slope change&rdquo; means, and it is why the loud position on each side is wrong &mdash; the raises are not why there is a gap, and a smaller settlement would not have ended it.</Body>

        <WhoPays>
          The people on the scale, in pay; or the people not on it next year, in a job. There is no third party. A settlement at the cap with the staff intact costs every teacher the difference between {pct(LEVY_CAP, 1)} and what the market pays; a settlement at the market with the line held costs {SHRINK.positionsPerYear.toFixed(1)} colleagues a year. The scale runs from {usd(CONTRACT.bottom)} to {usd(CONTRACT.top)}.
        </WhoPays>
        <DoesNot>
          It does not touch health insurance, which is bargained separately and grows {pct(DEFAULT_RATES.health, 0)}; the two lines together are {pct(S.shareOfBudget + ATTRIBUTION.health.shareOfBudget, 0)} of the budget and the only two that change the rate. And it decides nothing before {CONTRACT.expires}: the FY{GAPS[0].fy} budget will be built on a settlement that does not yet exist.
        </DoesNot>
        <Settles>the successor agreement itself, or the district&rsquo;s bargaining parameters if the School Committee adopts any in public session; and DESE&rsquo;s staffing file for FY{GAPS[0].fy}, which would turn the position arithmetic here into a count.</Settles>

        <LeverLinks measures="staffing" label="School staffing — did it go up, and over which years" />
      </FullVersion>

      <MoreReports here={TAB} />
    </ReportShell>
  )
}
