import { usd, usdShort } from '../model/engine'
import {
  DEFAULT_SCENARIO, LEVY_CAP, SHARE, nextYear, overrideForYears, run,
} from '../model/rates'
import { YearLedger } from '../components/TheRaise'
import { OverrideTreadmill, OverrideSizing } from '../components/LevelVsSlope'
import { Section, Note } from '../components/primitives'

const pct = (x: number, d = 1) => `${(x * 100).toFixed(d)}%`
const N = nextYear()
/** The size the rest of the site uses, so the pages agree. */
const OVERRIDE = 1_250_000

/** Overrides, given a page of their own.
 *
 *  It is the first thing raised at every meeting and the least well understood thing in
 *  the whole budget, and the misunderstandings are specific rather than general: that an
 *  override is a one-off payment rather than a permanent lift to the levy limit; that a
 *  townwide question and a school question are the same ask; that closing next year's gap
 *  closes the problem. Each of those is answered by a table rather than an argument.
 *
 *  Deliberately not an argument against overrides. Two of the findings here cut the other
 *  way — a school-only question is worth nearly twice a townwide one per dollar of tax,
 *  and a large enough override genuinely does cover years rather than a year. What the
 *  page will not do is let "an override fixes it" stand without saying for how long. */
export function Override({ onJump }: {
  onJump: (tab: 'curve' | 'money' | 'answers' | 'adjust') => void
}) {
  const townwide = OVERRIDE / SHARE
  const five = overrideForYears(5)
  const withOne = run(10, { ...DEFAULT_SCENARIO, overrideLevy: OVERRIDE })
  const lasts = withOne.findIndex(y => y.gap > 0)

  return (
    <div>
      <div className="mx-auto max-w-6xl px-5 pt-12 pb-2">
        <p className="text-xs font-semibold uppercase tracking-widest mb-3"
          style={{ color: 'var(--text-muted)' }}>The revenue answer</p>
        <h1 className="text-3xl sm:text-4xl font-bold tracking-tight leading-[1.1] max-w-3xl">
          Overrides
        </h1>
        <p className="mt-4 text-[15px] leading-relaxed max-w-2xl"
          style={{ color: 'var(--text-secondary)' }}>
          The first thing raised at every meeting, and the thing most often described
          wrongly. An override is not a one-off payment: it raises the town&rsquo;s levy
          limit <strong style={{ color: 'var(--text-primary)' }}>permanently</strong>, and
          the higher limit then grows {pct(LEVY_CAP)} a year like the rest of it. So the
          real questions are how big, for how long, and written for whom &mdash; and all
          three have arithmetic answers.
        </p>
        <Note>
          Nothing here argues for or against one. Two of the findings below make overrides
          look considerably better than they are usually described, and one makes them look
          worse.
        </Note>
      </div>

      <Section id="shape" eyebrow="Three things about the instrument"
        title="What an override actually is"
        lede={<>Before any number, the mechanics &mdash; because most of the disagreement
          in town is about these rather than about the money.</>}>
        <div className="grid gap-3 lg:grid-cols-3 items-start">
          <Card title="It is permanent, and it compounds"
            body={<>Not a cheque for one year. The levy limit rises by the amount voted and
              stays risen, then grows {pct(LEVY_CAP)} a year like the rest of the limit. A{' '}
              {usdShort(OVERRIDE)} override is worth {usd(OVERRIDE * (1 + LEVY_CAP) ** 5)}{' '}
              in its sixth year without anybody voting again.</>} />
          <Card title="A school question is worth nearly twice a townwide one"
            tone="good"
            body={<>An override may be written for a single department. A school-only
              question sends the schools every dollar. A general one covering all
              departments sends them about {(SHARE * 100).toFixed(0)}&cent; of each, so it
              has to be {usdShort(townwide)} to do the work of a {usdShort(OVERRIDE)}{' '}
              school question &mdash; and costs the average homeowner nearly twice as much.
              The ask Lunenburg put up and lost was the townwide kind.</>} />
          <Card title="It raises a ceiling, not a bill"
            body={<>An override lifts the limit; it does not oblige the town to collect to
              it. In a year the schools need less than it raises, the town can levy under
              the limit &mdash; Lunenburg has left as much as $53,706 unlevied &mdash; or
              appropriate the difference elsewhere.</>} />
        </div>
      </Section>

      <Section id="one" eyebrow="What one override does"
        title={`One ${usdShort(OVERRIDE)} override, followed to the end`}
        lede={<>The clearest way to see it is the ordinary projection with one thing added:
          a school-only override of {usd(OVERRIDE)} passed once, in FY{N.fy}, never voted
          on again, carried forward at {pct(LEVY_CAP)}. The revenue column is built up so
          the addition is visible &mdash; what the town could give without an override,
          plus the override, equals what the schools actually have.</>}>
        <YearLedger overrideLevy={OVERRIDE}
          title={`The projection, with a ${usdShort(OVERRIDE)} override passed in FY${N.fy}`}
          intro={<>Identical arithmetic to the year-by-year table on the rate page, with
            the override added and carried forward. Watch the total, and then watch the
            last column.</>}
          footer={({ grew }) => (
            <>
              <p>
                <strong>{lasts} years funded, then it fails</strong> &mdash; and the reason
                is in the last column. The override adds {usd(OVERRIDE * LEVY_CAP)} of
                growth in its second year, because {pct(LEVY_CAP)} of {usdShort(OVERRIDE)}{' '}
                is {usd(OVERRIDE * LEVY_CAP)}. The gap grows{' '}
                {usd(grew[1] + OVERRIDE * LEVY_CAP)} that same year. The override covers
                about{' '}
                {Math.round((OVERRIDE * LEVY_CAP / (grew[1] + OVERRIDE * LEVY_CAP)) * 100)}%
                of the annual growth, so the other{' '}
                {100 - Math.round((OVERRIDE * LEVY_CAP / (grew[1] + OVERRIDE * LEVY_CAP)) * 100)}%
                accumulates until it swallows the override whole.
              </p>
              <p className="mt-2">
                This is also why an override is sized against the{' '}
                <strong>running total</strong> rather than against the annual growth. It
                replaces a revenue line that never rose, so it has to cover everything
                missing from that line in the year you care about, not just that
                year&rsquo;s increment. The increment is the right measure only for the
                other strategy, below: a new override every year, each topping up the ones
                already passed.
              </p>
            </>
          )} />
      </Section>

      <Section id="treadmill" eyebrow="Why an override is not one vote"
        title="The ballot question you would have to pass every year"
        lede={<>An override is heard as a single ask. It lifts the levy base once, and that
          base then grows {pct(LEVY_CAP)} while costs grow {pct(0.0493, 2)} &mdash; so
          holding services level asks for a fresh one every spring. Each of these is the
          new money needed on top of the overrides already passed and still
          growing.</>}>
        <OverrideTreadmill />
        <Note>
          This is not an argument against an override. It is an argument against expecting
          one to be the last one. An override closes a level; it does not change a rate,
          which is why the row below it is nearly as large.
        </Note>
      </Section>

      <Section id="sizing" eyebrow="The other way to do it"
        title="Or one vote, sized to last"
        lede={<>The fair counterpoint to the treadmill. Because an override compounds, a
          large enough one really does cover years rather than a year. This is what each
          length costs, and the price of each extra year is the thing to
          notice.</>}>
        <OverrideSizing />
        <Note>
          {usdShort(five.levy)} buys five years at ${five.onAverageHome} a year on the
          average home. Whether that is worth it is a judgment about what five years of
          stability is for &mdash; time to bend a cost curve, or time before the same
          conversation happens again.
        </Note>
      </Section>

      <Section id="after" eyebrow="What it does not do"
        title="An override buys time, not a solution"
        lede={<>Everything on this page is about the level: how much money, for how long.
          None of it touches the reason the level keeps moving.</>}>
        <div className="grid gap-3 lg:grid-cols-2 items-start">
          <Card title="The two rates never cross"
            body={<>An override compounds at {pct(LEVY_CAP)}. What the schools buy compounds
              at nearly 5%. No override of any size holds for ever, because those two lines
              do not meet &mdash; buying a decade costs{' '}
              {usd(overrideForYears(10).onAverageHome)} a year on the average home and
              FY{38} arrives anyway.</>}
            link="See the rate problem" onClick={() => onJump('curve')} />
          <Card title="What the time would be for"
            body={<>Which is the case for one rather than against it. Five years of
              stability is five years in which a health insurance contract could be
              renegotiated and a teachers&rsquo; agreement settled at a different number
              &mdash; the two lines that are 82% of the budget. An override that buys time
              nobody uses buys nothing.</>}
            link="See what each option costs" onClick={() => onJump('money')} />
        </div>
      </Section>
    </div>
  )
}

function Card({ title, body, tone, link, onClick }: {
  title: string; body: React.ReactNode; tone?: 'good'; link?: string; onClick?: () => void
}) {
  return (
    <div className="card p-5">
      <h3 className="text-[15px] font-bold mb-2"
        style={{ color: tone === 'good' ? 'var(--status-good)' : undefined }}>{title}</h3>
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
