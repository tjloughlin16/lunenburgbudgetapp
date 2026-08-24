import { usd, usdShort } from '../model/engine'
import { GAPS } from '../model/answers'
import { verdict, TARGETS } from '../model/price'
import { PriceList } from '../components/PriceList'
import { Section, Note } from '../components/primitives'

/** One number, priced on every lever at once.
 *
 *  The rest of this site is a projection: rates compounding out to FY33, which is the
 *  honest way to model a structural gap and the least checkable thing a resident can be
 *  handed. Whatever the arithmetic deserves, a six-year chain asks to be believed rather
 *  than followed, and that is a fair complaint about every conclusion drawn from it.
 *
 *  So this page gives the projection up deliberately. It fixes one flat target, prices it
 *  once per lever, and prints the division underneath each answer. Nothing here compounds
 *  and nothing here is a forecast. Accept a teacher's salary, the number of athletes and
 *  the tax rate, and every figure follows.
 *
 *  What it buys is not precision — the projection is more accurate. It is standing: an
 *  argument nobody has to take on trust, which is a different and sometimes more useful
 *  thing for a town to have. The closing section says plainly what was given up to get
 *  it, because a page that drops the time dimension has to admit that it did. */
export function FindTheMoney({ onJump }: {
  onJump: (tab: 'why' | 'answers' | 'adjust' | 'development') => void
}) {
  const v = verdict(TARGETS[0])
  const last = GAPS[GAPS.length - 1]

  return (
    <div>
      <div className="mx-auto max-w-6xl px-5 pt-12 pb-2">
        <p className="text-xs font-semibold uppercase tracking-widest mb-3"
          style={{ color: 'var(--text-muted)' }}>Plain arithmetic</p>
        <h1 className="text-3xl sm:text-4xl font-bold tracking-tight leading-[1.1] max-w-3xl">
          Find the money
        </h1>
        <p className="mt-4 text-[15px] leading-relaxed max-w-2xl"
          style={{ color: 'var(--text-secondary)' }}>
          {usd(GAPS[0].cumulative)} has to come from somewhere next year. Here is every
          place it could come from, what each one costs, and{' '}
          <strong style={{ color: 'var(--text-primary)' }}>how many of them cannot do it
          at all</strong>.
        </p>
        <p className="mt-3 text-[15px] leading-relaxed max-w-2xl"
          style={{ color: 'var(--text-secondary)' }}>
          Every other page here asks what happens over six years, which means trusting a
          projection. This one does not have a projection in it. One year, one division per
          answer, printed underneath so you can check it on the back of an envelope.
        </p>
        <Note>
          Figures come from the town&rsquo;s published FY27 budget and tax records. The
          only forecast on this page is the size of the hole itself &mdash; and you can
          ignore even that, and simply pick a number.
        </Note>
      </div>

      <Section id="price" eyebrow="The price list"
        title="Pick a number. See what it takes."
        lede={<>Each card answers the same question for one lever: to raise this much,
          next year, what would have to happen? The answer is stated the way somebody
          would say it out loud, then again in a unit you can picture, then as the
          arithmetic that produced it.
          <br /><br />
          The finding is not in any single card. It is <strong>how many of them say
          &ldquo;not possible&rdquo;</strong>. Most of the levers named at meetings have a
          hard ceiling well below the number &mdash; a fee cannot lawfully raise more than
          the program costs, and past a point a higher fee raises less rather than more.
          That ceiling is what the argument is usually missing. Step the target up and
          watch them go out one at a time.</>}>
        <PriceList />
        <Note>
          Each lever is priced on its own, as if it were the only thing being done. Several
          can be done at once and the ceilings add up &mdash; which is the point of the
          paragraph below. Every ceiling here is the same one used elsewhere on this site.
        </Note>

        {/* The one thing worth saying about the combined ceiling that the summary card
            does not already say: the year it stops being enough. It is a paragraph rather
            than a section because it is a single finding, and because comparing against
            FY30 is the only place this page leans on the projection it otherwise
            refuses. */}
        <div className="card p-4 sm:p-5 mt-4">
          <p className="text-[15px] leading-relaxed">
            <strong>That ceiling never moves.</strong> Administration, technology and all
            three fees at their limits come to {usd(v.overheadAndFees)} in{' '}
            <em>any</em> year &mdash; a fee cannot exceed what the program costs, and
            there are only so many office lines to cut. Next year&rsquo;s hole is{' '}
            {usdShort(GAPS[0].cumulative)}, so there is room. By FY{GAPS[2].fy} the hole is{' '}
            {usdShort(GAPS[2].cumulative)} and there is not &mdash;{' '}
            {usdShort(GAPS[2].cumulative - v.overheadAndFees)} past the ceiling before
            anyone has argued about which program to cut.
          </p>
          <p className="text-[12px] leading-relaxed mt-2" style={{ color: 'var(--text-muted)' }}>
            That last comparison is the one place this page uses the projection. Everything
            else on it is arithmetic on today&rsquo;s figures.
          </p>
        </div>
      </Section>

      <Section id="caveat" eyebrow="Being straight about it"
        title="What this page gives up"
        lede={<>Dropping the time dimension is what makes everything above checkable, and
          it costs something real. Three things this page cannot tell you, and where they
          are answered instead.</>}>
        <div className="grid gap-3 lg:grid-cols-3 items-start">
          <Caveat title="It only asks about next year"
            body={<>Every answer here is a one-year answer. Take any of them and the
              question comes back the following spring, bigger &mdash; the hole reaches{' '}
              {usdShort(last.cumulative)} by FY{last.fy}. That is the part you cannot get
              to without a projection.</>}
            link="See why it repeats" onClick={() => onJump('why')} />
          <Caveat title="It prices levers, not consequences"
            body={<>{usd(TARGETS[0])} of program cuts is {v.rows.find(r => r.id === 'cuts')?.ask ?? ''} —
              but which programs, in what order, is a choice somebody has to make, and
              the cost of it is not a dollar figure.</>}
            link="Read the answers in full" onClick={() => onJump('answers')} />
          <Caveat title="It does one lever at a time"
            body={<>Nobody will close this with a single lever, because most of them
              cannot reach. The real answer is a combination, and the only honest way to
              see a combination is to build one.</>}
            link="Build your own budget" onClick={() => onJump('adjust')} />
        </div>
        <Note>
          One thing the page deliberately does not do is rank these. Which lever is
          cheapest and which is right are different questions, and only the first one is
          arithmetic. Every card above is priced; not one of them is recommended.
        </Note>
      </Section>
    </div>
  )
}

function Caveat({ title, body, link, onClick }: {
  title: string; body: React.ReactNode; link: string; onClick: () => void
}) {
  return (
    <div className="card p-5">
      <h3 className="text-[15px] font-bold mb-2">{title}</h3>
      <p className="text-[13px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
        {body}
      </p>
      <button onClick={onClick}
        className="text-[12px] font-semibold mt-3" style={{ color: 'var(--series-cost)' }}>
        {link} &rarr;
      </button>
    </div>
  )
}
