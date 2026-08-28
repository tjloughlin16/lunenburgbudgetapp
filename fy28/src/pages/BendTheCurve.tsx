import { usd, usdShort, COST_GROWTH_BLENDED } from '../model/engine'
import {
  BASELINE_REVENUE_GROWTH, LEVY_CAP, RATE_LINES, DEFAULT_SCENARIO, run, STATE_AID,
  nextYear, HEADCOUNT, PACKAGES,
} from '../model/rates'
import { ALREADY_CUT } from '../model/walk'
import { RateBoard } from '../components/RateBoard'
import { type Package } from '../model/rates'
import { LevelVsSlope } from '../components/LevelVsSlope'
import { StateAid } from '../components/Forever'
import { TheRaise, YearLedger } from '../components/TheRaise'
import { Section, Note } from '../components/primitives'

const pct = (x: number, d = 2) => `${(x * 100).toFixed(d)}%`

/** The rate problem, made adjustable — the answer to "why doesn't this year's cut fix it".
 *
 *  "Why it repeats" already proves that the gap comes back, and proves it well. What it
 *  cannot do, because it is a static page, is let somebody discover the mechanism with
 *  their hands: tick every painful cut on the list, watch the growth rate underneath
 *  refuse to move, then drag one rate and watch the curve bend. That gap between knowing
 *  a fact and having done it is the whole reason this tab exists.
 *
 *  The distinction it is built to teach, in one line: a cut changes how much is spent, a
 *  rate changes how fast that grows, and only the second one can end a problem that is
 *  itself a rate. */
const RAISE = nextYear()

export function BendTheCurve({ onJump, option = null }: {
  onJump: (tab: 'why' | 'money' | 'answers' | 'adjust' | 'override' | 'solved') => void
  /** An option loaded into this page's own board, from here or from the walkthrough. */
  option?: { route: Package; nonce: number } | null
}) {
  const base = run(12, DEFAULT_SCENARIO)
  const spread = COST_GROWTH_BLENDED - BASELINE_REVENUE_GROWTH
  const ranked = RATE_LINES.slice().sort((a, b) => b.swing - a.swing)
  const top2 = ranked.slice(0, 2)
  const rest = ranked.slice(2)
  const topSwing = top2.reduce((s, l) => s + l.swing, 0)
  const restSwing = rest.reduce((s, l) => s + l.swing, 0)
  // Against the spread that actually has to be closed, not against each other — the
  // headline claim here was once "98% of the problem", which was the two lines' share of
  // the total swing available and answered a question nobody asked.
  const topVsSpread = topSwing / spread
  const restVsSpread = restSwing / spread

  return (
    <div>
      <div className="mx-auto max-w-6xl px-5 pt-12 pb-2">
        <p className="text-xs font-semibold uppercase tracking-widest mb-3"
          style={{ color: 'var(--text-muted)' }}>The rate problem</p>
        <h1 className="text-3xl sm:text-4xl font-bold tracking-tight leading-[1.1] max-w-3xl">
          Bend the curve
        </h1>
        <p className="mt-4 text-[15px] leading-relaxed max-w-2xl"
          style={{ color: 'var(--text-secondary)' }}>
          The budget Lunenburg is running on right now cut{' '}
          {usdShort(ALREADY_CUT.cost)} and {ALREADY_CUT.fte} positions, and next year the
          hole is bigger than the one that bought. That sounds like somebody failed. It is
          not &mdash;{' '}
          <strong style={{ color: 'var(--text-primary)' }}>it is what happens when you
          answer a rate problem with an amount</strong>. This page lets you do both and
          watch the difference.
        </p>
        <Note>
          Same projection as the rest of the site, opened up at the growth rates. At the
          default settings it reproduces the main model to the dollar.
        </Note>
      </div>

      <Section id="raise" eyebrow="Start here"
        title={`Next year the schools get ${usdShort(RAISE.allowed)} more. Here is who spends it.`}
        lede={<>Nobody at a meeting argues about the size of the school budget. They argue
          about whether a {pct(LEVY_CAP, 1)} raise ought to be enough. So put the raise on
          the table as one fixed number of dollars, and let each cost line take its bite in
          the order it takes it.
          <br /><br />
          <strong>Health insurance alone wants {pct(RAISE.costs[1].shareOfAllowed)} of
          it.</strong> By the third line there is nothing left, and there are three more
          lines. None of this is new spending &mdash; it is the same staff, the same buses
          and the same buildings, one year older. That is what &ldquo;the rate problem&rdquo;
          means before any of the arithmetic below.</>}>
        <TheRaise />
      </Section>

      <Section id="two" eyebrow="The whole thing in two numbers"
        title={`Costs grow ${pct(COST_GROWTH_BLENDED)}. Revenue grows ${pct(BASELINE_REVENUE_GROWTH)}.`}
        lede={<>That is the entire problem, and everything else on this site is downstream
          of it. Two things compounding at different speeds pull apart forever, and the
          distance between them grows on its own whether or not anybody does anything
          wrong. Those {(spread * 100).toFixed(2)} points are why the hole is{' '}
          <strong>{usd(base[1].gap - base[0].gap)} bigger in FY{base[1].fy} than in
          FY{base[0].fy}</strong> — and bigger again every year after, because it is a
          percentage of a number that keeps getting bigger.</>}>
        <div className="grid gap-3 sm:grid-cols-3">
          <Fact label="Costs grow at" value={pct(COST_GROWTH_BLENDED)}
            sub="Weighted across salaries, insurance, transport, special education, utilities and supplies"
            tone="critical" />
          <Fact label="Revenue grows at" value={pct(BASELINE_REVENUE_GROWTH)}
            sub={`Proposition 2½ caps the levy at ${pct(LEVY_CAP, 1)}; new growth adds the rest`} />
          <Fact label="The gap by FY33" value={usdShort(base[5].gap)}
            sub={`Starting from ${usdShort(base[0].gap)} next year, with nothing going wrong`}
            tone="critical" />
        </div>
        <div className="mt-4">
          <YearLedger
            title="Every year, with the increase already taken off"
            intro={<>Revenue does rise every year, and it rises here &mdash; third column.
              The gap is what is left <em>after</em> it. The last column is the difference
              between the row above and the row below, so it can be checked by
              subtraction.</>}
            footer={({ years, grew, avg }) => (
              <p>
                <strong>Read the last column.</strong> The running total looks explosive
                because it is cumulative &mdash; FY{years[1].fy}&rsquo;s{' '}
                {usdShort(years[1].gap)} <em>includes</em> FY{years[0].fy}&rsquo;s{' '}
                {usdShort(years[0].gap)} rather than sitting on top of it. What is actually
                happening is steadier and worse: the hole gets{' '}
                <strong>{usd(grew[0])} bigger next year and more every year after</strong>{' '}
                &mdash; {usd(avg)} a year on average across the decade, and never once
                smaller.
              </p>
            )} />
        </div>
      </Section>

      <Section id="board" eyebrow="The experiment"
        title="Cut things. Then change a rate. Watch which one works."
        lede={<>Two columns. The left one changes <strong>amounts</strong> &mdash; it cuts
          real, named things and passes an override. The right one changes{' '}
          <strong>rates</strong>. Both print the blended cost growth underneath.
          <br /><br />
          Start by ticking every box on the left. All of it &mdash; every sport, the band,
          the clubs, most of technology, every administrator the law allows you to lose.
          The chart drops. Now look at the growth rate under that column:{' '}
          <strong>it has not moved</strong>, and the curve you just lowered is climbing at
          exactly the angle it was before. That is why this year&rsquo;s cut does not stop
          next year&rsquo;s hole, and it is the thing that is almost impossible to say in
          words.
          <br /><br />
          Then drag one rate on the right and watch the line change angle instead.</>}>
        <RateBoard seed={option} />
      </Section>

      <Section id="leverage" eyebrow="Where the leverage actually is"
        title="Two lines can close it. The other four cannot."
        lede={<>Size and growth rate both matter, and neither one alone tells you
          anything &mdash; a huge line growing at the cap is harmless, and a small line
          growing at 9% is not. What matters is the product, and the product is brutally
          concentrated. The spread that has to be closed is{' '}
          {(spread * 100).toFixed(2)} points. Holding each line to the{' '}
          {pct(LEVY_CAP, 1)} levy cap moves the blended rate by:</>}>
        <div className="card p-4">
          {ranked.map(l => (
            <div key={l.key} className="py-2.5 border-b last:border-b-0"
              style={{ borderColor: 'var(--grid)' }}>
              <div className="flex items-baseline justify-between gap-3">
                <p className="text-[14px] font-semibold">{l.label}</p>
                <p className="text-[14px] font-bold tnum shrink-0">
                  {(l.swing * 100).toFixed(2)} pts
                </p>
              </div>
              <div className="h-1.5 rounded-full mt-1.5 mb-1.5"
                style={{ background: 'var(--surface-3)' }}>
                <div className="h-full rounded-full" style={{
                  width: `${(l.swing / ranked[0].swing) * 100}%`,
                  background: 'var(--series-cost)' }} />
              </div>
              <p className="text-[11px]" style={{ color: 'var(--text-muted)' }}>
                {pct(l.weight, 1)} of the budget, growing {pct(l.rate, 1)} · {l.controlledBy}
              </p>
            </div>
          ))}
        </div>
        <Note>
          {top2.map(l => l.label).join(' and ')} are{' '}
          {pct(top2.reduce((s2, l) => s2 + l.weight, 0), 0)} of the budget and worth{' '}
          {(topSwing * 100).toFixed(2)} points &mdash;{' '}
          <strong>{Math.round(topVsSpread * 100)}% of the spread, so those two alone are
          enough to end it</strong>. The other four lines together are worth{' '}
          {(restSwing * 100).toFixed(2)} points, or {Math.round(restVsSpread * 100)}% of it:
          hold transport, special education, utilities and supplies all at the cap, at
          once, forever, and you have closed under a quarter of the problem.
        </Note>
        <Note>
          Note which line the town has actually been cutting. &ldquo;Everything else&rdquo;
          is the only one the School Committee genuinely controls &mdash; and it is the
          smallest on the list, the slowest-growing, and worth{' '}
          {(rest[rest.length - 1].swing * 100).toFixed(2)} points. Athletics, clubs, art
          supplies and devices all live inside it.
        </Note>
      </Section>

      <Section id="proof" eyebrow="Level against slope"
        title="Six futures, priced the same way"
        lede={<>The same six things the board can do, fixed in place so the argument does
          not depend on finding the right slider. Read the last line of each card: whether
          the two rates have crossed is the only thing that decides if the fix is
          permanent.</>}>
        <LevelVsSlope />
        <Note>
          Notice what the last card does. Fixing the rates first leaves a residue &mdash;
          the gap stops growing but does not vanish, because FY28 already starts behind.
          A single cut then closes that residue and it <em>stays</em> closed. Done the
          other way round, the same cut buys twelve months. The order is the whole lesson:
          a one-time fix only works after the rate is fixed.
        </Note>
      </Section>

      <Section id="override" eyebrow="The revenue side"
        title="Overrides have a page of their own"
        lede={<>An override is the one answer here that takes nothing from a classroom, and
          the arithmetic of it &mdash; how big, for how long, and whether the question is
          written for the schools or for the whole town &mdash; needs more room than a
          section. The short version: it compounds at {pct(LEVY_CAP, 1)} while the gap
          compounds at {pct(COST_GROWTH_BLENDED)}, so a {usdShort(1_250_000)} school
          override funds two years, and no override of any size holds for ever.</>}>
        <button onClick={() => onJump('override')}
          className="text-[13px] font-semibold" style={{ color: 'var(--series-cost)' }}>
          See the override arithmetic &rarr;
        </button>
      </Section>

      <Section id="forever" eyebrow="The actual question"
        title="What stable looks like — not for a year, forever"
        lede={<>Everything above is about closing a gap. Never having one again is a
          different and much harder question, and it has exactly one condition: the
          weighted average of everything the district buys has to grow no faster than the
          town&rsquo;s revenue. That sounds like one locked door and it is not &mdash;
          there are {PACKAGES.length} combinations that keep the gap shut, filed by how
          long they hold for, each with the rates it needs and the four interchangeable
          ways to cover the first years. It outgrew this page and has one of its own.</>}>
        <div className="card p-4 sm:p-5">
          <p className="text-[15px] font-bold mb-1">What &ldquo;solved&rdquo; would actually require</p>
          <p className="text-[13px] leading-relaxed mb-3" style={{ color: 'var(--text-secondary)' }}>
            {PACKAGES.length} priced combinations &mdash; five years, ten, a generation, and{' '}
            {PACKAGES.filter(p => p.forEver).length} that never reopen &mdash; plus why
            every one of them moves at least two lines, what a moderate result at the State
            House is worth to each, and the trade table they were drawn from. Any of them
            loads straight back into the board above.
          </p>
          <button onClick={() => onJump('solved')} className="text-[13px] font-semibold"
            style={{ color: 'var(--series-cost)' }}>
            See what actually holds, and for how long &rarr;
          </button>
        </div>
      </Section>

      <Section id="state" eyebrow="The other way out"
        title="What the state would have to do"
        lede={<>Every route above takes it from somebody in Lunenburg. There is one that
          does not: Chapter 70 pays {pct(STATE_AID.shareOfSchoolBudget, 0)} of this school
          budget, and all state aid together is {usdShort(STATE_AID.total)} of what the
          town collects. If that grew faster than the things it buys, none of the rest of
          this page would be necessary. So it is worth a number rather than a wish.</>}>
        <StateAid />
      </Section>

      <Section id="honest" eyebrow="Being straight about it"
        title="What this page cannot tell you"
        lede={<>The controls make rates look like dials. They are not &mdash; every one of
          them is somebody&rsquo;s contract, somebody&rsquo;s insurance, or a state
          formula.</>}>
        <div className="grid gap-3 lg:grid-cols-3 items-start">
          <Caveat title="Rates are not set by sliders"
            body={<>Dragging salaries to {pct(LEVY_CAP, 1)} is a bargaining position, not a
              decision, and it is a real-terms pay cut for roughly {HEADCOUNT} people. Health
              insurance is bought by the Town, not the district. Out-of-district special
              education is set by state rates and by which children enroll.</>} />
          <Caveat title="The rates themselves are assumptions"
            body={<>9% health and 4% salaries are this model&rsquo;s projections, not
              measured futures. If insurance comes in at 5% much of this eases on its own
              — which is a reason to watch that number more closely than any cut list.</>} />
          <Caveat title="It says nothing about what should go"
            body={<>Every arithmetic here is indifferent to what a school is for. Which
              cuts are survivable, and which rate is fair to ask of the people who work
              there, are not questions a curve can answer.</>}
            link="See what each option costs" onClick={() => onJump('money')} />
        </div>
        <Note>
          If this tab makes its point, the rest of the site reads differently: the cut
          lists are not solutions, they are the price of not having fixed a rate.{' '}
          <button onClick={() => onJump('why')} className="font-semibold"
            style={{ color: 'var(--series-cost)' }}>
            The static version of this argument is on &ldquo;Why it repeats&rdquo; &rarr;
          </button>
        </Note>
      </Section>
    </div>
  )
}

function Fact({ label, value, sub, tone }: {
  label: string; value: string; sub: string; tone?: 'critical'
}) {
  return (
    <div className="card p-4">
      <p className="text-[11px] font-semibold uppercase tracking-widest mb-1.5"
        style={{ color: 'var(--text-muted)' }}>{label}</p>
      <p className="text-3xl font-bold tnum leading-none" style={{
        color: tone === 'critical' ? 'var(--status-critical)' : 'var(--text-primary)' }}>
        {value}
      </p>
      <p className="text-xs mt-2 leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
        {sub}
      </p>
    </div>
  )
}

function Caveat({ title, body, link, onClick }: {
  title: string; body: React.ReactNode; link?: string; onClick?: () => void
}) {
  return (
    <div className="card p-5">
      <h3 className="text-[15px] font-bold mb-2">{title}</h3>
      <p className="text-[13px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
        {body}
      </p>
      {link && (
        <button onClick={onClick} className="text-[12px] font-semibold mt-3"
          style={{ color: 'var(--series-cost)' }}>{link} &rarr;</button>
      )}
    </div>
  )
}
