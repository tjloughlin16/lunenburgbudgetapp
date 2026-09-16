import type { Tab } from '../routes'
import { Go } from '../lib/nav'
import { MODEL, usd, usdShort } from '../model/engine'
import { BASELINE_REVENUE_GROWTH, LEVY_CAP, SHARE, DEFAULT_SCENARIO, DEFAULT_RATES,
         buildRateToHold, newGrowthValueFor, developmentsFor } from '../model/rates'
import { DEVELOPMENT, FEASIBILITY } from '../model/answers'
import { ReportShell, ShortVersion, Insight, Stat, Grain, NotShown, H2, Body, MoreReports } from '../components/report'
import { FullVersion } from '../components/FullVersion'
import { WhatIsADevelopment } from '../components/walk'

const TAB: Tab = 'growth'
const pct = (x: number, d = 1) => `${(x * 100).toFixed(d)}%`

/** COMMERCIAL DEVELOPMENT, AS A REPORT OF ITS OWN.
 *
 *  TJ, 16 September 2026: "Do we have a page/report on commercial development? I don't
 *  see one listed. We may need to extract that from the budget crisis page into its own
 *  report for 'the town' and keeping the high level in the crisis page ... we need
 *  individual reports for the big concepts in the budget crisis."
 *
 *  There was a room on the crisis page (Walkthrough, room 9), a card in its short
 *  version, a question on Straight answers, and a board of dials at /development -- and
 *  no report a resident could be handed. This is that report. It draws the same figures
 *  from the same model (`DEVELOPMENT`, `FEASIBILITY` in model/answers.ts; the build rate
 *  that holds the projection in model/rates.ts), so it cannot disagree with the crisis
 *  page, and it says the thing that page only has room to gesture at: what "grow our way
 *  out" would have to look like on the ground, in buildings, per year, for ever.
 *
 *  RULE 7. Every figure here is the model's arithmetic on the town's tax-base records --
 *  the assessors' new-growth history, the FY23 value by class, the archetype values -- and
 *  it is a projection, labelled so. Nothing here says development will or will not
 *  happen, or should; it says what it would have to be to do the job people ask of it. */

const YEARS = 12
const BUILD_RATE = buildRateToHold(DEFAULT_RATES, YEARS)
const BUILD = BUILD_RATE === null ? null : {
  levy: BUILD_RATE,
  value: newGrowthValueFor(BUILD_RATE),
  developments: developmentsFor(BUILD_RATE),
  multiple: BUILD_RATE / DEFAULT_SCENARIO.newGrowth,
  shareOfExisting: newGrowthValueFor(BUILD_RATE) / DEVELOPMENT.existingBase,
  forThirty: buildRateToHold(DEFAULT_RATES, 30),
}
const T = MODEL.taxBase
const HOME_PAYS = Math.round(T.avgHomeValue * (T.rate / 1000) * T.schoolShareOfBudget)
const HOME_COSTS = Math.round(T.localCostPerPupil / T.homesPerPupil)

export function CommercialDevelopment() {
  const five = DEVELOPMENT.fiveYear
  const F = FEASIBILITY
  const best = DEVELOPMENT.best
  // The assessors certify new growth as levy DOLLARS; the plan is stated in VALUE. Put
  // the best year in the same unit before setting the two beside each other.
  const bestValue = newGrowthValueFor(best.amount)
  return (
    <ReportShell tab={TAB} dataUrl="/data/model.json"
      title="Commercial development is real money and the wrong order of magnitude"
      standfirst={<>What &ldquo;grow our way out of it&rdquo; would have to look like: {usdShort(five.value)} of new commercial value a year, every year, against a town whose best year on record added {usdShort(bestValue)} of new value of every kind &mdash; and the schools keep {(SHARE * 100).toFixed(0)}&cent; of each new dollar.</>}>

      <Grain>
        A projection from the town&rsquo;s own tax-base records &mdash; the assessors&rsquo; new-growth history, the FY23 value by class, and the model&rsquo;s archetype values for what one development is worth. Dollars of assessed value, not buildings that exist. Nothing here says whether any of it will happen.
      </Grain>

      <div className="mt-10 flex flex-wrap gap-x-12 gap-y-6">
        <Stat value={usdShort(five.value)} tone="var(--status-critical)">of new commercial value a year to hold the gap for five years &mdash; {five.developments.toFixed(0)} developments a year, one every {F.everyDays} days</Stat>
        <Stat value={`${(SHARE * 100).toFixed(0)}¢`}>of each new-growth dollar reaches the schools; the rest is the town&rsquo;s</Stat>
        <Stat value={usdShort(bestValue)}>of new value, all classes, in the most Lunenburg has ever added in one year (FY{best.fy})</Stat>
        {BUILD && <Stat value={`${BUILD.multiple.toFixed(1)}×`} tone="var(--status-critical)">today&rsquo;s build rate, sustained for ever, to hold the whole projection from this side alone</Stat>}
      </div>

      <H2 id="conclusions">If you read nothing else</H2>
      <ShortVersion>
        <div className="grid gap-4 mt-5 md:grid-cols-2">
          <Insight n={1} figure={usdShort(five.value)} tone="var(--status-critical)"
            headline={<>Holding the gap for five years takes {usdShort(five.value)} of new commercial value a year &mdash; about {five.developments.toFixed(0)} developments a year, {F.developments5} over the five.</>}>
            That is {pct(five.shareOfBase, 0)} of everything commercial, industrial and personal the town has today, added again every year. The best year on record added {usdShort(bestValue)} of new value of every kind, residential included. Broken into the model&rsquo;s own mix of a &ldquo;typical Lunenburg development&rdquo; it is {F.buildings5} buildings in five years, on {F.parcelsToday} business parcels today.
          </Insight>
          <Insight n={2} figure={`${(SHARE * 100).toFixed(0)}¢`}
            headline={<>The schools keep {(SHARE * 100).toFixed(0)}&cent; of each new-growth dollar. Pricing a development against the school gap without that roughly doubles what it appears to be worth.</>}>
            New growth goes to the town&rsquo;s levy, and the schools get their share of what the town collects &mdash; {pct(T.schoolShareOfBudget, 0)} of it. And the housing half of the same argument: the average home pays about {usd(HOME_PAYS)} a year toward schools and brings about {usd(HOME_COSTS)} of school cost with it. Housing grows the town; it does not close this.
          </Insight>
          {BUILD && (
            <Insight n={3} figure={`${BUILD.multiple.toFixed(1)}×`} tone="var(--status-critical)"
              headline={<>Development is the one answer that moves the revenue <em>rate</em> &mdash; and a flat build rate decays. To do the job it has to accelerate, not merely continue.</>}>
              A fixed number of dollars of new growth each year is a shrinking share of a growing town, which is why {pct(BASELINE_REVENUE_GROWTH, 2)} drifts back toward the {pct(LEVY_CAP, 1)} cap. Holding the projection for {YEARS} years from this side alone takes {BUILD.multiple.toFixed(1)} times today&rsquo;s build rate &mdash; {usdShort(BUILD.value)} a year, {pct(BUILD.shareOfExisting, 0)} of the commercial base{BUILD.forThirty !== null ? <>; for thirty years, {(BUILD.forThirty / DEFAULT_SCENARIO.newGrowth).toFixed(1)} times</> : null}. It is the only lever on the revenue side the town owns, and it is a decade&rsquo;s work before it shows.
            </Insight>
          )}
        </div>
        <NotShown>
          Whether any of this is buildable. The model prices assessed value; it does not know the zoning, the sewer capacity or the market, and the town&rsquo;s own planning documents name the constraint: {F.constraint.replace(/\.$/, '')}. It does not say development is a bad idea &mdash; it says what size of idea it is.
        </NotShown>
      </ShortVersion>

      <FullVersion what="the full analysis">
        <H2 id="one-development">What one &ldquo;development&rdquo; means here</H2>
        <WhatIsADevelopment />

        <H2 id="in-buildings">The five-year plan, in buildings</H2>
        <Body>
          {usdShort(five.value)} a year is a number nobody can picture, and it reads as painless because nobody&rsquo;s pay is cut to get it. In the model&rsquo;s own mix it is this, every year for five years:
        </Body>
        <div className="overflow-x-auto mt-4">
          <table className="w-full text-sm" style={{ minWidth: 560 }}>
            <thead><tr className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>
              <th className="text-left py-2 pr-3">building</th><th className="text-right py-2 pr-3">assessed value each</th><th className="text-right py-2 pr-3">a year</th><th className="text-right py-2">over five years</th></tr></thead>
            <tbody>{F.each.map(e => (
              <tr key={e.label} style={{ borderTop: '1px solid var(--grid)' }}>
                <td className="py-2 pr-3">{e.label}</td>
                <td className="py-2 pr-3 text-right tnum">{usd(e.unit)}</td>
                <td className="py-2 pr-3 text-right tnum">{e.perYear.toFixed(1)}</td>
                <td className="py-2 text-right tnum">{e.over5}</td>
              </tr>))}
              <tr style={{ borderTop: '2px solid var(--grid)' }} className="font-bold">
                <td className="py-2 pr-3">All of it</td><td /><td className="py-2 pr-3 text-right tnum">{F.developmentsPerYear.toFixed(1)}</td><td className="py-2 text-right tnum">{F.buildings5}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <Body>
          Done, it takes the business share of the town&rsquo;s tax base from {pct(F.businessShareNow, 1)} to {pct(F.businessShareAfter, 1)} and the commercial base to {F.multipleOfBase.toFixed(2)} times what it is today. The corridors the town&rsquo;s own planning names for it: {F.corridors.join(', ')}.
          {F.notRealistic ? <> The one building type big enough to shortcut this is a {F.notRealistic.name.toLowerCase()}, and the model&rsquo;s own note on it: {F.notRealistic.note}</> : null}
        </Body>

        <H2 id="history">What the town has actually added, year by year</H2>
        <Body>New growth of every kind &mdash; commercial, industrial, personal property and residential &mdash; as the assessors certified it. The five-year plan above asks for {usdShort(five.value)} of <em>commercial value</em> a year; the table is dollars of new growth <em>revenue</em> as certified, the two are related by the tax rate, and the best year is marked.</Body>
        <div className="overflow-x-auto mt-4">
          <table className="text-sm" style={{ minWidth: 320 }}>
            <thead><tr className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}><th className="text-left py-2 pr-6">year</th><th className="text-right py-2">new growth</th></tr></thead>
            <tbody>{DEVELOPMENT.history.map(h => (
              <tr key={h.fy} style={{ borderTop: '1px solid var(--grid)' }} className={h.fy === best.fy ? 'font-bold' : undefined}>
                <td className="py-1.5 pr-6 tnum">FY{h.fy}</td><td className="py-1.5 text-right tnum">{usd(h.amount)}</td>
              </tr>))}</tbody>
          </table>
        </div>
        <Body>The recent direction of travel by class, FY22 to FY23:</Body>
        <ul className="mt-2 text-sm space-y-1" style={{ color: 'var(--text-secondary)' }}>
          {F.trend.map(v => <li key={v.cls} className="tnum"><strong style={{ color: 'var(--text-primary)' }}>{v.cls}</strong>: {usd(v.fy22)} &rarr; {usd(v.fy23)} ({v.pct >= 0 ? '+' : ''}{pct(v.pct, 1)})</li>)}
        </ul>

        <H2 id="try-it">Try it yourself</H2>
        <Body>
          The board at <Go to="development" className="underline" style={{ color: 'var(--series-cost)' }}>Development</Go> has the dials &mdash; set a commercial build rate and a housing rate and watch what each does to the gap. The same arithmetic, the same model; this page is the settled reading of it.
        </Body>
        <Body>
          The wider argument &mdash; why an amount cannot fix a rate problem, and which lines can &mdash; is on the <Go to="walk" className="underline" style={{ color: 'var(--series-cost)' }}>crisis page</Go>; the options side by side are on <Go to="solutions" className="underline" style={{ color: 'var(--series-cost)' }}>Solutions</Go>.
        </Body>
      </FullVersion>

      <MoreReports here={TAB} />
    </ReportShell>
  )
}
