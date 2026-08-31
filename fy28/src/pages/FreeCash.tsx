import { useState } from 'react'
import { MODEL, usd } from '../model/engine'

/** Free cash: how much is spendable, and why it cannot bend the curve.
 *
 *  Built because two claims are argued about locally — that the town is too conservative
 *  and sitting on money, and that free cash is "not up to standard" so the town is
 *  rebuilding. The Town's own budget release contains both, and both are true of different
 *  windows.
 *
 *  The slider goes below the band on purpose. "What if we spent it all" is the question
 *  people actually ask, and the answer — two years — is more persuasive than any argument
 *  about prudence.
 *
 *  RULE 1. The projection is built from budget columns. Free cash is derived from actuals.
 *  They are subtracted here and nowhere else, and the result is labelled deferral rather
 *  than a closed gap, because the money is one-time by construction.
 *
 *  ON THE STYLING, because it was wrong in public for a while. This page and the rate
 *  register shipped with inline styles and no class names at all, which meant neither got
 *  the site's container: content ran to the left edge of the window, headings rendered at
 *  the browser's default size so they read as body text, and sections had no space between
 *  them. Every other page opens with `mx-auto max-w-6xl px-5`, and now so does this one.
 *  A page that looks broken is not read, however good the arithmetic behind it is. */

const F = MODEL.freeCash
const pct = (x: number) => `${(x * 100).toFixed(2)}%`
const OC = MODEL.freeCash.overrideContrast!
const LADDER = MODEL.freeCash.policyLadder

/** One figure and its caption, the way every other page states a headline number. */
function Stat({ value, children }: { value: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="text-3xl font-bold tnum tracking-tight">{value}</div>
      <div className="text-[13px] leading-snug mt-1 max-w-[15rem]"
        style={{ color: 'var(--text-secondary)' }}>{children}</div>
    </div>
  )
}

function H2({ children }: { children: React.ReactNode }) {
  return <h2 className="text-2xl font-bold tracking-tight mt-12 mb-3 max-w-3xl">{children}</h2>
}

function Body({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-[15px] leading-relaxed max-w-2xl mt-3"
      style={{ color: 'var(--text-secondary)' }}>{children}</p>
  )
}

const TH = 'text-right font-bold uppercase tracking-widest text-[10px] pb-1 pl-3'
const TH_L = 'text-left font-bold uppercase tracking-widest text-[10px] pb-1'

export function FreeCash() {
  // OFF by default. Nothing on this page or anywhere else changes until somebody asks.
  const [on, setOn] = useState(false)
  // LADDER runs high target -> low. Default to the bottom of the recommended band.
  const [idx, setIdx] = useState(LADDER.findIndex(l => Math.abs(l.target - 0.05) < 1e-9))
  const P = LADDER[idx] ?? LADDER[0]

  return (
    <div className="mx-auto max-w-6xl px-5 pt-14 pb-16">
      <p className="text-xs font-semibold uppercase tracking-widest mb-3"
        style={{ color: 'var(--text-muted)' }}>One-time money</p>
      <h1 className="text-4xl sm:text-5xl font-bold tracking-tight leading-[1.05] max-w-3xl">
        Free cash &mdash; how much is actually spendable
      </h1>
      <p className="mt-5 text-lg leading-relaxed max-w-2xl"
        style={{ color: 'var(--text-secondary)' }}>
        Free cash is what the town may appropriate without raising taxes: the money left
        when the books close, mostly from budget lines that were not fully spent and revenue
        that came in above estimate. It is <strong>one-time money by construction</strong>
        {' '}&mdash; a variance, not an income stream.
      </p>

      <div className="mt-10 flex flex-wrap gap-x-12 gap-y-6">
        <Stat value={usd(F.certified)}>certified, 1 July 2025 &mdash; a record</Stat>
        <Stat value={pct(F.currentShare)}>
          of a {usd(F.budgetBase)} budget &middot; band is{' '}
          {(F.bandLow * 100).toFixed(0)}&ndash;{(F.bandHigh * 100).toFixed(0)}%
        </Stat>
        <Stat value={pct(F.normalShare)}>what a <em>normal</em> year generates</Stat>
      </div>

      <section className="card p-5 mt-10 max-w-3xl">
        <label className="flex gap-2 items-center font-bold text-[15px]">
          <input type="checkbox" checked={on} onChange={e => setOn(e.target.checked)} />
          Try it as a policy
        </label>
        <p className="text-[13px] leading-relaxed mt-2 mb-5"
          style={{ color: 'var(--text-secondary)' }}>
          Off by default, and off everywhere else on this site. The published projection is
          built without free cash.
        </p>

        <div style={{ opacity: on ? 1 : .45, pointerEvents: on ? 'auto' : 'none' }}>
          <label htmlFor="fc" className="block font-bold text-[15px]">
            Hold the balance at {(P.target * 100).toFixed(0)}% of the budget
          </label>
          <div className="text-[13px] mt-0.5 mb-2"
            style={{ color: P.inBand ? 'var(--status-good)' : 'var(--text-secondary)' }}>
            {P.label}
          </div>
          <input id="fc" type="range" min={0} max={LADDER.length - 1} step={1}
            className="w-full"
            value={LADDER.length - 1 - idx}
            onChange={e => setIdx(LADDER.length - 1 - Number(e.target.value))} />
          <div className="flex justify-between text-[11px] mt-1"
            style={{ color: 'var(--text-muted)' }}>
            <span>0% &mdash; nothing held</span><span>5&ndash;7% band</span><span>8%</span>
          </div>
        </div>

        {on && (
          <div className="mt-6">
            <div className="flex flex-wrap gap-x-10 gap-y-4 mb-5">
              <div>
                <div className="text-xl font-bold tnum">{usd(P.oneTime)}</div>
                <div className="text-[12px] mt-0.5 max-w-[16rem]"
                  style={{ color: 'var(--text-secondary)' }}>
                  released once, by moving to this level
                </div>
              </div>
              <div>
                <div className="text-xl font-bold tnum">{usd(P.annual)}</div>
                <div className="text-[12px] mt-0.5 max-w-[16rem]"
                  style={{ color: 'var(--text-secondary)' }}>
                  every year, by holding it there instead of accumulating
                </div>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-[13px] tnum">
                <thead>
                  <tr style={{ color: 'var(--text-muted)' }}>
                    <th className={TH_L}>FY</th>
                    <th className={TH}>gap</th>
                    <th className={TH}>free cash used</th>
                    <th className={TH}>gap after</th>
                  </tr>
                </thead>
                <tbody>
                  {P.years.map(y => (
                    <tr key={y.fy} className="border-t"
                      style={{ borderColor: 'var(--surface-3)' }}>
                      <td className="py-1 font-semibold">FY{y.fy}</td>
                      <td className="py-1 pl-3 text-right">{usd(y.before)}</td>
                      <td className="py-1 pl-3 text-right"
                        style={{ color: y.applied > 0 ? 'var(--status-good)' : 'inherit' }}>
                        {y.applied > 0 ? `−${usd(y.applied)}` : '—'}
                      </td>
                      <td className="py-1 pl-3 text-right">{usd(y.after)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </section>

      <H2>The level you hold barely matters. The policy is everything.</H2>
      <Body>
        Move the slider and watch the second number stay still. That is the finding, and it
        is the opposite of how the argument is usually made.
      </Body>
      <ul className="mt-4 grid gap-3 max-w-2xl">
        <li className="card p-4 text-[14px] leading-relaxed"
          style={{ color: 'var(--text-secondary)' }}>
          <strong style={{ color: 'var(--text-primary)' }}>Holding a lower balance is a
          one-off.</strong> Going from today&rsquo;s {pct(F.currentShare)} to the bottom of
          the band releases{' '}
          {usd(LADDER.find(l => Math.abs(l.target - F.bandLow) < 1e-9)!.oneTime)} &mdash;
          once. Going below that releases more on paper and achieves nothing, because you
          cannot apply more free cash to a year than that year&rsquo;s gap, and
          FY{F.deficits[0].fy}&rsquo;s gap is only {usd(F.deficits[0].amount)}.
        </li>
        <li className="card p-4 text-[14px] leading-relaxed"
          style={{ color: 'var(--text-secondary)' }}>
          <strong style={{ color: 'var(--text-primary)' }}>Appropriating the flow every year
          is the policy</strong>, and it is worth far more: it takes the six-year gap from{' '}
          {usd(LADDER[0].gapLeftOneTimeOnly)} to {usd(LADDER[0].gapLeftWithPolicy)}.{' '}
          <strong style={{ color: 'var(--text-primary)' }}>And it does not depend on the
          target at all.</strong> A lower target does not generate more money. It releases
          the accumulated stock sooner, and then you are living on the flow either way.
        </li>
      </ul>

      <H2>The catch, and it is the whole argument</H2>
      <Body>
        That {usd(F.sustainableDraw)} a year is what an ordinary year generates &mdash;{' '}
        {pct(F.normalShare)} of the budget, <strong>below the bottom of the band</strong>.
        And two thirds of it is money that was appropriated and never spent.
      </Body>
      <p className="text-[15px] leading-relaxed max-w-2xl mt-4 font-semibold">
        So the policy is self-cancelling at the edges: the flow you would spend every year is
        produced by the over-appropriating you would be trying to stop. Budget more tightly
        and the gap shrinks &mdash; but so does the free cash you were going to close it
        with. You cannot bank on both.
      </p>

      <H2>It changes the amount, not the direction</H2>
      <Body>
        This site&rsquo;s argument is that cuts change the amount and only rates change the
        direction. <strong>Free cash is in the same category as a cut, and weaker</strong>
        {' '}&mdash; a cut persists year after year; free cash is spent once and gone. The gap
        grows by roughly {usd(Math.round(F.deficits[1].amount - F.deficits[0].amount))} a
        year, so even <em>emptying the entire reserve</em> &mdash; drawing to 0%, which
        nobody proposes &mdash; defers the problem two years and leaves the town with no
        reserve at all.
      </Body>

      <H2>Is this the same as an override? No &mdash; they are opposites</H2>
      <Body>
        The same dollars, spent once versus raised permanently. An override lifts the levy
        limit for good and the schools keep it every year after, growing at the{' '}
        {(OC.levyCap * 100).toFixed(1)}% cap. Free cash is spent and gone.
      </Body>
      <div className="overflow-x-auto mt-5 max-w-3xl">
        <table className="w-full text-[13px] tnum">
          <thead>
            <tr style={{ color: 'var(--text-muted)' }}>
              <th className={TH_L}>FY</th>
              <th className={TH}>gap</th>
              <th className={TH}>after {usd(OC.amount)} of free cash</th>
              <th className={TH}>after the same as an override</th>
            </tr>
          </thead>
          <tbody>
            {OC.years.map(y => (
              <tr key={y.fy} className="border-t" style={{ borderColor: 'var(--surface-3)' }}>
                <td className="py-1 font-semibold">FY{y.fy}</td>
                <td className="py-1 pl-3 text-right">{usd(y.deficit)}</td>
                <td className="py-1 pl-3 text-right">{usd(y.afterFreeCash)}</td>
                <td className="py-1 pl-3 text-right">{usd(y.afterOverride)}</td>
              </tr>
            ))}
            <tr className="border-t-2 font-bold" style={{ borderColor: 'var(--text-muted)' }}>
              <td className="py-1.5">six-year total</td>
              <td className="py-1.5 pl-3 text-right">{usd(OC.cumulativeNone)}</td>
              <td className="py-1.5 pl-3 text-right">{usd(OC.cumulativeFreeCash)}</td>
              <td className="py-1.5 pl-3 text-right">{usd(OC.cumulativeOverride)}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <Body>
        Identical dollars. Over six years the override is worth{' '}
        <strong>{usd(OC.cumulativeFreeCash - OC.cumulativeOverride)}</strong> more, because
        it arrives every year and free cash arrives once.
      </Body>
      <Body>
        <strong>But look at the last column, not the total.</strong> Even the override does
        not close the gap &mdash; it leaves{' '}
        {usd(OC.years[OC.years.length - 1].afterOverride)} in
        FY{OC.years[OC.years.length - 1].fy}, and the shortfall grows every year. An override
        rises at {(OC.levyCap * 100).toFixed(1)}%; the cost of running the schools rises
        faster. A permanent revenue increase loses ground more slowly than one-time money
        does, and still loses ground. That is the whole argument of this site in one table:
        only a change in the growth rates changes the direction.
      </Body>

      <H2>And a normal year does not refill it</H2>
      <Body>
        The {pct(F.currentShare)} exists because one component was unusually large. Unspent
        appropriations in 2025 were <strong>{usd(F.unspent2025)}</strong> against a
        2021&ndash;24 average of {usd(F.unspentAvg)} &mdash; <strong>2.49&times;</strong>,
        the biggest jump of nine comparable towns, while two of them fell. Hold everything
        else constant and put that one line back at its own average, and the town certifies{' '}
        <strong>{usd(F.normalCertified)}</strong>, which is{' '}
        <strong>{pct(F.normalShare)}</strong> &mdash; below the bottom of the band.
      </Body>
      <Body>
        That is the strongest thing in this data. Not that the balance is low, but that{' '}
        <strong>the flow which refills it does not clear the floor in an ordinary
        year</strong>. You can draw down to 5% once. Holding 5% while spending requires the
        underspending to continue &mdash; which would mean the budgeting problem continuing.
      </Body>

      <H2>Two claims, both true, different windows</H2>
      <blockquote className="border-l-[3px] pl-4 mt-5 max-w-2xl text-[15px] leading-relaxed"
        style={{ borderColor: 'var(--surface-3)', color: 'var(--text-secondary)' }}>
        &ldquo;This year, Lunenburg certified a record $3.354 million in free cash &mdash;
        6.65% of the operating budget &mdash; well within DLS recommendations.{' '}
        {F.townHistory}&rdquo;
        <div className="text-[12px] mt-2" style={{ color: 'var(--text-muted)' }}>
          &mdash; Town of Lunenburg, FY27 budget press release, page 6
        </div>
      </blockquote>
      <Body>
        Somebody saying the town is sitting on money is describing this year. Somebody saying
        it is rebuilding is describing the decade. Neither has to be wrong.
      </Body>

      <H2>What is ours, and what is not</H2>
      <ul className="mt-4 grid gap-3 max-w-2xl">
        {[
          [<>The band is single-sourced.</>, <>{F.bandSource} At a lower threshold this
            balance is above the range rather than inside it, and the count of years the
            town fell short moves with it.</>],
          [<>The denominator is soft.</>, <>The Town publishes 6.65%, implying a base of{' '}
            {usd(F.townImpliedBase)}; the FY26 original appropriation gives{' '}
            {pct(F.currentShare)} and the revised budget slightly less. We cannot reproduce
            the Town&rsquo;s base.</>],
          [<>The years are labelled differently.</>, <>{F.yearOffsetNote}</>],
          [<>The projection and free cash never meet in a calculation.</>, <>The gap is
            built from budget columns; free cash is derived from actuals. They are placed
            side by side and subtracted, and the result is deferral, not a closed gap.</>],
          [<>No breakdown exists.</>, <>For the {usd(F.unspent2025)} of unspent
            appropriations there is a town-wide total across 67 departments and nothing
            more. Whether it is a few departments with vacancies or a systematic
            over-appropriation is the one question that would settle the argument, and
            nobody publishes it.</>],
        ].map(([head, body], i) => (
          <li key={i} className="card p-4 text-[14px] leading-relaxed"
            style={{ color: 'var(--text-secondary)' }}>
            <strong style={{ color: 'var(--text-primary)' }}>{head}</strong> {body}
          </li>
        ))}
      </ul>
    </div>
  )
}
