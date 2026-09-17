import type { Tab } from '../routes'
import { MODEL, usd, usdShort } from '../model/engine'
import { GAP, GAPS, yearsCovered, shortfallAfter } from '../model/answers'
import { ReportShell, ShortVersion, Insight, Stat, Grain, NotShown, H2, Body, MoreReports } from '../components/report'
import { FullVersion } from '../components/FullVersion'
import { WhoPays, DoesNot, Settles, LeverLinks, pct, n0 } from '../components/lever'

const TAB: Tab = 'freecashlever'

/** CAN FREE CASH FILL THE GAP. TJ, 17 September 2026: "can we use it to fill the gap?
 *  ... having a page that answers 'can we be more conservative and prevent money going
 *  to free cash to solve the school budget problem' would be useful."
 *
 *  /free-cash measures the THING: what free cash is, whether the town is hoarding or
 *  rebuilding, how nine towns compare. This page is the LEVER: what redirecting it is
 *  worth, for how many years, and what it takes from -- because free cash is the
 *  capital programme's largest source, so "spend it on the schools" is "do not do
 *  these projects". And it answers the question as put: budgeting tighter so less lands
 *  in free cash is the same money seen a year earlier, and a rate does not care which
 *  year it is seen in. Every figure is the model's (MODEL.freeCash, answers.ts). */
const FC = MODEL.freeCash
const CAP = FC.capital
const REDIRECT = Math.round(FC.certified - FC.bandLow * FC.budgetBase)            // inside the town's own guideline
const NORMAL_REDIRECT = Math.max(0, Math.round(FC.normalCertified - FC.bandLow * FC.budgetBase))
const YEARS_AT_REDIRECT = yearsCovered(REDIRECT, 0)
const AFTER = shortfallAfter(REDIRECT, 0)
const YEARS_ALL = yearsCovered(FC.certified, 0)

export function FreeCashLever() {
  const draw = CAP?.atDraw?.find(d => d.redirect === CAP.redirectCeiling) ?? CAP?.atDraw?.[CAP.atDraw.length - 4]
  return (
    <ReportShell tab={TAB} dataUrl="/data/model.json"
      title="Can free cash fill the gap?"
      standfirst={<>In a year like this one, about {usdShort(REDIRECT)} of free cash could go to the schools without breaching the town&rsquo;s own {pct(FC.bandLow, 0)}&ndash;{pct(FC.bandHigh, 0)} guideline. That covers next year. It is one-time money against a gap that grows every year, it is the capital plan&rsquo;s money, and budgeting tighter so less of it appears does not change the arithmetic &mdash; it moves the same dollars a year earlier.</>}>

      <Grain>
        A projection from the town&rsquo;s certified free cash, its own stated guideline, and the capital plan&rsquo;s own funding table. Dollars the town has certified and could appropriate; not a prediction of next year&rsquo;s certification, which depends on what is left unspent.
      </Grain>

      <div className="mt-10 flex flex-wrap gap-x-12 gap-y-6">
        <Stat value={usdShort(REDIRECT)} tone="var(--series-revenue)">a year could go to the schools inside the guideline, in a year like FY{CAP?.lastYear?.fy ?? 2026}</Stat>
        <Stat value={`${YEARS_AT_REDIRECT} year${YEARS_AT_REDIRECT === 1 ? '' : 's'}`} tone="var(--status-critical)">of the gap that covers; by FY{AFTER.fy} the gap is {usdShort(AFTER.short)} beyond it</Stat>
        <Stat value={usdShort(FC.normalCertified)}>certified in an ordinary year &mdash; {pct(FC.normalShare, 1)} of the budget, already under the {pct(FC.bandLow, 0)} floor, {NORMAL_REDIRECT ? usdShort(NORMAL_REDIRECT) : 'nothing'} to redirect</Stat>
        <Stat value={CAP?.lastYear ? `${CAP.lastYear.redirectAsMultiple.toFixed(1)}×` : '—'}>what free cash gave the capital plan last year, the redirect is that many times over</Stat>
      </div>

      <H2 id="conclusions">If you read nothing else</H2>
      <ShortVersion>
        <div className="grid gap-4 mt-5 md:grid-cols-2">
          <Insight n={1} figure={usdShort(REDIRECT)} tone="var(--series-revenue)"
            headline={<>Yes, once: about {usdShort(REDIRECT)} of this year&rsquo;s {usdShort(FC.certified)} could go to the schools inside the town&rsquo;s own guideline, and it covers the FY{GAPS[0].fy} gap of {usdShort(GAP)}.</>}>
            The town certified {usdShort(FC.certified)}, {pct(FC.currentShare, 2)} of the budget, against a stated aim of {pct(FC.bandLow, 0)}&ndash;{pct(FC.bandHigh, 0)}. Everything above the floor is {usdShort(REDIRECT)}. Spend it on the schools and next year is closed. That is a true sentence and it is where most of the argument in town stops.
          </Insight>
          <Insight n={2} figure={`${YEARS_AT_REDIRECT} yr`} tone="var(--status-critical)"
            headline={<>It covers {YEARS_AT_REDIRECT} year{YEARS_AT_REDIRECT === 1 ? '' : 's'}. The gap is a rate, and by FY{AFTER.fy} it is {usdShort(AFTER.short)} past what the same {usdShort(REDIRECT)} can reach.</>}>
            This year was a record: an ordinary year certifies {usdShort(FC.normalCertified)}, {pct(FC.normalShare, 1)} of the budget, already below the floor, with {NORMAL_REDIRECT ? usdShort(NORMAL_REDIRECT) : 'nothing'} to redirect. Even the whole {usdShort(FC.certified)}, guideline ignored, covers {YEARS_ALL} year{YEARS_ALL === 1 ? '' : 's'}. Free cash is last year&rsquo;s underspend; it cannot be counted on, and it cannot grow at {pct(GAPS[1].growthRate, 1)} a year the way the gap does.
          </Insight>
          <Insight n={3} figure={CAP?.lastYear ? `${CAP.lastYear.redirectAsMultiple.toFixed(1)}×` : '—'}
            headline={<>It is the capital plan&rsquo;s money: {usdShort(REDIRECT)} is {CAP?.lastYear ? CAP.lastYear.redirectAsMultiple.toFixed(1) : '—'}&times; what free cash gave capital last year, and more than that whole share in {CAP?.yearsRedirectExceedsFreeCash ?? '—'} of the {CAP?.yearsCovered ?? '—'} years the plan publishes.</>}>
            Free cash funded {usdShort(CAP?.lastYear?.freeCash ?? 0)} of last year&rsquo;s {usdShort(CAP?.lastYear?.total ?? 0)} capital plan. At the redirect, {draw && CAP ? `${draw.projects.length} of the plan’s ${CAP.queueCount} queued projects` : 'most of the plan'} go unfunded &mdash; {draw ? draw.projects.slice(0, 3).map(p => p.project.replace(/\s*\(.*\)$/, '')).join(', ') : ''}{draw && draw.projects.length > 3 ? ', and more' : ''}. &ldquo;Available within the guideline&rdquo; and &ldquo;available&rdquo; are not the same sentence.
          </Insight>
        </div>
        <NotShown>
          Whether the capital plan is the right size, or whether any project in it could wait. This page prices what the redirect takes; it does not rank a roof against a teacher. Nor does it predict next year&rsquo;s certification: free cash is what was left unspent, and this year&rsquo;s {usdShort(FC.unspent2025)} of underspending was {(FC.unspent2025 / FC.unspentAvg).toFixed(1)}&times; the recent average.
        </NotShown>
      </ShortVersion>

      <FullVersion what="the arithmetic, and the question as put">
        <H2 id="tighter">&ldquo;Can we budget tighter so less goes to free cash?&rdquo;</H2>
        <Body>
          Free cash is money the town appropriated and did not spend, plus revenue above the estimate, certified the following July. Budgeting closer to the bone this year means less is certified next year &mdash; and the same dollars, appropriated to the schools directly instead of arriving as free cash a year later. It is not a different pot. It is the same pot, seen a year earlier, and it is still one year&rsquo;s worth. The gap grows {pct(GAPS[1].growthRate, 1)} a year whichever year the money is counted in.
        </Body>
        <Body>
          What tighter budgeting <em>does</em> change is the cushion. Local receipts have beaten the estimate in every one of the years on record here (the measurement is on <a className="underline" href="/free-cash">the free cash report</a>); a tighter estimate is a real choice, and its cost is a year in which they do not.
        </Body>

        <H2 id="years">What the redirect covers, year by year</H2>
        <div className="overflow-x-auto mt-4">
          <table className="text-sm" style={{ minWidth: 520 }}>
            <thead><tr className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>
              <th className="text-left py-2 pr-6">year</th><th className="text-right py-2 pr-6">the gap</th><th className="text-right py-2 pr-6">{usdShort(REDIRECT)} a year covers</th><th className="text-right py-2">short by</th></tr></thead>
            <tbody>{GAPS.map(g => (
              <tr key={g.fy} style={{ borderTop: '1px solid var(--grid)' }}>
                <td className="py-1.5 pr-6 tnum">FY{g.fy}</td><td className="py-1.5 pr-6 text-right tnum">{usd(g.cumulative)}</td>
                <td className="py-1.5 pr-6 text-right tnum">{REDIRECT >= g.cumulative ? 'all of it' : pct(REDIRECT / g.cumulative, 0)}</td>
                <td className="py-1.5 text-right tnum" style={{ color: REDIRECT >= g.cumulative ? 'var(--text-muted)' : 'var(--status-critical)' }}>{REDIRECT >= g.cumulative ? '—' : usd(g.cumulative - REDIRECT)}</td>
              </tr>))}</tbody>
          </table>
        </div>

        <H2 id="capital">What it takes from</H2>
        <div className="overflow-x-auto mt-4">
          <table className="text-sm" style={{ minWidth: 420 }}>
            <thead><tr className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>
              <th className="text-left py-2 pr-6">year</th><th className="text-right py-2 pr-6">capital plan</th><th className="text-right py-2">of it from free cash</th></tr></thead>
            <tbody>{(CAP?.history ?? []).map(h => (
              <tr key={h.fy} style={{ borderTop: '1px solid var(--grid)' }}>
                <td className="py-1.5 pr-6 tnum">FY{h.fy}</td><td className="py-1.5 pr-6 text-right tnum">{usd(h.total)}</td><td className="py-1.5 text-right tnum">{usd(h.freeCash)} <span style={{ color: 'var(--text-muted)' }}>({pct(h.freeCash / h.total, 0)})</span></td>
              </tr>))}</tbody>
          </table>
        </div>

        <WhoPays>
          The capital plan: the roof, the cruiser, the bridge that were next in the queue. {CAP?.restrictedTotal ? <>About {usdShort(CAP.restrictedTotal)} of it is restricted money that could not move anyway; the {usdShort(CAP.convertibleTotal)} that could is what the redirect competes with.</> : null} And, in a year that is not a record, nobody &mdash; because there is nothing above the floor to move.
        </WhoPays>
        <DoesNot>
          It does not change the rate. Costs grow {pct(GAPS[1].growthRate, 1)} a year and the levy {pct(0.025, 1)}; a one-time appropriation, however large, leaves both where they were, and the same gap is back the next spring plus growth. The two things that change the rate are on <a className="underline" href="/what-changing-the-health-plan-does">the health plan</a> and <a className="underline" href="/what-the-contract-decides">the contract</a>.
        </DoesNot>
        <Settles>the Town Accountant&rsquo;s free cash certification for 1 July {n0(GAPS[0].fy - 1)} (the next one), which says whether this year&rsquo;s record repeats; and the capital plan&rsquo;s adopted FY{GAPS[0].fy} funding table, which says what a redirect would actually displace.</Settles>

        <LeverLinks measures="freecash" label="Is the town hoarding free cash, or rebuilding it?" />
      </FullVersion>

      <MoreReports here={TAB} />
    </ReportShell>
  )
}
