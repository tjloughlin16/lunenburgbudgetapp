import type { Tab } from '../routes'
import { usd, usdShort } from '../model/engine'
import { GAP, GAPS, FEES, yearsCovered, shortfallAfter } from '../model/answers'
import { DEFAULT_RATES } from '../model/rates'
import { ReportShell, ShortVersion, Insight, Stat, Grain, NotShown, H2, Body, MoreReports } from '../components/report'
import { FullVersion } from '../components/FullVersion'
import { WhoPays, DoesNot, Settles, LeverLinks, pct, n0 } from '../components/lever'

const TAB: Tab = 'feelever'

/** WHAT FEES CAN RAISE. /what-families-pay measures what a family hands over; this is
 *  the LEVER: what each fee could add against the appropriation if it were pushed to
 *  the most it can ever raise -- and the shape of a fee, which is that past a price
 *  people stop paying it, so every fee has a peak and one of the three cannot reach
 *  self-funding at any price. Every figure is the lever's own (model/levers.py through
 *  answers.FEES). */
const YEARS = yearsCovered(FEES.total, DEFAULT_RATES.other)
const AFTER = shortfallAfter(FEES.total, DEFAULT_RATES.other)

export function FeeLever() {
  return (
    <ReportShell tab={TAB} dataUrl="/data/model.json"
      title="School user and athletic fees: what they can raise"
      standfirst={<>Athletic, activity and bus fees pushed to the most each can ever raise add {usdShort(FEES.total)} against the budget &mdash; {pct(FEES.shareOfGap, 0)} of next year&rsquo;s gap. Every fee has a peak, because past a price families stop paying; {FEES.cases.filter(c => !c.reachable).length === 0 ? 'each of the three' : `${FEES.cases.filter(c => c.reachable).length} of the three`} can reach self-funding. Special education transport, {usdShort(FEES.spedTransport)}, may not be charged for at all.</>}>

      <Grain>
        A projection from the district&rsquo;s own fee schedules, participation counts and the cost of each programme: what each fee yields now, at the price where the programme pays for itself, and at the price where it raises the most it ever can. Dollars against the appropriation, net of what is already collected; not what a family pays, which is on its own page.
      </Grain>

      <div className="mt-10 flex flex-wrap gap-x-12 gap-y-6">
        <Stat value={usdShort(FEES.total)} tone="var(--series-revenue)">the most all three fees can add against the budget, at once, at their peaks</Stat>
        <Stat value={pct(FEES.shareOfGap, 0)}>of next year&rsquo;s {usdShort(GAP)} gap that is</Stat>
        <Stat value={YEARS ? `${YEARS} yr` : 'not 1 yr'} tone="var(--status-critical)">{YEARS ? 'it covers, growing with the programmes it funds; ' : 'it covers — '}by FY{AFTER.fy} the gap is {usdShort(AFTER.short)} past it</Stat>
        <Stat value={usdShort(FEES.spedTransport)}>of transport no fee may touch &mdash; special education</Stat>
      </div>

      <H2 id="conclusions">If you read nothing else</H2>
      <ShortVersion>
        <div className="grid gap-4 mt-5 md:grid-cols-2">
          <Insight n={1} figure={usdShort(FEES.total)} tone="var(--series-revenue)"
            headline={<>Every fee at its peak adds {usdShort(FEES.total)}: {pct(FEES.shareOfGap, 0)} of the gap, and none of the programmes cut.</>}>
            {FEES.cases.map(c => `${c.label}: ${usd(Math.max(0, c.gain))} more than today${c.reachable ? ', at a fee that makes it pay for itself' : ', and it cannot reach self-funding at any price'}.`).join(' ')} Worth doing on the model&rsquo;s arithmetic; not a solution, because the gap grows {pct(GAPS[1].growthRate, 1)} a year and a fee does not.
          </Insight>
          <Insight n={2} figure={`${FEES.cases.filter(c => c.reachable).length} of 3`}
            headline={<>A fee has a peak. Raise it past that and it raises less, because families stop paying &mdash; {FEES.cases.filter(c => c.reachable).length} of the three programmes can pay for themselves before their peak.</>}>
            {FEES.cases.map(c => `${c.label} costs ${usd(c.cost)}; at ${usd(c.currentFee)} it raises ${usd(c.currentYield)} (${pct(c.coverageNow, 0)}), and the most it can raise is ${usd(c.peakYield)} at ${usd(c.peakFee)} (${pct(c.peakCoverage, 0)}).`).join(' ')}
          </Insight>
          <Insight n={3} figure={YEARS ? `${YEARS} yr` : 'not 1 yr'} tone="var(--status-critical)"
            headline={YEARS ? <>The whole fee package covers {YEARS} year{YEARS === 1 ? '' : 's'} of the gap and is {usdShort(AFTER.short)} short by FY{AFTER.fy}.</> : <>The whole fee package does not cover even next year: {usdShort(AFTER.short)} short in FY{AFTER.fy}, and further behind every year after.</>}>
            A fee is an amount; it grows, at best, with the programme it funds ({pct(DEFAULT_RATES.other, 0)} here). The gap is a rate. So the package that closes {pct(FEES.shareOfGap, 0)} of next year closes less of every year after, and never a whole one. It is the honest first thing to do, and it changes nothing about the direction.
          </Insight>
        </div>
        <NotShown>
          Who stops playing. The peak is where the model&rsquo;s demand curve turns, calibrated to the district&rsquo;s own participation counts; it does not know which children leave a team at $400 or which families are waived. {FEES.unresolved ? <>And one accounting question is open: {FEES.unresolved}</> : null}
        </NotShown>
      </ShortVersion>

      <FullVersion what="each fee, at each price">
        <H2 id="each">Each fee: now, self-funding, and the peak</H2>
        <div className="overflow-x-auto mt-4">
          <table className="text-sm" style={{ minWidth: 720 }}>
            <thead><tr className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>
              <th className="text-left py-2 pr-4">programme</th><th className="text-right py-2 pr-4">costs</th><th className="text-right py-2 pr-4">fee now</th><th className="text-right py-2 pr-4">raises now</th><th className="text-right py-2 pr-4">self-funds at</th><th className="text-right py-2 pr-4">peak fee</th><th className="text-right py-2 pr-4">peak raises</th><th className="text-right py-2">adds</th></tr></thead>
            <tbody>{FEES.cases.map(c => (
              <tr key={c.id} style={{ borderTop: '1px solid var(--grid)' }}>
                <td className="py-2 pr-4 align-top"><span className="font-semibold">{c.label}</span><span className="block text-[11.5px]" style={{ color: 'var(--text-muted)' }}>{c.what}{c.payersKnown ? ` · ${n0(c.payers)} payers` : ''}</span></td>
                <td className="py-2 pr-4 text-right tnum align-top">{usd(c.cost)}</td><td className="py-2 pr-4 text-right tnum align-top">{usd(c.currentFee)}</td><td className="py-2 pr-4 text-right tnum align-top">{usd(c.currentYield)}</td>
                <td className="py-2 pr-4 text-right tnum align-top">{c.selfFund === null ? <span style={{ color: 'var(--status-critical)' }}>never</span> : usd(c.selfFund)}</td>
                <td className="py-2 pr-4 text-right tnum align-top">{usd(c.peakFee)}</td><td className="py-2 pr-4 text-right tnum align-top">{usd(c.peakYield)}</td><td className="py-2 text-right tnum align-top font-semibold">{usd(Math.max(0, c.gain))}</td>
              </tr>))}</tbody>
          </table>
        </div>
        {FEES.cases.some(c => c.caveat) && <div className="mt-3 text-[12.5px] space-y-1" style={{ color: 'var(--text-muted)' }}>{FEES.cases.filter(c => c.caveat).map(c => <p key={c.id}><strong>{c.label}:</strong> {c.caveat}</p>)}</div>}

        <H2 id="years">What the package covers, year by year</H2>
        <Body>The whole {usdShort(FEES.total)}, growing {pct(DEFAULT_RATES.other, 0)} a year with the programmes it funds, against the gap.</Body>
        <div className="overflow-x-auto mt-4">
          <table className="text-sm" style={{ minWidth: 460 }}>
            <thead><tr className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}><th className="text-left py-2 pr-6">year</th><th className="text-right py-2 pr-6">the gap</th><th className="text-right py-2 pr-6">the fees</th><th className="text-right py-2">short by</th></tr></thead>
            <tbody>{GAPS.map((g, i) => { const f = FEES.total * (1 + DEFAULT_RATES.other) ** i; return (
              <tr key={g.fy} style={{ borderTop: '1px solid var(--grid)' }}>
                <td className="py-1.5 pr-6 tnum">FY{g.fy}</td><td className="py-1.5 pr-6 text-right tnum">{usd(g.cumulative)}</td><td className="py-1.5 pr-6 text-right tnum">{usd(f)}</td>
                <td className="py-1.5 text-right tnum" style={{ color: f >= g.cumulative ? 'var(--text-muted)' : 'var(--status-critical)' }}>{f >= g.cumulative ? '—' : usd(g.cumulative - f)}</td>
              </tr>) })}</tbody>
          </table>
        </div>

        <WhoPays>
          The families whose children play, perform or ride &mdash; and, at the peak, the ones who stop. What that comes to per household, with siblings and waivers, is on <a className="underline" href="/what-families-pay">what a family actually pays</a>: the same fees, seen from the kitchen table.
        </WhoPays>
        <DoesNot>
          It does not change the rate, and it does not reach the biggest transport line: {usdShort(FEES.spedTransport)} of special education transport is required and unchargeable. A fee that funds a programme also makes that programme&rsquo;s budget line net of the fee &mdash; rule 11 on this site &mdash; so the line will look smaller without the cost having moved.
        </DoesNot>
        <Settles>the district&rsquo;s participation counts by fee tier for the current year (the demand curve here is calibrated to the last published ones), and the revolving fund&rsquo;s cashbook, which says what the fees actually brought in.</Settles>

        <LeverLinks measures="families" label="What a family actually pays" />
      </FullVersion>

      <MoreReports here={TAB} />
    </ReportShell>
  )
}
