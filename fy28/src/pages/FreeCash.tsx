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

export function FreeCash() {
  // OFF by default. Nothing on this page or anywhere else changes until somebody asks.
  const [on, setOn] = useState(false)
  const [target, setTarget] = useState(0.05)
  const [spread, setSpread] = useState(1)

  const pick = (t: number, sp: number) =>
    F.scenarios.find(s => Math.abs(s.target - t) < 1e-9 && s.spread === sp)
  const sc = pick(Math.round(target * 100) / 100, spread) ?? F.scenarios[0]
  const released = on ? sc.released : 0
  const walk = sc.years.map(y => ({
    fy: y.fy, amount: y.deficit,
    applied: on ? y.applied : 0,
    after: on ? y.after : y.deficit,
  }))
  const lastCovered = on ? [...walk].reverse().find(w => w.after === 0) : undefined

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
                        maxWidth: '46rem' }}>
        <label style={{ display: 'flex', gap: '.5rem', alignItems: 'center',
                        fontWeight: 600, marginBottom: '.85rem' }}>
          <input type="checkbox" checked={on} onChange={e => setOn(e.target.checked)} />
          Apply free cash to the projected gap
        </label>
        <p style={{ margin: '-.5rem 0 .9rem', fontSize: '.85rem',
                    color: 'var(--text-secondary)' }}>
          Off by default, and off everywhere else on this site. Free cash is one-time money
          and the projection is built without it; this shows what spending it would defer,
          not a plan.
        </p>

        <div style={{ opacity: on ? 1 : .45, pointerEvents: on ? 'auto' : 'none' }}>
        <label htmlFor="fc" style={{ display: 'block', fontWeight: 600, marginBottom: '.5rem' }}>
          Draw the balance down to {(target * 100).toFixed(0)}% of the budget
        </label>
        <input id="fc" type="range" min={0} max={0.08} step={0.01} value={target}
               onChange={e => setTarget(parseFloat(e.target.value))}
               style={{ width: '100%' }} />
        <div style={{ display: 'flex', justifyContent: 'space-between',
                      fontSize: '.8rem', color: 'var(--text-secondary)' }}>
          <span>0% — spend it all</span>
          <span>5% floor</span>
          <span>8%</span>
        </div>

        <div style={{ display: 'flex', gap: '.6rem', alignItems: 'center',
                      margin: '.75rem 0 0', fontSize: '.9rem' }}>
          <span style={{ fontWeight: 600 }}>spread over</span>
          {[1, 2, 3].map(n => (
            <button key={n} onClick={() => setSpread(n)}
              style={{ padding: '.2rem .6rem', cursor: 'pointer', borderRadius: '.3rem',
                       border: '1px solid var(--border)', color: 'inherit',
                       background: spread === n ? 'var(--surface-3)' : 'transparent' }}>
              {n} year{n > 1 ? 's' : ''}
            </button>
          ))}
        </div>
        </div>

        <p style={{ margin: '1rem 0 .5rem', fontSize: '1.1rem' }}>
          {released >= 0
            ? <>That releases <strong>{usd(released)}</strong>{' '}
                {target < F.bandLow
                  ? <span style={{ color: 'var(--bad, #a03232)' }}>— below the bottom of the band</span>
                  : null}</>
            : <>The balance is <strong>{usd(-released)}</strong> short of that target — this
                would mean adding money, not releasing it.</>}
        </p>

        {on && released > 0 && (
          <table style={{ borderCollapse: 'collapse', width: '100%', fontSize: '.9rem',
                          marginTop: '.75rem' }}>
            <thead>
              <tr style={{ textAlign: 'left', borderBottom: '1px solid var(--border)' }}>
                <th style={{ padding: '.3rem 0' }}>year</th>
                <th style={{ padding: '.3rem .8rem', textAlign: 'right' }}>projected gap</th>
                <th style={{ padding: '.3rem .8rem', textAlign: 'right' }}>free cash</th>
                <th style={{ padding: '.3rem .8rem', textAlign: 'right' }}>gap after</th>
              </tr>
            </thead>
            <tbody>
              {walk.map(w => (
                <tr key={w.fy} style={{ opacity: w.applied > 0 ? 1 : .5 }}>
                  <td style={{ padding: '.25rem 0' }}>FY{w.fy}</td>
                  <td style={{ padding: '.25rem .8rem', textAlign: 'right',
                               fontVariantNumeric: 'tabular-nums' }}>{usd(w.amount)}</td>
                  <td style={{ padding: '.25rem .8rem', textAlign: 'right',
                               fontVariantNumeric: 'tabular-nums',
                               color: w.applied > 0 ? 'var(--ok, #2f7d4f)' : 'inherit' }}>
                    {w.applied > 0 ? `−${usd(w.applied)}` : '—'}
                  </td>
                  <td style={{ padding: '.25rem .8rem', textAlign: 'right',
                               fontVariantNumeric: 'tabular-nums' }}>{usd(w.after)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        <p style={{ margin: '.9rem 0 0', fontWeight: 600 }}>
          {!on
            ? 'Turn it on to see what drawing the balance down would defer.'
            : lastCovered
              ? `Defers the gap through FY${lastCovered.fy}. Then it is gone, and the gap `
                + 'returns larger because the base kept growing.'
              : 'Releases nothing that fully covers even the first year of the gap.'}
        </p>
      </section>

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
