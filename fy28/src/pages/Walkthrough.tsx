import { usd, usdShort, COST_GROWTH_BLENDED } from '../model/engine'
import {
  ALREADY_CUT, ALREADY_SAID, LEVEL_SERVICE,
} from '../model/walk'
import {
  BASELINE_REVENUE_GROWTH, LEVY_CAP, RATE_LINES, DEFAULT_SCENARIO, STATE_AID,
  nextYear, overrideForYears, longRunTarget, salaryRateToBalance, workforceShrink,
  DEFAULT_RATES, ch70OnlyGrowth, aidGrowthToSustain, SHARE, HEADCOUNT,
} from '../model/rates'
import { ADMIN, DEVELOPMENT } from '../model/answers'
import { MODEL } from '../model/engine'
import { Room, Say, Plate, AlreadyCut, OneTimeAnswers, WhatIsADevelopment } from '../components/walk'
import { TheRaise } from '../components/TheRaise'
import { RateBoard } from '../components/RateBoard'
import { OverrideSizing, OverrideTreadmill, OverrideExplorer } from '../components/LevelVsSlope'
import { PriceList } from '../components/PriceList'
import { Forever } from '../components/Forever'
import { Note } from '../components/primitives'

const pct = (x: number, d = 2) => `${(x * 100).toFixed(d)}%`
const N = nextYear()
const T = longRunTarget(DEFAULT_SCENARIO)
/** The two halves of the housing question, from the tax base rather than typed out. */
const HOME_PAYS = Math.round(MODEL.taxBase.avgHomeValue * (MODEL.taxBase.rate / 1000)
  * MODEL.taxBase.schoolShareOfBudget)
const HOME_COSTS = Math.round(MODEL.taxBase.localCostPerPupil / MODEL.taxBase.homesPerPupil)

/** The walkthrough: the same facts, in the order somebody has to meet them.
 *
 *  The tabbed site answers questions. This answers them in sequence, for a visitor who
 *  arrives with no question yet — which is almost everybody. Every room corrects exactly
 *  one belief, shows one object, and hands over one sentence, and the order is
 *  load-bearing: each room depends on the one before it and none depends on the one after.
 *
 *  Built alongside the tabs rather than instead of them, so nothing that works breaks while
 *  this is still wrong in places. */
export function Walkthrough({ onJump }: {
  onJump: (tab: 'money' | 'override' | 'curve' | 'adjust' | 'context' | 'answers'
    | 'deeper') => void
}) {
  const cuts = ALREADY_CUT
  const ranked = RATE_LINES.slice().sort((a, b) => b.swing - a.swing)
  const salaryAt4 = salaryRateToBalance({ ...DEFAULT_RATES, health: 0.04 }, T)
  const shrink = workforceShrink(Math.max(salaryRateToBalance(DEFAULT_RATES, T), 0), 0.04)
  const aidRate = aidGrowthToSustain(DEFAULT_SCENARIO)!
  const five = overrideForYears(5)
  const two = overrideForYears(2)

  return (
    <div>
      <div className="mx-auto max-w-6xl px-5 pt-14 pb-10">
        <p className="text-xs font-semibold uppercase tracking-widest mb-3"
          style={{ color: 'var(--text-muted)' }}>Start here &middot; eleven steps</p>
        <h1 className="text-3xl sm:text-5xl font-bold tracking-tight leading-[1.05] max-w-3xl">
          Why the school budget keeps doing this
        </h1>
        <p className="mt-5 text-[16px] leading-relaxed max-w-2xl"
          style={{ color: 'var(--text-secondary)' }}>
          Eleven steps, in order, assuming you know nothing about the budget. Each one
          answers a single question and hands you one sentence. You can stop after any of
          them and the thing you took away will still be true.
        </p>
        <Note>
          Every figure comes from the town&rsquo;s published FY27 budget and tax records.
          FY28 onward are projections. Nothing here is rounded to flatter an argument.
        </Note>
      </div>

      {/* ------------------------------------------------ 01 */}
      <Room n={1} tag="Where you already are"
        title="You have already been told the number"
        leave={<>Everyone agrees on the number, the town has already given real things up,
          and nobody has explained why it keeps happening.</>}>
        <Say>
          The schools are short <strong>{usd(LEVEL_SERVICE.gap)}</strong> next year. You
          have probably heard that. You may also have heard that the schools always need
          more, that the problem is administration, or that nothing has been tightened.
        </Say>
        <Say>
          Start with what the town has already done about it. Two override questions, both
          defeated. And a budget that cut <strong>{cuts.fte} positions</strong>.
        </Say>
        <Plate label="On the wall" figures={[
          { v: usdShort(LEVEL_SERVICE.gap), k: 'short in FY28', tone: 'critical' },
          { v: `${cuts.fte} FTE`, k: 'positions already cut last year', tone: 'critical' },
          { v: '0 of 2', k: 'override questions passed' },
          { v: `$${ALREADY_SAID.overrides[0].cost} · $${ALREADY_SAID.overrides[1].cost}`,
            k: 'what each would have added to the average tax bill' },
        ]} />
        <AlreadyCut />
        <Say>
          That list matters before anything else does. The rest of this explains why the
          hole came back anyway &mdash; which is a different question from whether anybody
          tried.
        </Say>
      </Room>

      {/* ------------------------------------------------ 02 */}
      <Room n={2} tag="What the ask is"
        title="&ldquo;More money&rdquo; means the same schools, one year older"
        corrects={<>&ldquo;The schools keep asking for more.&rdquo;</>}
        leave={<>The ask is not for more schooling. It is for the same schooling at next
          year&rsquo;s prices.</>}>
        <Say>
          Everything here turns on one phrase that budget documents use and nobody
          explains. <strong>Level service</strong> means the same staff, the same buses,
          the same buildings, the same {LEVEL_SERVICE.enrollment.toLocaleString()} children.
          Nobody is hired. Nothing is added. No programme comes back.
        </Say>
        <Plate label="What standing still costs" figures={[
          { v: usdShort(LEVEL_SERVICE.fy27), k: 'the town gave the schools this year' },
          { v: `+${usd(LEVEL_SERVICE.increase)}`, k: 'what the identical thing costs next year',
            tone: 'critical' },
        ]} />
        <Say>
          This is the school budget&rsquo;s cost of living, and no committee voted for it.
          Salaries rise under an agreement signed in 2024. Health insurance rises because
          the insurance market says so. Out-of-district special education rises at rates
          the state sets.
        </Say>
      </Room>

      {/* ------------------------------------------------ 03 */}
      <Room n={3} tag="What the town can give"
        title={<>The town can give {usd(N.allowed)} more, and that is the ceiling</>}
        corrects={<>&ldquo;The town is choosing not to fund the schools.&rdquo;</>}
        leave={<>The limit is a law from 1980, not a decision by anybody currently in the
          room.</>}>
        <Say>
          Proposition 2&frac12; &mdash; a 1980 statewide ballot question &mdash; caps how
          much more a town may collect at {pct(LEVY_CAP, 1)} a year. New growth, state aid
          and local receipts top that up to about {pct(BASELINE_REVENUE_GROWTH)}. That is
          the whole increase.
        </Say>
        <Plate label={`Where the ${usdShort(N.allowed)} comes from`}
          figures={N.sources.map(s => ({ v: usd(s.toSchools), k: s.note }))} />
        <Say>
          And the fact that reframes the argument: <strong>2&frac12;% was never indexed to
          what municipal costs actually do.</strong> It is a number chosen in 1980. Health
          insurance did not agree to it.
        </Say>
      </Room>

      {/* ------------------------------------------------ 04 */}
      <Room n={4} tag="The subtraction"
        title={<>Costs want {usd(N.costTotal)}. Revenue offers {usd(N.allowed)}.</>}
        corrects={<>&ldquo;There must be waste in there somewhere.&rdquo;</>}
        leave={<>The deficit is a subtraction, and you have now watched it being done.</>}>
        <Say>
          Now the number you were handed in room one stops being handed down and starts
          being derived. Put the increase on the table as a fixed quantity, and let each
          cost line take its bite in the order it takes it.
        </Say>
        <TheRaise />
      </Room>

      {/* ------------------------------------------------ 05 */}
      <Room n={5} tag="Whose fault it is"
        title="Only one line in the budget lives within its means"
        corrects={<>&ldquo;Salaries are eating the budget&rdquo; &mdash; the biggest line
          looks guiltiest, and is not.</>}
        leave={<>The lines that overrun are not the lines anybody in Lunenburg sets. The
          line that fits is the only one they do.</>}>
        <Say>
          That last chart is the fair version of the question, and it is worth staying with
          for a moment. Salaries take more of the increase than anything else because they
          are {pct(ranked.find(l => l.key === 'salaries')!.weight, 0)} of the budget. Health
          insurance takes almost three times its share on{' '}
          {pct(ranked.find(l => l.key === 'health')!.weight, 0)} of it.
        </Say>
        <Say>
          And the only line that fits is &ldquo;everything else&rdquo; &mdash; supplies,
          materials, technology, athletics, clubs. The one line the School Committee fully
          controls. <strong>Both things are true at once:</strong> the district has cut
          deeply, including {cuts.fte} positions last year, and the line it fully controls
          is the one already living within its means.
        </Say>
      </Room>

      {/* ------------------------------------------------ 06 */}
      <Room n={6} tag="The centrepiece" handsOn
        title="Two rates, and they were never going to meet"
        corrects={<>&ldquo;We cut last year. Why are we back?&rdquo;</>}
        leave={<>Cuts change the amount. Only rates change the direction. Last year&rsquo;s
          cut was never going to stop this year&rsquo;s hole.</>}>
        <div className="card p-5 sm:p-6" style={{ borderColor: 'var(--status-critical)',
                                                  borderWidth: 2 }}>
          <p className="text-[17px] sm:text-xl leading-snug font-medium">
            Last year Lunenburg cut <strong>{cuts.fte} positions</strong> and{' '}
            <strong>{usd(cuts.cost)}</strong> &mdash; four classroom teachers, an
            interventionist and a half, an assistant principal, a custodian, half the
            athletic trainer. Next year the schools are short{' '}
            <strong style={{ color: 'var(--status-critical)' }}>
              {usd(LEVEL_SERVICE.gap)}</strong>.
          </p>
        </div>
        <Say>
          The town has already run this experiment. The painful thing was done and the hole
          came back bigger, and that is better evidence than any chart. What follows is
          why.
        </Say>
        <Say>
          Costs compound at {pct(COST_GROWTH_BLENDED)} a year. Revenue compounds at{' '}
          {pct(BASELINE_REVENUE_GROWTH)}, drifting toward {pct(LEVY_CAP, 1)} as a flat
          new-growth figure becomes a smaller share of a bigger town. Two things compounding
          at different speeds pull apart for ever, and the distance between them grows on
          its own whether or not anybody does anything wrong.
        </Say>
        <Say>
          <strong>Try it.</strong> Tick every box in the left column &mdash; every sport,
          the band, the clubs, most of technology, every administrator the law allows. Watch
          the growth rate underneath that column refuse to move, and watch the year squares
          go green and then red again. Then drag one rate on the right instead.
        </Say>
        {/* Pinned, and sitting under the room heading rather than beside it. The curve
            and the funded-year squares are the room's whole argument: a reader dragging a
            slider has to be able to see them move without scrolling away from the control
            doing the moving. The offset is taller at sm and up because the heading's title
            sets larger there and can take two lines. */}
        <RateBoard stickyTop="top-[136px] sm:top-[156px]" />
      </Room>

      {/* ------------------------------------------------ 07 */}
      <Room n={7} tag="The cuts you feel" handsOn
        title="What the things you would cut are actually worth"
        corrects={<>&ldquo;Cut the administrators.&rdquo; &middot; &ldquo;Cut sports before
          you cut classrooms.&rdquo;</>}
        leave={<>Athletics is a third of one year and none of the problem. That is not an
          argument for cutting it. It is an argument that cutting it was never the
          answer.</>}>
        <Say>
          This room owes you a straight answer about the two cuts people feel most, and it
          is not going to flinch. Every remaining sport &mdash; 25 of them, 691
          student-seasons, every coach &mdash; is{' '}
          {usd(MODEL.facts.athleticsRemaining as number)}. Every administrative and office
          line the law allows the district to cut is {usd(ADMIN.lawful)}.
        </Say>
        <OneTimeAnswers />
        <Say>
          The two cheapest-looking rows are the only two that change anything, and the
          loudest argument in town is worth nothing structurally at all.
        </Say>
        <Say>
          <strong>Try it.</strong> Pick a number you think the town should find, and see
          what every lever would have to do to raise it &mdash; and how many of them
          cannot, at any price.
        </Say>
        <PriceList />
      </Room>

      {/* ------------------------------------------------ 08 */}
      <Room n={8} tag="The revenue answer" handsOn
        title="What one override actually buys"
        corrects={<>&ldquo;An override would fix this&rdquo; &middot; &ldquo;Overrides are
          just the schools coming back again.&rdquo;</>}
        leave={<>An override is not one vote. It is either a smaller one every spring for
          ever, or a very large one whose first years collect far more than the schools
          need.</>}>
        <Say>
          Both sides of this argument are wrong in the same way: they think an override is a
          payment. It is a permanent lift to the town&rsquo;s levy limit, which then
          compounds at {pct(LEVY_CAP, 1)} like the rest of the limit. Three things follow,
          and two of them are good news nobody has told the town.
        </Say>
        <Plate label="The two nobody mentions" figures={[
          { v: `${(SHARE * 100).toFixed(0)}¢`, k: 'what the schools keep of a town-wide override dollar — a school-only question keeps all of it', tone: 'good' },
          { v: usdShort(two.levy), k: `a school question covering two years, at $${two.onAverageHome} on the average home`, tone: 'good' },
          { v: usdShort(five.levy), k: `and five years, at $${five.onAverageHome} — but see what it over-collects` },
        ]} />
        <Say>
          The two questions Lunenburg put up and lost were town-wide, covering every
          department. Written for the schools alone, the same money does nearly twice the
          work here.
        </Say>
        <OverrideSizing />
        <Say>
          <strong>Try it.</strong> Each notch is the smallest override that funds one more
          year. Watch the ballot figure, the tax bill and the over-collection move together
          &mdash; they are three views of one decision.
        </Say>
        <OverrideExplorer />
        <Say>
          And the alternative to one big question: a smaller one, every spring, for ever.
        </Say>
        <OverrideTreadmill />
      </Room>

      {/* ------------------------------------------------ 09 */}
      <Room n={9} tag="The growth answer"
        title="What commercial development would have to look like"
        corrects={<>&ldquo;Commercial development will grow us out of this.&rdquo;</>}
        leave={<>Commercial development is real money and the wrong order of magnitude
          &mdash; and it has to accelerate, not merely continue.</>}>
        <Say>
          The right instinct, priced honestly. Two facts do all the work here, and neither
          is in general circulation.
        </Say>
        <Plate label="On the wall" figures={[
          { v: `${(SHARE * 100).toFixed(0)}¢`, k: 'of each new-growth dollar reaches the schools — the rest is the town’s' },
          { v: usdShort(DEVELOPMENT.fiveYear.value),
            k: 'of new commercial value a year to hold the gap for five years' },
          { v: DEVELOPMENT.fiveYear.developments.toFixed(0),
            k: 'developments a year — see below for what one of those is' },
          { v: `${usd(HOME_PAYS)} · ${usd(HOME_COSTS)}`,
            k: 'what an average home pays toward schools, and the school cost it brings' },
        ]} />
        <WhatIsADevelopment />
        <Say>
          The first is that <strong>the schools keep {(SHARE * 100).toFixed(0)}&cent; of
          each new-growth dollar</strong>. New growth goes to the town&rsquo;s levy, and the
          schools get their share of what the town collects. Pricing development against the
          school gap without that roughly doubles what a new development appears to be worth.
        </Say>
        <Say>
          The second has not been said out loud anywhere in town: <strong>a flat build rate
          decays as a rate.</strong> A fixed number of dollars of new growth each year is a
          shrinking share of a growing town, which is exactly why{' '}
          {pct(BASELINE_REVENUE_GROWTH)} drifts back toward {pct(LEVY_CAP, 1)}. To work as a
          rate rather than as a one-off, the rate of new commercial construction has to
          keep rising.
        </Say>
        <Say>
          And the housing half, which settles a separate argument: the average home pays
          about {usd(HOME_PAYS)} a year toward schools and brings about {usd(HOME_COSTS)} of
          school cost with it. Housing grows the town. It does not close this.
        </Say>
      </Room>

      {/* ------------------------------------------------ 10 */}
      <Room n={10} tag="The advocacy answer"
        title="What winning at the State House would have to mean"
        corrects={<>&ldquo;Fix Chapter 70 and we&rsquo;re fine.&rdquo;</>}
        leave={<>Worth asking the delegation for. Not worth planning around.</>}>
        <Say>
          The one route where nobody in Lunenburg gives anything up, so it deserves a number
          rather than a wish. First untangle two figures that get conflated constantly: all
          state aid is {usdShort(STATE_AID.total)}, and Chapter 70 school aid is{' '}
          {usdShort(STATE_AID.chapter70)} of it.
        </Say>
        <Plate label="On the wall" figures={[
          { v: pct(STATE_AID.shareOfTownRevenue, 0), k: 'of town revenue is state aid — which is why the rate has to be so high' },
          { v: pct(ch70OnlyGrowth(aidRate)), k: 'annual growth Chapter 70 alone would need, for ever', tone: 'critical' },
          { v: '+$833,340', k: 'extra in the first year' },
          { v: '$64.2M', k: 'extra over ten years' },
        ]} />
        <Say>
          The reason the rate has to be so steep is that aid is only{' '}
          {pct(STATE_AID.shareOfTownRevenue, 0)} of what the town collects. Fixing a{' '}
          {pct(COST_GROWTH_BLENDED)} cost rate by moving a quarter of the revenue means
          moving that quarter very hard.
        </Say>
        <Say>
          And the fact that should shape the ask: the town already spends{' '}
          {usdShort(STATE_AID.aboveFoundation)} above its foundation budget, which is not
          where the formula sends money. Worth knowing before writing the letter, because it
          tells you what to ask for.
        </Say>
      </Room>

      {/* ------------------------------------------------ 11 */}
      <Room n={11} tag="What it would take" handsOn
        title="What &ldquo;solved&rdquo; would actually require"
        corrects={<>&ldquo;There must be a version of this where nobody gets hurt.&rdquo;</>}
        leave={<>There is no painless version. There is a choice between kinds of pain, and
          only one of the kinds ends the conversation.</>}>
        <Say>
          Permanent balance has exactly one condition: everything the district buys has to
          grow no faster than <strong>{pct(T)}</strong> a year, which is where the
          town&rsquo;s revenue settles once a flat new-growth figure has finished shrinking
          as a share.
        </Say>
        <Say>
          Four of the six lines are fixed by contract, state law or the market. So salaries
          are the residual, and the honest question is not whether the town can hold them to
          a number, but what is left for them once insurance has taken its share.
        </Say>
        <Plate label="Leave insurance where it is, and balance on headcount alone" figures={[
          { v: pct(Math.max(salaryRateToBalance(DEFAULT_RATES, T), 0)), k: 'the salary line would have to grow this slowly', tone: 'critical' },
          { v: `${shrink.positionsPerYear.toFixed(1)}`, k: 'positions shed in the first year, and more every year after' },
          { v: `−${pct(shrink.after20, 0)}`, k: 'of the workforce after twenty years', tone: 'critical' },
          { v: pct(salaryAt4), k: 'what salaries could grow at instead, if insurance came to 4%', tone: 'good' },
        ]} />
        <Say>
          <strong>Try it.</strong> Move the health insurance assumption down the table below
          and watch what it leaves for salaries &mdash; and tick the box to hold the four
          small lines to the cap as well. Read the other way, nobody loses a job and the
          settlement itself lands near {pct(salaryAt4)}: roughly flat pay, permanently, for
          about {HEADCOUNT} people. Any mix of the two works. What does not work is neither.
        </Say>
        <Forever />
      </Room>

      {/* The exit, which is not a room.
       *
       * It was inside room 11, which made that room both an exploration and a conclusion
       * and put a "hands on" badge over a heading whose tag read "the exit". A room that
       * ends the walkthrough should not also open a new question. */}
      <section id="exit" className="scroll-mt-12 border-t py-14"
        style={{ borderColor: 'var(--grid)', background: 'var(--surface-1)' }}>
        <div className="mx-auto max-w-6xl px-5">
          <p className="text-xs font-semibold uppercase tracking-widest mb-3"
            style={{ color: 'var(--text-muted)' }}>The way out</p>
          <h2 className="text-2xl sm:text-3xl font-bold tracking-tight leading-[1.15]
                         mb-4 max-w-3xl">
            So the choice is not between a good option and a bad one
          </h2>
          <p className="text-[16px] leading-relaxed max-w-2xl mb-6"
            style={{ color: 'var(--text-secondary)' }}>
            It is between funding next April and being back here in twelve months, or
            changing one of two rates that nobody in this town sets alone &mdash; a health
            insurance contract the Town buys, and an agreement bargained three years at a
            time. Everything else on this site is a way of checking that for yourself.
          </p>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {([
              ['adjust', 'Build your own budget', 'Every dial that moves the gap, on one page'],
              ['curve', 'Bend the curve', 'Cut things, then change a rate, and watch which one works'],
              ['answers', 'Straight answers', 'The questions people ask, answered one at a time'],
              ['deeper', 'Go deeper', 'Everything this walkthrough left out, and where the numbers come from'],
            ] as const).map(([id, label, what]) => (
              <button key={id} onClick={() => onJump(id)}
                className="card p-4 text-left transition-opacity hover:opacity-90">
                <span className="block text-[14px] font-bold">{label}</span>
                <span className="block text-[12px] leading-snug mt-1"
                  style={{ color: 'var(--text-secondary)' }}>{what}</span>
                <span className="block text-[12px] font-semibold mt-2"
                  style={{ color: 'var(--series-cost)' }}>Open &rarr;</span>
              </button>
            ))}
          </div>
        </div>
      </section>

      <div className="mx-auto max-w-6xl px-5 py-12">
        <Note>
          The staff reductions in room one are the FY27 cycle, which is what this model
          records. If there were cuts in earlier years they are not here, and a multi-year
          count would be the most persuasive figure on this page.
        </Note>
      </div>
    </div>
  )
}
