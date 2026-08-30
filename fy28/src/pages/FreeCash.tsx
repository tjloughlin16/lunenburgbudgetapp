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
 *  than a closed gap, because the money is one-time by construction. */

const F = MODEL.freeCash
const pct = (x: number) => `${(x * 100).toFixed(2)}%`
const OC = MODEL.freeCash.overrideContrast!
const LADDER = MODEL.freeCash.policyLadder

export function FreeCash() {
  // OFF by default. Nothing on this page or anywhere else changes until somebody asks.
  const [on, setOn] = useState(false)
  // LADDER runs high target -> low. Default to the bottom of the recommended band.
  const [idx, setIdx] = useState(LADDER.findIndex(l => Math.abs(l.target - 0.05) < 1e-9))
  const P = LADDER[idx] ?? LADDER[0]

  return (
    <div style={{ padding: '1.5rem 0 4rem' }}>
      <h2 style={{ marginTop: 0 }}>Free cash — how much is actually spendable</h2>
      <p style={{ maxWidth: '46rem' }}>
        Free cash is what the town may appropriate without raising taxes: the money left when
        the books close, mostly from budget lines that were not fully spent and revenue that
        came in above estimate. It is <strong>one-time money by construction</strong> — it is
        a variance, not an income stream.
      </p>

      <div style={{ display: 'flex', gap: '2rem', flexWrap: 'wrap', margin: '1.5rem 0' }}>
        <div>
          <div style={{ fontSize: '1.8rem', fontWeight: 600 }}>{usd(F.certified)}</div>
          <div style={{ color: 'var(--text-secondary)', fontSize: '.9rem' }}>
            certified, 1 July 2025 — a record
          </div>
        </div>
        <div>
          <div style={{ fontSize: '1.8rem', fontWeight: 600 }}>{pct(F.currentShare)}</div>
          <div style={{ color: 'var(--text-secondary)', fontSize: '.9rem' }}>
            of a {usd(F.budgetBase)} budget · band is{' '}
            {(F.bandLow * 100).toFixed(0)}–{(F.bandHigh * 100).toFixed(0)}%
          </div>
        </div>
        <div>
          <div style={{ fontSize: '1.8rem', fontWeight: 600 }}>{pct(F.normalShare)}</div>
          <div style={{ color: 'var(--text-secondary)', fontSize: '.9rem' }}>
            what a <em>normal</em> year generates
          </div>
        </div>
      </div>

      <section style={{ border: '1px solid var(--border, rgba(128,128,128,.25))',
                        borderRadius: '.5rem', padding: '1.25rem', margin: '1.5rem 0',
                        maxWidth: '48rem' }}>
        <label style={{ display: 'flex', gap: '.5rem', alignItems: 'center',
                        fontWeight: 600, marginBottom: '.75rem' }}>
          <input type="checkbox" checked={on} onChange={e => setOn(e.target.checked)} />
          Try it as a policy
        </label>
        <p style={{ margin: '-.35rem 0 1rem', fontSize: '.85rem',
                    color: 'var(--text-secondary)' }}>
          Off by default, and off everywhere else on this site. The published projection is
          built without free cash.
        </p>

        <div style={{ opacity: on ? 1 : .45, pointerEvents: on ? 'auto' : 'none' }}>
          <label htmlFor="fc" style={{ display: 'block', fontWeight: 600 }}>
            Hold the balance at {(P.target * 100).toFixed(0)}% of the budget
          </label>
          <div style={{ fontSize: '.85rem', color: P.inBand ? 'var(--ok, #2f7d4f)'
                                                            : 'var(--text-secondary)',
                        margin: '.15rem 0 .5rem' }}>
            {P.label}
          </div>
          <input id="fc" type="range" min={0} max={LADDER.length - 1} step={1}
                 value={LADDER.length - 1 - idx}
                 onChange={e => setIdx(LADDER.length - 1 - Number(e.target.value))}
                 style={{ width: '100%' }} />
          <div style={{ display: 'flex', justifyContent: 'space-between',
                        fontSize: '.78rem', color: 'var(--text-secondary)' }}>
            <span>0% — nothing held</span><span>5–7% band</span><span>8%</span>
          </div>
        </div>

        {on && (
          <div style={{ marginTop: '1.25rem' }}>
            <div style={{ display: 'flex', gap: '2rem', flexWrap: 'wrap',
                          marginBottom: '1rem' }}>
              <div>
                <div style={{ fontSize: '1.3rem', fontWeight: 600 }}>{usd(P.oneTime)}</div>
                <div style={{ fontSize: '.85rem', color: 'var(--text-secondary)' }}>
                  released once, by moving to this level
                </div>
              </div>
              <div>
                <div style={{ fontSize: '1.3rem', fontWeight: 600 }}>{usd(P.annual)}</div>
                <div style={{ fontSize: '.85rem', color: 'var(--text-secondary)' }}>
                  every year, by holding it there instead of accumulating
                </div>
              </div>
            </div>

            <table style={{ borderCollapse: 'collapse', width: '100%', fontSize: '.9rem' }}>
              <thead>
                <tr style={{ textAlign: 'left', borderBottom: '1px solid var(--border)' }}>
                  <th style={{ padding: '.3rem 0' }}>year</th>
                  <th style={{ padding: '.3rem .8rem', textAlign: 'right' }}>gap</th>
                  <th style={{ padding: '.3rem .8rem', textAlign: 'right' }}>free cash used</th>
                  <th style={{ padding: '.3rem 0 .3rem .8rem', textAlign: 'right' }}>gap after</th>
                </tr>
              </thead>
              <tbody>
                {P.years.map(y => (
                  <tr key={y.fy} style={{ borderBottom: '1px solid var(--border-subtle, rgba(128,128,128,.15))' }}>
                    <td style={{ padding: '.28rem 0' }}>FY{y.fy}</td>
                    <td style={{ padding: '.28rem .8rem', textAlign: 'right', fontVariantNumeric: 'tabular-nums' }}>{usd(y.before)}</td>
                    <td style={{ padding: '.28rem .8rem', textAlign: 'right', fontVariantNumeric: 'tabular-nums',
                                 color: y.applied > 0 ? 'var(--ok, #2f7d4f)' : 'inherit' }}>
                      {y.applied > 0 ? `−${usd(y.applied)}` : '—'}
                    </td>
                    <td style={{ padding: '.28rem 0 .28rem .8rem', textAlign: 'right', fontVariantNumeric: 'tabular-nums' }}>{usd(y.after)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <h3>The level you hold barely matters. The policy is everything.</h3>
      <p style={{ maxWidth: '46rem' }}>
        Move the slider and watch the second number stay still. That is the finding, and it
        is the opposite of how the argument is usually made.
      </p>
      <ul style={{ maxWidth: '46rem' }}>
        <li>
          <strong>Holding a lower balance is a one-off.</strong> Going from today's{' '}
          {pct(F.currentShare)} to the bottom of the band releases {usd(LADDER.find(l => Math.abs(l.target - F.bandLow) < 1e-9)!.oneTime)}{' '}
          — once. Going below that releases more on paper and achieves nothing, because you
          cannot apply more free cash to a year than that year's gap, and FY{F.deficits[0].fy}'s
          gap is only {usd(F.deficits[0].amount)}.
        </li>
        <li>
          <strong>Appropriating the flow every year is the policy</strong>, and it is worth
          far more: it takes the six-year gap from {usd(LADDER[0].gapLeftOneTimeOnly)} to{' '}
          {usd(LADDER[0].gapLeftWithPolicy)}. <strong>And it does not depend on the target
          at all.</strong> A lower target does not generate more money. It releases the
          accumulated stock sooner, and then you are living on the flow either way.
        </li>
      </ul>

      <h3>The catch, and it is the whole argument</h3>
      <p style={{ maxWidth: '46rem' }}>
        That {usd(F.sustainableDraw)} a year is what an ordinary year generates —{' '}
        {pct(F.normalShare)} of the budget, <strong>below the bottom of the band</strong>.
        And two thirds of it is money that was appropriated and never spent.
      </p>
      <p style={{ maxWidth: '46rem', fontWeight: 600 }}>
        So the policy is self-cancelling at the edges: the flow you would spend every year
        is produced by the over-appropriating you would be trying to stop. Budget more
        tightly and the gap shrinks — but so does the free cash you were going to close it
        with. You cannot bank on both.
      </p>

      <h3>It changes the amount, not the direction</h3>
      <p style={{ maxWidth: '46rem' }}>
        This site's argument is that cuts change the amount and only rates change the
        direction. <strong>Free cash is in the same category as a cut, and weaker</strong> — a
        cut persists year after year; free cash is spent once and gone. The gap grows by
        roughly {usd(Math.round((F.deficits[1].amount - F.deficits[0].amount)))} a year, so
        even <em>emptying the entire reserve</em> — drawing to 0%, which nobody proposes —
        defers the problem two years and leaves the town with no reserve at all.
      </p>

      <h3>Is this the same as an override? No — they are opposites</h3>
      <p style={{ maxWidth: '46rem' }}>
        The same dollars, spent once versus raised permanently. An override lifts the levy
        limit for good and the schools keep it every year after, growing at the{' '}
        {(OC.levyCap * 100).toFixed(1)}% cap. Free cash is spent and gone.
      </p>
      <div style={{ overflowX: 'auto', maxWidth: '46rem' }}>
        <table style={{ borderCollapse: 'collapse', width: '100%', fontSize: '.9rem' }}>
          <thead>
            <tr style={{ textAlign: 'left', borderBottom: '1px solid var(--border)' }}>
              <th style={{ padding: '.35rem .6rem .35rem 0' }}>year</th>
              <th style={{ padding: '.35rem .6rem', textAlign: 'right' }}>gap</th>
              <th style={{ padding: '.35rem .6rem', textAlign: 'right' }}>after {usd(OC.amount)} of free cash</th>
              <th style={{ padding: '.35rem 0 .35rem .6rem', textAlign: 'right' }}>after the same as an override</th>
            </tr>
          </thead>
          <tbody>
            {OC.years.map(y => (
              <tr key={y.fy} style={{ borderBottom: '1px solid var(--border-subtle, rgba(128,128,128,.15))' }}>
                <td style={{ padding: '.3rem .6rem .3rem 0' }}>FY{y.fy}</td>
                <td style={{ padding: '.3rem .6rem', textAlign: 'right', fontVariantNumeric: 'tabular-nums' }}>{usd(y.deficit)}</td>
                <td style={{ padding: '.3rem .6rem', textAlign: 'right', fontVariantNumeric: 'tabular-nums' }}>{usd(y.afterFreeCash)}</td>
                <td style={{ padding: '.3rem 0 .3rem .6rem', textAlign: 'right', fontVariantNumeric: 'tabular-nums' }}>{usd(y.afterOverride)}</td>
              </tr>
            ))}
            <tr style={{ fontWeight: 600 }}>
              <td style={{ padding: '.45rem .6rem .45rem 0' }}>six-year total</td>
              <td style={{ padding: '.45rem .6rem', textAlign: 'right', fontVariantNumeric: 'tabular-nums' }}>{usd(OC.cumulativeNone)}</td>
              <td style={{ padding: '.45rem .6rem', textAlign: 'right', fontVariantNumeric: 'tabular-nums' }}>{usd(OC.cumulativeFreeCash)}</td>
              <td style={{ padding: '.45rem 0 .45rem .6rem', textAlign: 'right', fontVariantNumeric: 'tabular-nums' }}>{usd(OC.cumulativeOverride)}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <p style={{ maxWidth: '46rem' }}>
        Identical dollars. Over six years the override is worth{' '}
        <strong>{usd(OC.cumulativeFreeCash - OC.cumulativeOverride)}</strong> more, because
        it arrives every year and free cash arrives once.
      </p>
      <p style={{ maxWidth: '46rem' }}>
        <strong>But look at the last column, not the total.</strong> Even the override does
        not close the gap — it leaves {usd(OC.years[OC.years.length - 1].afterOverride)} in
        FY{OC.years[OC.years.length - 1].fy}, and the shortfall grows every year. An override
        rises at {(OC.levyCap * 100).toFixed(1)}%; the cost of running the schools rises
        faster. A permanent revenue increase loses ground more slowly than one-time money
        does, and still loses ground. That is the whole argument of this site in one table:
        only a change in the growth rates changes the direction.
      </p>

      <h3>And a normal year does not refill it</h3>
      <p style={{ maxWidth: '46rem' }}>
        The {pct(F.currentShare)} exists because one component was unusually large. Unspent
        appropriations in 2025 were <strong>{usd(F.unspent2025)}</strong> against a 2021–24
        average of {usd(F.unspentAvg)} — <strong>2.49×</strong>, the biggest jump of nine
        comparable towns, while two of them fell. Hold everything else constant and put that
        one line back at its own average, and the town certifies{' '}
        <strong>{usd(F.normalCertified)}</strong>, which is <strong>{pct(F.normalShare)}</strong>
        {' '}— below the bottom of the band.
      </p>
      <p style={{ maxWidth: '46rem' }}>
        That is the strongest thing in this data. Not that the balance is low, but that
        <strong> the flow which refills it does not clear the floor in an ordinary year</strong>.
        You can draw down to 5% once. Holding 5% while spending requires the underspending to
        continue — which would mean the budgeting problem continuing.
      </p>

      <h3>Two claims, both true, different windows</h3>
      <blockquote style={{ borderLeft: '3px solid var(--border)', paddingLeft: '1rem',
                           margin: '1rem 0', maxWidth: '46rem',
                           color: 'var(--text-secondary)' }}>
        “This year, Lunenburg certified a record $3.354 million in free cash — 6.65% of the
        operating budget — well within DLS recommendations. {F.townHistory}”
        <div style={{ fontSize: '.85rem', marginTop: '.4rem' }}>
          — Town of Lunenburg, FY27 budget press release, page 6
        </div>
      </blockquote>
      <p style={{ maxWidth: '46rem' }}>
        Somebody saying the town is sitting on money is describing this year. Somebody saying
        it is rebuilding is describing the decade. Neither has to be wrong.
      </p>

      <h3 style={{ marginTop: '2rem' }}>What is ours, and what is not</h3>
      <ul style={{ maxWidth: '46rem' }}>
        <li>
          <strong>The band is single-sourced.</strong> {F.bandSource} At a lower threshold
          this balance is above the range rather than inside it, and the count of years the
          town fell short moves with it.
        </li>
        <li>
          <strong>The denominator is soft.</strong> The Town publishes 6.65%, implying a base
          of {usd(F.townImpliedBase)}; the FY26 original appropriation gives {pct(F.currentShare)}
          {' '}and the revised budget slightly less. We cannot reproduce the Town's base.
        </li>
        <li>
          <strong>{F.yearOffsetNote}</strong>
        </li>
        <li>
          <strong>The projection and free cash never meet in a calculation.</strong> The gap
          is built from budget columns; free cash is derived from actuals. They are placed
          side by side and subtracted, and the result is deferral, not a closed gap.
        </li>
        <li>
          <strong>No breakdown exists</strong> for the {usd(F.unspent2025)} of unspent
          appropriations. It is town-wide across 67 departments. Whether it is a few
          departments with vacancies or a systematic over-appropriation is the one question
          that would settle the argument, and nobody publishes it.
        </li>
      </ul>
    </div>
  )
}
