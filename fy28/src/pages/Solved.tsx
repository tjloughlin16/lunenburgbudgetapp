import { usd, usdShort } from '../model/engine'
import {
  DEFAULT_SCENARIO, DEFAULT_RATES, LONG, PACKAGES, HEADCOUNT,
  longRunTarget, salaryRateToBalance, workforceShrink, FOREVER_BAR, TODAY_GAP,
} from '../model/rates'
import { Packages, type LoadPackage } from '../components/Packages'
import { WhyCombination } from '../components/WhyCombination'
import { HealthSalaryTrade } from '../components/Forever'
import { Section, Note } from '../components/primitives'

const pct = (x: number, d = 2) => `${(x * 100).toFixed(d)}%`
const TARGET = longRunTarget(DEFAULT_SCENARIO)
const salaryAt4 = salaryRateToBalance({ ...DEFAULT_RATES, health: 0.04 }, TARGET)
const shrink = workforceShrink(
  Math.max(salaryRateToBalance(DEFAULT_RATES, TARGET), 0), DEFAULT_RATES.salaries)

/** The page this material always wanted to be.
 *
 *  It grew up inside the walkthrough's eleventh room, where it did not belong: the
 *  walkthrough is a forty-minute argument that has to stay walkable on a phone, and by the
 *  end this section was twelve priced packages, a state-aid table, two necessity proofs
 *  and a trade table — more material than the ten rooms before it put together. A reader
 *  arriving at the front door does not need the whole answer; they need to know an answer
 *  exists and where it lives.
 *
 *  So the room keeps the condition and the shape of the answer, and everything that
 *  follows from it lives here, at its own address, where somebody can send a link to it. */
export function Solved({ onLoadPackage }: { onLoadPackage?: LoadPackage }) {
  const forEver = PACKAGES.filter(p => p.forEver).length

  return (
    <div>
      <div className="mx-auto max-w-6xl px-5 pt-12 pb-2">
        <p className="text-xs font-semibold uppercase tracking-widest mb-3"
          style={{ color: 'var(--text-muted)' }}>What it would take</p>
        <h1 className="text-3xl sm:text-4xl font-bold tracking-tight leading-[1.1] max-w-3xl">
          What &ldquo;solved&rdquo; would actually require
        </h1>
        <p className="mt-4 text-[15px] leading-relaxed max-w-2xl"
          style={{ color: 'var(--text-secondary)' }}>
          Every other page here is about closing a gap. This one is about not having one
          again &mdash; which is a different question with a single condition:{' '}
          <strong style={{ color: 'var(--text-primary)' }}>the weighted average of
          everything the district buys has to grow no faster than the town&rsquo;s
          revenue</strong>, {pct(TARGET)} over {LONG} years, or {pct(FOREVER_BAR, 1)} to
          never expire at all. That sounds like one locked door. There are{' '}
          {PACKAGES.length} ways through it, {forEver} of which never reopen, and this page
          prices all of them the same way.
        </p>
        <Note>
          Same projection as the rest of the site, opened up at the growth rates. Every
          package is solved rather than proposed: the figures are what the arithmetic
          requires, not what anybody has recommended.
        </Note>
      </div>

      <Section id="packages" eyebrow="The menu"
        title="Combinations that hold, and for how long"
        lede={<>Filed by how long they keep the gap shut rather than by how good they are,
          because five quiet years is a smaller ask than thirty and the town is entitled to
          know what the smaller ask costs. Within each band the packages differ in who is
          asked for what &mdash; which is the only part of this that is a decision rather
          than arithmetic.</>}>
        <Packages onLoad={onLoadPackage} />
      </Section>

      <Section id="why" eyebrow="The reason there is no single lever"
        title="Why every one of them moves at least two lines"
        lede={<>Not one package on the board above pulls one lever, and that is arithmetic
          rather than taste. Salaries and special education staffing are two thirds of the
          budget between them &mdash; but only one of those is bargained, and insurance is
          the highest-leverage line relative to its size. No one of them finishes the job,
          and the price of leaving either one out is on this page in the currency it is
          actually paid in.</>}>
        <WhyCombination />
      </Section>

      <Section id="trade" eyebrow="The table the packages were drawn from"
        title="What insurance does decides what is left for salaries"
        lede={<>Four of the six budget lines are fixed by contract, state law or the
          market, so salaries are the residual: whatever the other lines do, this is the
          line that has to absorb it. The honest question is not whether the town can hold
          salaries to any particular number, but what is left for them once insurance has
          taken its share &mdash; at every insurance rate worth asking the question at.</>}>
        <HealthSalaryTrade />
        <Note>
          The default, if nobody decides anything, is the last column read backwards:
          insurance stays where it is, the bargained increase stays where it is, and the
          salary line is held down by employing{' '}
          {shrink.positionsPerYear.toFixed(1)} fewer people a year &mdash;{' '}
          {pct(shrink.after20, 0)} of the workforce over twenty years. Getting insurance to
          4% lands the same arithmetic near {pct(salaryAt4)} instead: roughly flat pay,
          permanently, for about {HEADCOUNT} people and nobody losing a job. Any mix of the
          two works. What does not work is neither.
        </Note>
      </Section>

      <Section id="honest" eyebrow="Being straight about it"
        title="What this page cannot tell you"
        lede={<>Every package here is a point in a continuous trade-off, chosen because it
          is legible rather than because it is right.</>}>
        <div className="grid gap-3 lg:grid-cols-3 items-start">
          <Caveat title="These are twelve of infinitely many"
            body={<>Any mix of the same levers works if it gets the blended rate under the
              bar. The packages are curated so they can be compared, not because these
              particular numbers are the ones to adopt &mdash; the budget builder is where
              you make your own.</>} />
          <Caveat title="The rates are assumptions, not futures"
            body={<>9% health insurance and 4% salaries are this model&rsquo;s projections.
              If insurance comes in at 5% much of this eases on its own, which is a reason
              to watch that number more closely than any cut list. FY28 starting{' '}
              {usd(TODAY_GAP)} short is the one figure here that is already decided.</>} />
          <Caveat title="Nothing here says what should go"
            body={<>Whether a 3% settlement is fair, whether narrower networks are
              acceptable, whether the town wants {usdShort(1_000_000)} more of commercial
              development a year &mdash; none of those are questions a curve can answer,
              and this page does not pretend otherwise.</>} />
        </div>
      </Section>
    </div>
  )
}

function Caveat({ title, body }: { title: string; body: React.ReactNode }) {
  return (
    <div className="card p-5">
      <h3 className="text-[15px] font-bold mb-2">{title}</h3>
      <p className="text-[13px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
        {body}
      </p>
    </div>
  )
}
