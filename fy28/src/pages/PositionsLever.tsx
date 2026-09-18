import type { Tab } from '../routes'
import { usd, usdShort } from '../model/engine'
import { GAP, GAPS, EXTRACURRICULAR, yearsCovered } from '../model/answers'
import { DEFAULT_RATES, LEVY_CAP, COST_PER_FTE, HEADCOUNT, CUT_OPTIONS, ALL_CUTS, cutInThings, workforceShrink } from '../model/rates'
import { ALREADY_CUT } from '../model/walk'
import { ReportShell, ShortVersion, Insight, Stat, Grain, NotShown, H2, Body, MoreReports } from '../components/report'
import { FullVersion } from '../components/FullVersion'
import { WhoPays, DoesNot, Settles, LeverLinks, pct, n0 } from '../components/lever'

const TAB: Tab = 'positionslever'

/** CLASSROOM POSITIONS. The lever nobody names first and everybody reaches last: after
 *  the extras, the administrators and the technology, the only lines big enough to
 *  close a gap this size are people in classrooms. This page prices it -- what a
 *  position is worth against the gap, how many the gap is, what the town has already
 *  cut -- and states the one thing the model can say about it as a rate: a line that
 *  grows slower than the pay on it carries fewer people every year. /cut-register
 *  measures what was announced and what shows; this is what the lever is worth. */
const IN_POSITIONS = cutInThings(GAP)
const SHRINK = workforceShrink(LEVY_CAP, DEFAULT_RATES.salaries)
const YEARS_ALL_DISCRETIONARY = yearsCovered(ALL_CUTS, DEFAULT_RATES.other)
const EXTRAS = EXTRACURRICULAR

export function PositionsLever() {
  const fy32 = GAPS[GAPS.length - 1]
  const posBy32 = fy32.cumulative / COST_PER_FTE
  return (
    <ReportShell tab={TAB} dataUrl="/data/model.json"
      title="Classroom positions"
      standfirst={<>Next year&rsquo;s gap is {usdShort(GAP)}: {IN_POSITIONS.positions.toFixed(1)} positions at the district&rsquo;s own {usd(COST_PER_FTE)} a post. Every sport, club, administrator the law allows and most of technology together come to {usdShort(ALL_CUTS)}, which covers {YEARS_ALL_DISCRETIONARY} year{YEARS_ALL_DISCRETIONARY === 1 ? '' : 's'}; after that the only lines big enough are classrooms. The town has already cut {ALREADY_CUT.fte} FTE. This is the lever every other page on this shelf exists to avoid.</>}>

      <Grain>
        Arithmetic on the district&rsquo;s own programme catalogue: the gap divided by the catalogue&rsquo;s cost per full-time position, and the positions already cut in the budget in force. FTE as budgeted, not people by name, and not class sizes &mdash; the district does not publish a headcount by classroom.
      </Grain>

      <div className="mt-10 flex flex-wrap gap-x-12 gap-y-6">
        <Stat value={`${IN_POSITIONS.positions.toFixed(1)} FTE`} tone="var(--status-critical)">next year&rsquo;s gap, in positions at {usd(COST_PER_FTE)} each</Stat>
        <Stat value={`${posBy32.toFixed(1)} FTE`} tone="var(--status-critical)">the FY{fy32.fy} gap in positions, if nothing else moves</Stat>
        <Stat value={`${ALREADY_CUT.fte} FTE`}>already cut in the budget in force &mdash; {usdShort(ALREADY_CUT.cost)}, {ALREADY_CUT.count} lines</Stat>
        <Stat value={`${YEARS_ALL_DISCRETIONARY} yr`}>everything outside the classroom, {usdShort(ALL_CUTS)}, buys before this page is the only one left</Stat>
      </div>

      <H2 id="conclusions">If you read nothing else</H2>
      <ShortVersion>
        <div className="grid gap-4 mt-5 md:grid-cols-2">
          <Insight n={1} figure={`${IN_POSITIONS.positions.toFixed(1)} FTE`} tone="var(--status-critical)"
            headline={<>Cutting classrooms closes the gap only by cutting again every year: {IN_POSITIONS.positions.toFixed(1)} positions next year, {posBy32.toFixed(1)} by FY{fy32.fy}, because the gap grows {pct(GAPS[1].growthRate, 1)} a year.</>}>
            At the catalogue&rsquo;s {usd(COST_PER_FTE)} per position &mdash; salary and benefits, averaged across the roughly {n0(HEADCOUNT)} the salary line pays &mdash; the {usdShort(GAP)} gap is {IN_POSITIONS.positions.toFixed(1)} FTE, {pct(IN_POSITIONS.shareOfBudget, 1)} of the appropriation. A position cut in FY{GAPS[0].fy} stays cut, and the next year&rsquo;s gap asks for more on top.
          </Insight>
          <Insight n={2} figure={`${YEARS_ALL_DISCRETIONARY} yr`}
            headline={<>Everything else that can be cut &mdash; {usdShort(ALL_CUTS)} &mdash; buys {YEARS_ALL_DISCRETIONARY} year{YEARS_ALL_DISCRETIONARY === 1 ? '' : 's'}. After that, classrooms are the only line big enough.</>}>
            {CUT_OPTIONS.map(c => `${c.label.toLowerCase()}, ${usd(c.amount)}`).join('; ')}. That is the whole discretionary shelf, and the gap is {pct(IN_POSITIONS.shareOfDiscretionary, 0)} of it next year alone. Comparable districts found the same: none closed a gap this size with extras.
          </Insight>
          <Insight n={3} figure={`${ALREADY_CUT.fte} FTE`}
            headline={<>The budget in force already cut {ALREADY_CUT.fte} FTE and {usdShort(ALREADY_CUT.cost)} &mdash; four classroom teachers, an interventionist and a half, an assistant principal &mdash; and the projection reopens on top of it.</>}>
            {ALREADY_CUT.people.slice(0, 5).map(p => `${p.label.toLowerCase()} (${p.fte} FTE, ${usd(p.cost)})`).join('; ')}. Not a failure: it is what a {pct(LEVY_CAP, 1)} revenue line against {pct(GAPS[1].growthRate, 1)} costs looks like the year after it happens. Holding the salary line to the cap while pay rises {pct(DEFAULT_RATES.salaries, 0)} is {SHRINK.positionsPerYear.toFixed(1)} positions a year, every year &mdash; the same lever, on a schedule.
          </Insight>
        </div>
        <NotShown>
          Class sizes. The district publishes neither a headcount by classroom nor a class-size report, so what {IN_POSITIONS.positions.toFixed(1)} fewer positions does to a third-grade room is not computable here &mdash; it is the number most worth asking for. Nor does this page say which positions: the catalogue prices an average post, and no post is average.
        </NotShown>
      </ShortVersion>

      <FullVersion what="the arithmetic, and what was already cut">
        <H2 id="gap-in-people">The gap, in positions, year by year</H2>
        <div className="overflow-x-auto mt-4">
          <table className="text-sm" style={{ minWidth: 420 }}>
            <thead><tr className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}><th className="text-left py-2 pr-6">year</th><th className="text-right py-2 pr-6">the gap</th><th className="text-right py-2">in positions</th></tr></thead>
            <tbody>{GAPS.map(g => (
              <tr key={g.fy} style={{ borderTop: '1px solid var(--grid)' }}><td className="py-1.5 pr-6 tnum">FY{g.fy}</td><td className="py-1.5 pr-6 text-right tnum">{usd(g.cumulative)}</td><td className="py-1.5 text-right tnum">{(g.cumulative / COST_PER_FTE).toFixed(1)} FTE</td></tr>))}</tbody>
          </table>
        </div>
        <Body>Cumulative, because a position cut stays cut: the FY{fy32.fy} figure is the total gone by then, not that year&rsquo;s addition.</Body>

        <H2 id="already">What the budget in force already cut</H2>
        <div className="overflow-x-auto mt-4">
          <table className="text-sm" style={{ minWidth: 520 }}>
            <thead><tr className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}><th className="text-left py-2 pr-6">position</th><th className="text-right py-2 pr-6">FTE</th><th className="text-right py-2">cost</th></tr></thead>
            <tbody>{ALREADY_CUT.people.map(p => (
              <tr key={p.id} style={{ borderTop: '1px solid var(--grid)' }}><td className="py-1.5 pr-6">{p.label}</td><td className="py-1.5 pr-6 text-right tnum">{p.fte}</td><td className="py-1.5 text-right tnum">{usd(p.cost)}</td></tr>))}
              <tr style={{ borderTop: '2px solid var(--grid)' }} className="font-bold"><td className="py-2 pr-6">All of it</td><td className="py-2 pr-6 text-right tnum">{ALREADY_CUT.fte}</td><td className="py-2 text-right tnum">{usd(ALREADY_CUT.cost)}</td></tr>
            </tbody>
          </table>
        </div>
        {ALREADY_CUT.unfunded.count > 0 && <Body>And {ALREADY_CUT.unfunded.count} request{ALREADY_CUT.unfunded.count === 1 ? '' : 's'} asked for and never funded, {usdShort(ALREADY_CUT.unfunded.cost)} &mdash; a cut by another name.</Body>}

        <H2 id="shelf">The discretionary shelf, for comparison</H2>
        <Body>Everything outside the classroom that could be cut at all, at its real size. The extras alone are {usdShort(EXTRAS.total)}; the whole shelf is {usdShort(ALL_CUTS)}; the gap next year is {usdShort(GAP)} and grows.</Body>

        <WhoPays>
          Children in larger classes, and the people whose jobs they were. What the town has already asked of them is in the table above; what the cut register shows about earlier rounds &mdash; which announced cuts the state&rsquo;s counts can see and which they cannot &mdash; is on <a className="underline" href="/cut-register">the cut register</a>.
        </WhoPays>
        <DoesNot>
          It does not change the rate either. Fewer positions is a smaller base growing at the same {pct(DEFAULT_RATES.salaries, 0)}; the gap reopens the next year on the smaller base. Only <a className="underline" href="/salaries">the settlement</a> and <a className="underline" href="/health-insurance">health insurance</a> move the rate, and an <a className="underline" href="/override">override</a> moves the other side of it.
        </DoesNot>
        <Settles>a class-size report by school and grade for FY{GAPS[0].fy - 1}, which the district does not publish and could; and DESE&rsquo;s staffing file for the same year, to turn the catalogue&rsquo;s positions into a count.</Settles>

        <LeverLinks measures="cuts" label="The cut register — what was announced, and what shows" />
      </FullVersion>

      <MoreReports here={TAB} />
    </ReportShell>
  )
}
