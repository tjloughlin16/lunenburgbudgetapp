import type { Tab } from '../routes'
import { usd, usdShort } from '../model/engine'
import { GAP, GAPS, EXTRACURRICULAR, yearsCovered, shortfallAfter } from '../model/answers'
import { DEFAULT_RATES } from '../model/rates'
import { ReportShell, ShortVersion, Insight, Stat, Grain, NotShown, H2, MoreReports } from '../components/report'
import { FullVersion } from '../components/FullVersion'
import { WhoPays, DoesNot, Settles, LeverLinks, pct, n0 } from '../components/lever'

const TAB: Tab = 'extraslever'

/** CUTTING THE EXTRAS. The first thing said at every meeting -- "cut sports" -- priced
 *  as a lever: every sport, the band, the clubs and the art supplies still being paid
 *  for, what eliminating all of it saves, and for how many years. Only what is funded
 *  can be saved: the adopted FY27 budget already cut most of athletics, and the same
 *  money cannot be cut twice. /what-sports-cost measures the cost; this is what the cut
 *  is worth. Every figure is the model's programme catalogue (answers.EXTRACURRICULAR). */
const E = EXTRACURRICULAR
const YEARS = yearsCovered(E.total, DEFAULT_RATES.other)
const AFTER = shortfallAfter(E.total, DEFAULT_RATES.other)

export function ExtrasLever() {
  return (
    <ReportShell tab={TAB} dataUrl="/data/model.json"
      title="Cutting the extras"
      standfirst={<>Every sport still being paid for, the band and chorus, every club advisor and every art supply, eliminated entirely, comes to {usdShort(E.total)}. That is {pct(E.total / GAP, 0)} of next year&rsquo;s gap {YEARS ? `— ${YEARS} year${YEARS === 1 ? '' : 's'} of it —` : '— not even one year —'} and then the column is empty for ever while the gap comes back every spring. It is the answer that sounds like nothing is lost, and it is less than a year.</>}>

      <Grain>
        A count from the district&rsquo;s own programme catalogue: what is funded outside the classroom in the budget now in force, and what eliminating it would save against the appropriation. Dollars and FTE as budgeted; not what a programme is worth to a child, which no budget line carries.
      </Grain>

      <div className="mt-10 flex flex-wrap gap-x-12 gap-y-6">
        <Stat value={usdShort(E.total)} tone="var(--status-critical)">saved by eliminating everything outside the classroom that is still funded &mdash; {E.fte} FTE</Stat>
        <Stat value={YEARS ? `${YEARS} yr` : 'not 1 yr'} tone="var(--status-critical)">of the gap that covers; short by {usdShort(AFTER.short)} in FY{AFTER.fy}</Stat>
        <Stat value={usdShort(E.alreadyCut)}>of athletics the adopted budget has already cut &mdash; it cannot be cut again</Stat>
        <Stat value={pct(E.total / GAP, 0)}>of next year&rsquo;s {usdShort(GAP)} gap</Stat>
      </div>

      <H2 id="conclusions">If you read nothing else</H2>
      <ShortVersion>
        <div className="grid gap-4 mt-5 md:grid-cols-2">
          <Insight n={1} figure={usdShort(E.total)} tone="var(--status-critical)"
            headline={<>Every extra still funded, gone, saves {usdShort(E.total)} &mdash; {pct(E.total / GAP, 0)} of next year&rsquo;s gap, once.</>}>
            {E.items.slice(0, 4).map(it => `${it.label.toLowerCase()}, ${usd(it.amount)}`).join('; ')}{E.items.length > 4 ? '; and more' : ''}. The whole athletics programme costs {usdShort(E.wholeProgram)}; the budget in force already cut {usdShort(E.alreadyCut)} of it, so what is left to save is {usdShort(E.items.find(i => /sport/i.test(i.label))?.amount ?? 0)}.
          </Insight>
          <Insight n={2} figure={YEARS ? `${YEARS} yr` : 'not 1 yr'}
            headline={YEARS ? <>It buys {YEARS} year{YEARS === 1 ? '' : 's'}. In FY{AFTER.fy} the gap is {usdShort(AFTER.short)} past it, with nothing left outside the classroom to cut.</> : <>It does not buy even one year: {usdShort(AFTER.short)} short in FY{AFTER.fy}, with nothing left outside the classroom to cut.</>}>
            A cut is permanent and so is its saving, but the saving grows at most with the programmes it removed ({pct(DEFAULT_RATES.other, 0)}) and the gap grows {pct(GAPS[1].growthRate, 1)} a year from a base twenty times larger. The line under the extras is classrooms &mdash; which is <a className="underline" href="/classroom-positions">the next page</a>.
          </Insight>
          <Insight n={3} figure={`${E.fte} FTE`}
            headline={<>It is {E.fte} FTE of people &mdash; coaches, advisors, a music teacher &mdash; and {n0(E.items.length)} lines, every one of which has a room of parents.</>}>
            The cut that sounds free is the one with the most people at the meeting. What each programme costs a family in fees, and what the town has already taken off the field, is on <a className="underline" href="/what-sports-cost">what sports cost</a>; this page prices the whole shelf so nobody has to guess whether it reaches.
          </Insight>
        </div>
        <NotShown>
          What a season is worth to a child, what leaves with the students who go elsewhere for it, and what a fee-funded programme actually costs the town net of its fees (rule 11 on this site: the athletics line is already net). The catalogue is dollars budgeted; it does not know who quits.
        </NotShown>
      </ShortVersion>

      <FullVersion what="the whole shelf, line by line">
        <H2 id="lines">What is still funded outside the classroom</H2>
        <div className="overflow-x-auto mt-4">
          <table className="text-sm" style={{ minWidth: 420 }}>
            <thead><tr className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}><th className="text-left py-2 pr-6">line</th><th className="text-right py-2">budgeted</th></tr></thead>
            <tbody>{E.items.map(it => (
              <tr key={it.label} style={{ borderTop: '1px solid var(--grid)' }}><td className="py-1.5 pr-6">{it.label}</td><td className="py-1.5 text-right tnum">{usd(it.amount)}</td></tr>))}
              <tr style={{ borderTop: '2px solid var(--grid)' }} className="font-bold"><td className="py-2 pr-6">All of it</td><td className="py-2 text-right tnum">{usd(E.total)}</td></tr>
            </tbody>
          </table>
        </div>

        <H2 id="years">What the cut covers, year by year</H2>
        <div className="overflow-x-auto mt-4">
          <table className="text-sm" style={{ minWidth: 460 }}>
            <thead><tr className="text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}><th className="text-left py-2 pr-6">year</th><th className="text-right py-2 pr-6">the gap</th><th className="text-right py-2 pr-6">the saving</th><th className="text-right py-2">short by</th></tr></thead>
            <tbody>{GAPS.map((g, i) => { const s = E.total * (1 + DEFAULT_RATES.other) ** i; return (
              <tr key={g.fy} style={{ borderTop: '1px solid var(--grid)' }}>
                <td className="py-1.5 pr-6 tnum">FY{g.fy}</td><td className="py-1.5 pr-6 text-right tnum">{usd(g.cumulative)}</td><td className="py-1.5 pr-6 text-right tnum">{usd(s)}</td>
                <td className="py-1.5 text-right tnum" style={{ color: s >= g.cumulative ? 'var(--text-muted)' : 'var(--status-critical)' }}>{s >= g.cumulative ? '—' : usd(g.cumulative - s)}</td>
              </tr>) })}</tbody>
          </table>
        </div>

        <WhoPays>
          Students, first: every team, ensemble and club on the list. Then the {E.fte} FTE who run them. Then, in a year, the same students again &mdash; because the gap returns and the shelf is empty.
        </WhoPays>
        <DoesNot>
          It does not change the rate. Costs still grow {pct(GAPS[1].growthRate, 1)} a year and the levy {pct(0.025, 1)}; a cut is an amount, and an amount has to be found again. And it cannot be repeated: the {usdShort(E.alreadyCut)} the FY27 budget took from athletics is the proof that this shelf was already reached for once.
        </DoesNot>
        <Settles>the district&rsquo;s programme budget for FY{GAPS[0].fy} when it is published, which will say what is still on this shelf then; and the participation counts, which say who is on it.</Settles>

        <LeverLinks measures="sportsmoney" label="What sports cost, and who pays" />
      </FullVersion>

      <MoreReports here={TAB} />
    </ReportShell>
  )
}
