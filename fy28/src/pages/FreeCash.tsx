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

export function FreeCash() {
  const [target, setTarget] = useState(0.05)

  const released = Math.round(F.certified - F.budgetBase * Math.max(target, 0))
  let left = released
  const walk = F.deficits.map(d => {
    const before = left
    left -= d.amount
    return { ...d, covered: before >= d.amount, after: left }
  })
  const lastCovered = [...walk].reverse().find(w => w.covered)

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
        <label htmlFor="fc" style={{ display: 'block', fontWeight: 600, marginBottom: '.5rem' }}>
          Draw the balance down to {(target * 100).toFixed(0)}% of the budget
        </label>
        <input id="fc" type="range" min={0} max={0.08} step={0.005} value={target}
               onChange={e => setTarget(parseFloat(e.target.value))}
               style={{ width: '100%' }} />
        <div style={{ display: 'flex', justifyContent: 'space-between',
                      fontSize: '.8rem', color: 'var(--text-secondary)' }}>
          <span>0% — spend it all</span>
          <span>5% floor</span>
          <span>8%</span>
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

        {released > 0 && (
          <table style={{ borderCollapse: 'collapse', width: '100%', fontSize: '.9rem',
                          marginTop: '.75rem' }}>
            <thead>
              <tr style={{ textAlign: 'left', borderBottom: '1px solid var(--border)' }}>
                <th style={{ padding: '.3rem 0' }}>year</th>
                <th style={{ padding: '.3rem .8rem', textAlign: 'right' }}>projected gap</th>
                <th style={{ padding: '.3rem .8rem', textAlign: 'right' }}>left after</th>
              </tr>
            </thead>
            <tbody>
              {walk.map(w => (
                <tr key={w.fy} style={{ opacity: w.covered ? 1 : .45 }}>
                  <td style={{ padding: '.25rem 0' }}>FY{w.fy}</td>
                  <td style={{ padding: '.25rem .8rem', textAlign: 'right',
                               fontVariantNumeric: 'tabular-nums' }}>{usd(w.amount)}</td>
                  <td style={{ padding: '.25rem .8rem', textAlign: 'right',
                               fontVariantNumeric: 'tabular-nums',
                               color: w.after < 0 ? 'var(--bad, #a03232)' : 'inherit' }}>
                    {w.after < 0 ? 'exhausted' : usd(w.after)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        <p style={{ margin: '.9rem 0 0', fontWeight: 600 }}>
          {lastCovered
            ? `Defers the gap through FY${lastCovered.fy}. Then it is gone.`
            : 'Releases nothing that reaches even the first year of the gap.'}
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
