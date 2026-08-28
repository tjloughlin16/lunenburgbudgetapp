import { usd, usdShort, COST_GROWTH_BLENDED } from '../model/engine'
import {
  ALREADY_CUT, ALREADY_SAID, LEVEL_SERVICE,
} from '../model/walk'
import {
  BASELINE_REVENUE_GROWTH, LEVY_CAP, RATE_LINES, DEFAULT_SCENARIO, STATE_AID,
  nextYear, overrideForYears, longRunTarget, salaryRateToBalance, workforceShrink,
  DEFAULT_RATES, ch70OnlyGrowth, aidGrowthToSustain, SHARE, PACKAGES,
  overrideOnAverageHome,
} from '../model/rates'
import { ADMIN, DEVELOPMENT } from '../model/answers'
import { MODEL } from '../model/engine'
import { CitationList } from '../components/Citations'
import { Room, Say, Plate, SectionLink, AlreadyCut, OneTimeAnswers,
         WhatIsADevelopment } from '../components/walk'
import { TheRaise } from '../components/TheRaise'
import { RateBoard } from '../components/RateBoard'
import { OverrideSizing, OverrideTreadmill, OverrideExplorer } from '../components/LevelVsSlope'
import { PriceList } from '../components/PriceList'
import { Note } from '../components/primitives'
import { Upshot } from '../components/Upshot'

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
    | 'deeper' | 'solved') => void
}) {
  /** The cheapest ballot question on the packages page, which is the one figure from it
   *  worth carrying into the room — an override an order of magnitude below the one the
   *  town has already refused is the fact that makes somebody click through. */
  const CHEAPEST = PACKAGES
    .filter(p => (p.firstYears.overrideTownwide ?? 0) > 1000)
    .reduce((a, b) => ((a.firstYears.overrideTownwide ?? 0)
      <= (b.firstYears.overrideTownwide ?? 0) ? a : b))
  const cuts = ALREADY_CUT
  const ranked = RATE_LINES.slice().sort((a, b) => b.swing - a.swing)
  const salaryAt4 = salaryRateToBalance({ ...DEFAULT_RATES, health: 0.04 }, T)
  const shrink = workforceShrink(Math.max(salaryRateToBalance(DEFAULT_RATES, T), 0), 0.04)
  const aidRate = aidGrowthToSustain(DEFAULT_SCENARIO)!
  // Derived, not typed. Both of these moved when special education got its own escalator
  // and neither noticed, which is rule 2 in CLAUDE.md and the reason it is written down.
  const ch70Rate = ch70OnlyGrowth(aidRate)
  const ch70Year1 = STATE_AID.chapter70 * ch70Rate
  const ch70TenYear = Array.from({ length: 10 }, (_, i) =>
    STATE_AID.chapter70 * ((1 + ch70Rate) ** (i + 1) - 1)).reduce((a, b) => a + b, 0)
  const five = overrideForYears(5)
  const two = overrideForYears(2)

  return (
    <div>
      {/* The conclusions come before the working.
        *
        * This page used to open by announcing that it was eleven steps long and then
        * being eleven steps long, which is the shape of a proof rather than of an
        * argument. Readers told us so: there is a lot of it, and the point arrives last.
        * The material is not the problem — it is the reason any of this is checkable —
        * so nothing has been cut. What has changed is the order: four claims and two
        * pictures first, and the rooms below relabeled as what they always were. */}
      <div className="mx-auto max-w-6xl px-5 pt-14 pb-10">
        <p className="text-xs font-semibold uppercase tracking-widest mb-3"
          style={{ color: 'var(--text-muted)' }}>Start here</p>
        {/* Named, because this page gets shared as a link with no context around it.
          *
          * "The school budget" is whichever one the reader is already angry about, and a
          * headline that could be any town's is the wrong first sentence for an argument
          * that only holds for this one. The brand color is the same one the wordmark
          * uses, so the town's name reads as the town's name and not as a link. */}
        <h1 className="text-3xl sm:text-5xl font-bold tracking-tight leading-[1.05] max-w-3xl">
          Why <span style={{ color: 'var(--brand)' }}>Lunenburg&rsquo;s</span> school
          budget keeps doing this
        </h1>
        <p className="mt-5 text-[16px] leading-relaxed max-w-2xl"
          style={{ color: 'var(--text-secondary)' }}>
          <strong style={{ color: 'var(--text-primary)' }}>This is a projection of a year
          nobody has argued about yet.</strong> FY{N.fy} has not been decided, presented or
          debated. What follows is what the district&rsquo;s own published growth rates
          produce when you run them forward &mdash; which is the point of doing it now
          rather than in January.
        </p>
        <Note>
          Figures for FY27 and earlier are from the town&rsquo;s published budget and tax
          records. FY{N.fy} onward are this model&rsquo;s arithmetic, shown in full at every
          step so you can disagree with it precisely. Nothing here is rounded to flatter an
          argument.
        </Note>
      </div>

      <Upshot onJump={onJump} />

      {/* The summary's primary button lands here rather than on room one, so the reader
          arrives at the handover — "now the same thing slowly" — instead of dropping into
          the middle of an argument that has just been summarized at them. */}
      <div id="the-working" className="scroll-mt-12 mx-auto max-w-6xl px-5 pt-12 pb-8">
        <p className="text-xs font-semibold uppercase tracking-widest mb-3"
          style={{ color: 'var(--text-muted)' }}>The working &middot; eleven steps</p>
        <h2 className="text-2xl sm:text-4xl font-bold tracking-tight leading-[1.1] max-w-3xl">
          Now the same thing slowly, with every number shown
        </h2>
        <p className="mt-4 text-[16px] leading-relaxed max-w-2xl"
          style={{ color: 'var(--text-secondary)' }}>
          Eleven steps, in order, assuming you know nothing about the budget. Each one
          answers a single question, corrects one thing people believe, and hands you one
          sentence. You can stop after any of them and the thing you took away will still
          be true.
        </p>
      </div>

      {/* ------------------------------------------------ 01 */}
      <Room n={1} slug="where-the-town-is" tag="Where the town actually is"
        title="What has already happened, and what has not been said yet"
        leave={<>The town has already given real things up, and the next round has not
          started. This is what the arithmetic says is coming before anybody announces
          it.</>}>
        <Say>
          Two things have happened, and they are matters of record. Two override questions
          went to the ballot and both were defeated. And the FY{N.fy - 1} budget the town
          is running on right now cut <strong>{cuts.fte} positions</strong> and{' '}
          {usd(cuts.cost)}.
        </Say>
        <Say>
          <strong>Nothing about FY{N.fy} has been decided or announced.</strong>{' '}
          No committee has published a figure and no meeting has argued about one. The{' '}
          {usd(LEVEL_SERVICE.gap)} below is not a number somebody handed the town &mdash;
          it is what this projection produces by running the district&rsquo;s own published
          growth rates forward one year, and the next ten rooms are the working.
        </Say>
        <Say>
          Which is the reason to read it now rather than in January. Everything in the
          record column already happened. Everything in the projection column is still a
          choice.
        </Say>
        <Plate label="On the record — this already happened" figures={[
          { v: `${cuts.fte} FTE`, k: 'positions cut from the budget now in force', cite: 'cuts', tone: 'critical' },
          { v: '0 of 2', k: 'override questions passed', cite: 'override' },
          { v: `$${ALREADY_SAID.overrides[0].cost} · $${ALREADY_SAID.overrides[1].cost}`,
            k: 'what each would have added to the average tax bill', cite: 'override' },
        ]} />
        <Plate label="Projected — nobody has announced this" figures={[
          { v: usdShort(LEVEL_SERVICE.gap), k: 'what FY28 is short, on this model’s arithmetic', cite: 'gap',
            tone: 'critical' },
        ]} />
        <AlreadyCut />
        <Say>
          That list matters before anything else does. The rest of this explains why a hole
          opens again anyway &mdash; which is a different question from whether anybody
          tried.
        </Say>
      </Room>

      {/* ------------------------------------------------ 02 */}
      <Room n={2} slug="the-ask" tag="What the ask is"
        title="&ldquo;More money&rdquo; means the same schools, one year older"
        corrects={<>&ldquo;The schools keep asking for more.&rdquo;</>}
        leave={<>The ask is not for more schooling. It is for the same schooling at next
          year&rsquo;s prices.</>}>
        <Say>
          Everything here turns on one phrase that budget documents use and nobody
          explains. <strong>Level service</strong> means the same staff, the same buses,
          the same buildings, the same {LEVEL_SERVICE.enrollment.toLocaleString()} children.
          Nobody is hired. Nothing is added. No program comes back.
        </Say>
        <Plate label="What standing still costs" figures={[
          { v: usdShort(LEVEL_SERVICE.fy27), k: 'the town gave the schools this year', cite: 'fy27-approp' },
          { v: `+${usd(LEVEL_SERVICE.increase)}`, k: 'what the identical thing costs next year', cite: 'gap',
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
      <Room n={3} slug="what-the-town-can-give" tag="What the town can give"
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
      <Room n={4} slug="the-subtraction" tag="The subtraction"
        title={<>Costs want {usd(N.costTotal)}. Revenue offers {usd(N.allowed)}.</>}
        corrects={<>&ldquo;There must be waste in there somewhere.&rdquo;</>}
        leave={<>The deficit is a subtraction, and you have now watched it being done.</>}>
        <Say>
          Now the projected figure from room one stops being asserted and starts being
          derived. Put the increase on the table as a fixed quantity, and let each cost line
          take its bite in the order it takes it.
        </Say>
        <TheRaise />
      </Room>

      {/* ------------------------------------------------ 05 */}
      <Room n={5} slug="whose-fault-it-is" tag="Whose fault it is"
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
          deeply, including {cuts.fte} positions in the budget it is running on now, and
          the line it fully controls
          is the one already living within its means.
        </Say>
      </Room>

      {/* ------------------------------------------------ 06 */}
      <Room n={6} slug="two-rates" tag="The centerpiece" handsOn
        title="Two rates, and they were never going to meet"
        corrects={<>&ldquo;We just cut. Why is there a hole again?&rdquo;</>}
        leave={<>Cuts change the amount. Only rates change the direction. This year&rsquo;s
          cut was never going to stop next year&rsquo;s hole.</>}>
        <div className="card p-5 sm:p-6" style={{ borderColor: 'var(--status-critical)',
                                                  borderWidth: 2 }}>
          <p className="text-[17px] sm:text-xl leading-snug font-medium">
            The budget Lunenburg is running on right now cut{' '}
            <strong>{cuts.fte} positions</strong> and <strong>{usd(cuts.cost)}</strong>{' '}
            &mdash; four classroom teachers, an interventionist and a half, an assistant
            principal, a custodian, half the athletic trainer. Next year the schools are
            projected short{' '}
            <strong style={{ color: 'var(--status-critical)' }}>
              {usd(LEVEL_SERVICE.gap)}</strong>.
          </p>
        </div>
        <Say>
          The town is living inside this experiment right now. The painful thing has been
          done, and a bigger hole opens the year after it. What follows is why.
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
        {/* 48px of site header plus the ~38px identity strip above. It was 136 when the
            strip carried a two-line title as well. */}
        <RateBoard stickyTop="top-[86px]" />
      </Room>

      {/* ------------------------------------------------ 07 */}
      <Room n={7} slug="the-cuts" tag="The cuts you feel" handsOn
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
      <Room n={8} slug="the-override" tag="The revenue answer" handsOn
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
      <Room n={9} slug="commercial-development" tag="The growth answer"
        title="What commercial development would have to look like"
        corrects={<>&ldquo;Commercial development will grow us out of this.&rdquo;</>}
        leave={<>Commercial development is real money and the wrong order of magnitude
          &mdash; and it has to accelerate, not merely continue.</>}>
        <Say>
          The right instinct, priced honestly. Two facts do all the work here, and neither
          is in general circulation.
        </Say>
        <Plate label="On the wall" figures={[
          { v: `${(SHARE * 100).toFixed(0)}¢`, k: 'of each new-growth dollar reaches the schools — the rest is the town’s', cite: 'levy' },
          { v: usdShort(DEVELOPMENT.fiveYear.value),
            k: 'of new commercial value a year to hold the gap for five years', cite: 'taxbase' },
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
      <Room n={10} slug="the-state-house" tag="The advocacy answer"
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
          { v: pct(STATE_AID.shareOfTownRevenue, 0), k: 'of town revenue is state aid — which is why the rate has to be so high', cite: 'levy' },
          { v: pct(ch70Rate), k: 'annual growth Chapter 70 alone would need, for ever', cite: 'ch70', tone: 'critical' },
          { v: `+${usd(Math.round(ch70Year1))}`, k: 'extra in the first year', cite: 'ch70' },
          { v: usdShort(ch70TenYear), k: 'extra over ten years', cite: 'ch70' },
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
      <Room n={11} slug="what-it-takes" tag="What it would take" handsOn
        title="What &ldquo;solved&rdquo; would actually require"
        corrects={<>&ldquo;There must be a version of this where nobody gets hurt.&rdquo;</>}
        leave={<>There is no painless version, and there are several that work. Five
          quiet years is a smaller ask than thirty; every one of them moves both
          salaries and insurance; and the packages that share the change cost a
          fraction of the ones that spare either side.</>}>
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
        <Say>
          Start with the version of that nobody has to agree to, because it is the one
          already happening. Leave insurance where it is, leave the bargained increase
          where it is, and hold the salary line down by employing fewer people:
        </Say>
        <Plate label="The default — what happens if nobody decides anything" figures={[
          { v: pct(Math.max(salaryRateToBalance(DEFAULT_RATES, T), 0)), k: 'all the salary line can grow, while insurance rises 9% a year', cite: 'salaries', tone: 'critical' },
          { v: `${shrink.positionsPerYear.toFixed(1)}`, k: 'positions gone in the first year, and more every year after' },
          { v: `−${pct(shrink.after20, 0)}`, k: 'of the workforce after twenty years', tone: 'critical' },
          { v: pct(salaryAt4), k: 'what the salary line could grow at instead, if insurance came to 4%', cite: 'health', tone: 'good' },
        ]} />
        <Say>
          <strong>That is not a recommendation.</strong> It is what the arithmetic does on
          its own when nobody chooses: every position left unfilled is an instalment on it,
          and the town has been paying them for years without ever voting for the total.
          It appears below as <strong>option five of seven</strong>, priced beside the
          rest rather than standing on its own &mdash; and the last figure above is the
          reason it is not the only option. What insurance does decides what is left for
          salaries.
        </Say>
        <Say>
          So the one condition sounds like a single locked door, and it is not. There are
          {' '}{PACKAGES.length} combinations that actually keep the gap shut &mdash; for
          five years, for ten, for a generation, and {PACKAGES.filter(p => p.forEver).length}{' '}
          that never reopen at all &mdash; and none of them pulls a single lever. The
          cheapest of them costs an override of about{' '}
          {usd(overrideOnAverageHome(CHEAPEST.firstYears.overrideTownwide ?? 0))} a year on
          the average home, against the {usd(Math.round(MODEL.facts.tier1TaxIncrease))} one
          the town turned down.
        </Say>
        <Say>
          Each one names the rates it needs, the four interchangeable ways to cover the
          first years &mdash; build, one override, user fees, or one permanent cut &mdash;
          and who has to say yes. That is more arithmetic than a room can hold, so it has a
          page of its own.
        </Say>
        <div className="card p-4 sm:p-5">
          <p className="text-[15px] font-bold mb-1">
            What &ldquo;solved&rdquo; would actually require
          </p>
          <p className="text-[13px] leading-relaxed mb-3" style={{ color: 'var(--text-secondary)' }}>
            {PACKAGES.length} priced combinations, why every one of them moves at least two
            lines, what a moderate result at the State House is worth to each, and the
            table they were all drawn from. Any of them can be loaded straight into the
            curve or the budget builder.
          </p>
          <button onClick={() => onJump('solved')} className="text-[13px] font-semibold"
            style={{ color: 'var(--series-cost)' }}>
            See what actually holds, and for how long &rarr;
          </button>
        </div>
      </Room>

      {/* The exit, which is not a room.
       *
       * It was inside room 11, which made that room both an exploration and a conclusion
       * and put a "hands on" badge over a heading whose tag read "the exit". A room that
       * ends the walkthrough should not also open a new question. */}
      <section id="exit" className="scroll-mt-12 border-t py-14"
        style={{ borderColor: 'var(--grid)', background: 'var(--surface-1)' }}>
        <div className="mx-auto max-w-6xl px-5">
          <div className="flex items-center gap-2.5 mb-3">
            <p className="text-xs font-semibold uppercase tracking-widest"
              style={{ color: 'var(--text-muted)' }}>The way out</p>
            <SectionLink id="exit" what="the way out" />
          </div>
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
              ['solved', 'What solved requires', `${PACKAGES.length} combinations that keep the gap shut, priced and filed by how long they hold`],
              ['adjust', 'Build your own budget', 'Every dial that moves the gap, on one page'],
              ['curve', 'Bend the curve', 'Cut things, then change a rate, and watch which one works'],
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

      {/* Last thing on the page on purpose. A reader who has followed the argument this
          far has earned the right to check it, and should not have to go looking. */}
      <CitationList />
    </div>
  )
}
