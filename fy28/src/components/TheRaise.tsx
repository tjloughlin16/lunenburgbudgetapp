import type { ReactNode } from 'react'
import { usd, usdShort } from '../model/engine'
import { nextYear, RATE_LINES, run, DEFAULT_SCENARIO, LEVY_CAP,
         type Bucket } from '../model/rates'

const N = nextYear()
const pct = (x: number, d = 0) => `${(x * 100).toFixed(d)}%`

/** Distinct enough to tell apart, and never the only carrier of meaning — every segment
 *  is also a labelled row in the table underneath. */
const COLOR: Record<Bucket, string> = {
  salaries: 'var(--series-cost)',
  health: 'var(--series-revenue)',
  transport: 'var(--status-warning)',
  sped_tuition: 'var(--status-serious)',
  other: 'var(--axis)',
  utilities: 'var(--text-muted)',
}

/** Next year as a budget of the increase.
 *
 *  Every other view here is a budget of the total, and a total is the wrong unit for the
 *  argument the town is actually having: nobody disputes the size of the school budget,
 *  they dispute whether a 2½% raise ought to cover it. So this puts the raise on the table
 *  as one fixed number of dollars and lets each cost line take its bite in order.
 *
 *  The bar is scaled to what the six lines WANT rather than to what exists, so the part
 *  that does not fit is drawn rather than described. Everything past the marker is a
 *  service that has to be cut, a fee that has to be raised, or a ballot question. */
export function TheRaise() {
  const scale = (x: number) => `${(x / N.costTotal) * 100}%`
  const allowedPct = N.allowed / N.costTotal
  let running = 0

  return (
    <div>
      <div className="grid gap-3 sm:grid-cols-3 mb-4">
        <Fact label="The increase for next year" value={usdShort(N.allowed)}
          sub={`The town gave the schools ${usd(N.appropFy27)} this year. Town revenue rises `
            + `${pct(N.growthRate, 2)}, so next year it can give ${usd(N.allowed)} more than `
            + `it did. That is the entire increase.`} />
        <Fact label="What standing still costs" value={usdShort(N.costTotal)} tone="critical"
          sub={`What the same staff, the same buses and the same buildings cost next year, `
            + `one year older. Nobody is hired and nothing is added.`} />
        <Fact label={'Next year\u2019s gap'} value={usdShort(N.gap)} tone="critical"
          sub={`${usd(-N.leftOver)} of it is costs outrunning the increase — standing still `
            + `takes ${pct(N.consumed)} of it. The other ${usd(N.startingBehind)} is what `
            + `the district was already behind before anything grew.`} />
      </div>

      {/* ---- the bar ---- */}
      <div className="card p-4">
        <h3 className="text-[15px] font-bold">
          What the increase has to cover
        </h3>
        <p className="text-[12px] mt-1 mb-4" style={{ color: 'var(--text-secondary)' }}>
          The full width is what next year costs if nothing changes. The top band is who
          wants the money; the band underneath is the same span coloured only by whether
          there is money for it. The mark is where it runs out. Everything past the mark
          has to come from somewhere else, and no rearranging of the segments makes it fit.
          This bar is about the increase only &mdash; next year&rsquo;s full gap is{' '}
          {usd(N.gap)}, because the district also starts {usd(N.startingBehind)} behind.
        </p>

        <div className="relative">
          {/* who wants the money */}
          <div className="flex h-9 rounded-t-lg overflow-hidden"
            style={{ background: 'var(--surface-3)' }}>
            {N.costs.map(c => (
              <div key={c.key} style={{ width: scale(c.amount), background: COLOR[c.key] }}
                title={`${c.label} +${usd(c.amount)}`} />
            ))}
          </div>

          {/* the same span again, coloured only by whether it is paid for.
              The segmented bar answers "who spends it" and cannot answer "where does this
              stop working", because the eye has to find a thin mark among six colours.
              This one carries the verdict and nothing else. */}
          <div className="flex h-6 rounded-b-lg overflow-hidden">
            <div className="flex items-center justify-start pl-2"
              style={{ width: `${allowedPct * 100}%`, background: 'var(--status-good)' }}
              title={`Paid for by the increase: ${usd(N.allowed)}`}>
              <span className="hidden sm:block text-[10px] font-bold whitespace-nowrap"
                style={{ color: '#fff' }}>
                {usdShort(N.allowed)} the town can pay for
              </span>
            </div>
            <div className="flex-1 flex items-center justify-end pr-2"
              style={{ background: 'var(--status-critical)' }}
              title={`Not paid for: ${usd(-N.leftOver)}`}>
              <span className="hidden sm:block text-[10px] font-bold whitespace-nowrap"
                style={{ color: '#fff' }}>
                {usdShort(-N.leftOver)} it cannot
              </span>
            </div>
          </div>

          {/* everything to the right of this is what has to come from somewhere else */}
          <div className="absolute inset-y-0 pointer-events-none"
            style={{ left: `${allowedPct * 100}%`, width: 3, marginLeft: -1.5,
                     background: 'var(--text-primary)' }} />
        </div>

        <div className="relative h-10 mt-1.5 text-[11px]">
          <span className="absolute -translate-x-1/2 text-center leading-tight w-32"
            style={{ left: `${allowedPct * 100}%`, color: 'var(--text-primary)' }}>
            <strong>{usdShort(N.allowed)}</strong><br />
            <span style={{ color: 'var(--text-muted)' }}>where the money runs out</span>
          </span>
          {/* the amount lives in the red band itself now; this says what happens to it */}
          <span className="absolute right-0 text-right leading-tight"
            style={{ color: 'var(--text-muted)' }}>
            cut it, charge for it,<br />or vote for it
          </span>
        </div>

        <table className="stack w-full text-[13px] tnum mt-4">
          <caption className="sr-only">
            Each cost line&rsquo;s increase next year and the share of the available revenue
            increase it consumes
          </caption>
          <thead>
            <tr className="text-left" style={{ color: 'var(--text-muted)' }}>
              <th className="font-semibold py-1.5">Line</th>
              <th className="font-semibold py-1.5 text-right">Grows</th>
              <th className="font-semibold py-1.5 text-right">Costs more</th>
              <th className="font-semibold py-1.5 text-right">Share of the increase</th>
              <th className="font-semibold py-1.5 text-right">Running</th>
            </tr>
          </thead>
          <tbody>
            {N.costs.map(c => {
              running += c.amount
              const over = running > N.allowed
              return (
                <tr key={c.key} className="border-t" style={{ borderColor: 'var(--grid)' }}>
                  <td className="rowhead py-1.5 font-semibold">
                    <span aria-hidden="true"
                      className="inline-block w-2.5 h-2.5 rounded-sm mr-2 align-middle"
                      style={{ background: COLOR[c.key] }} />
                    {c.label}
                  </td>
                  <td data-label="Grows" className="py-1.5 text-right">{pct(c.rate, 1)}</td>
                  <td data-label="Costs more" className="py-1.5 text-right">
                    +{usd(c.amount)}
                  </td>
                  <td data-label="Share of the increase" className="py-1.5 text-right font-semibold">
                    {pct(c.shareOfAllowed)}
                  </td>
                  <td data-label="Running" className="py-1.5 text-right font-semibold"
                    style={{ color: over ? 'var(--status-critical)' : 'var(--text-secondary)' }}>
                    {pct(running / N.allowed)}
                  </td>
                </tr>
              )
            })}
            <tr className="border-t-2" style={{ borderColor: 'var(--text-primary)' }}>
              <td className="rowhead py-1.5 font-bold">All six</td>
              <td className="py-1.5" />
              <td data-label="Costs more" className="py-1.5 text-right font-bold">
                +{usd(N.costTotal)}
              </td>
              <td className="py-1.5" />
              <td data-label="Running" className="py-1.5 text-right font-bold"
                style={{ color: 'var(--status-critical)' }}>{pct(N.consumed)}</td>
            </tr>
          </tbody>
        </table>

        <p className="text-[13px] leading-relaxed mt-4 pt-3 border-t"
          style={{ borderColor: 'var(--grid)' }}>
          <strong>Health insurance alone takes {pct(N.costs[1].shareOfAllowed)} of the
          increase</strong> while being{' '}
          {pct(RATE_LINES.find(l => l.key === N.costs[1].key)!.weight, 0)} of the budget.
          Salaries take{' '}
          {pct(N.costs[0].shareOfAllowed)} on their own. By the third line the money has
          run out, and there are three more lines. Nothing in this table is new spending
          &mdash; it is the same staff, the same buses and the same buildings, a year older.
        </p>
      </div>

      {/* ---- the same money, asked as a fairness question ---- */}
      <WithinShare />

      {/* ---- where the raise came from, and the piece nobody counts ---- */}
      <div className="grid gap-3 lg:grid-cols-2 items-start mt-4">
        <div className="card p-4">
          <h4 className="text-[14px] font-bold mb-1">Where the {usdShort(N.allowed)} comes from</h4>
          <p className="text-[12px] mb-3" style={{ color: 'var(--text-secondary)' }}>
            Proposition 2½ is the largest piece but not the whole of it. The schools take
            their share of whatever the town collects.
          </p>
          <ul className="space-y-2">
            {N.sources.map(s => (
              <li key={s.label} className="border-t pt-2" style={{ borderColor: 'var(--grid)' }}>
                <div className="flex items-baseline justify-between gap-3">
                  <span className="text-[13px] font-medium">{s.label}</span>
                  <span className="text-[13px] font-semibold tnum shrink-0">
                    {usd(s.toSchools)}
                  </span>
                </div>
                <p className="text-[11px] mt-0.5" style={{ color: 'var(--text-muted)' }}>
                  {s.note}
                </p>
              </li>
            ))}
          </ul>
        </div>

        <div className="card p-4">
          <h4 className="text-[14px] font-bold mb-1">And it starts behind</h4>
          <p className="text-[13px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
            Before anything grows, the district is already spending{' '}
            <strong style={{ color: 'var(--text-primary)' }}>{usd(N.startingBehind)}</strong>{' '}
            more than it was appropriated this year &mdash; the special town meeting
            add-backs cost more than the special town meeting funded.
          </p>
          <dl className="text-[13px] mt-3 rounded-lg overflow-hidden"
            style={{ background: 'var(--surface-3)' }}>
            {[
              ['Already behind', N.startingBehind],
              ['What the six lines add', N.costTotal],
              ['Less the increase', -N.allowed],
            ].map(([k, v]) => (
              <div key={k as string} className="flex justify-between gap-3 px-3 py-1.5">
                <dt style={{ color: 'var(--text-secondary)' }}>{k}</dt>
                <dd className="tnum font-semibold">{usd(v as number)}</dd>
              </div>
            ))}
            <div className="flex justify-between gap-3 px-3 py-2 border-t"
              style={{ borderColor: 'var(--grid)' }}>
              <dt className="font-bold">Next year&rsquo;s gap</dt>
              <dd className="tnum font-bold" style={{ color: 'var(--status-critical)' }}>
                {usd(N.gap)}
              </dd>
            </div>
          </dl>
          <p className="text-[11px] mt-2" style={{ color: 'var(--text-muted)' }}>
            The same {usd(N.gap)} the rest of this site starts from, rebuilt from the
            increase rather than from the total.
          </p>
        </div>
      </div>
    </div>
  )
}

/** Who is living within the increase and who is not, drawn the same way as the bar above.
 *
 *  Was a diverging bar of overdrafts alone, which is a compact way to rank them and a
 *  poor way to understand them: it showed the excess without showing what it was an excess
 *  OF, so a reader had to hold the affordable amount in their head to make sense of it.
 *
 *  Now every line gets the same picture the whole budget got — green up to what it can
 *  afford, red past it, with a tick where the affordable amount ends. Bars share one
 *  dollar scale, so length is what the line costs and colour is whether it fits. Health
 *  insurance is the shorter bar and the redder one, which is the entire point and was
 *  invisible in the ranking. */
function WithinShare() {
  const rows = N.costs.slice().sort((a, b) => b.overdraft - a.overdraft)
  const max = Math.max(...rows.map(r => r.amount))
  const w = (x: number) => `${(x / max) * 100}%`

  return (
    <div className="card p-4 mt-4">
      <h3 className="text-[15px] font-bold">Which lines live within the increase</h3>
      <p className="text-[12px] mt-1 mb-1" style={{ color: 'var(--text-secondary)' }}>
        The bar above shows the money runs out, but a large line takes a large share of any
        increase and looks guilty simply for being large. So here is each line on its own,
        drawn the same way.
      </p>
      <p className="text-[12px] mb-4" style={{ color: 'var(--text-secondary)' }}>
        <span style={{ color: 'var(--status-good)' }}>&#9632;</span> Green is growth the
        increase pays for &mdash; up to <strong>{pct(N.affordableRate, 2)}</strong>, the rate
        every line could grow at if the {usdShort(N.allowed)} were exactly used up.{' '}
        <span style={{ color: 'var(--status-critical)' }}>&#9632;</span> Red is what the
        line takes above that, which has to come from somewhere else. The tick is where the
        money for that line runs out.
      </p>

      <ul className="space-y-2.5">
        {rows.map(r => (
          <li key={r.key}>
            <div className="flex items-baseline justify-between gap-3 mb-1">
              <span className="text-[12px] font-medium truncate" title={r.label}>
                {r.label}
                <span className="ml-1.5" style={{ color: 'var(--text-muted)' }}>
                  grows {pct(r.rate, 1)}
                </span>
              </span>
              <span className="text-[12px] font-semibold tnum shrink-0"
                style={{ color: r.fits ? 'var(--status-good)' : 'var(--status-critical)' }}>
                {r.fits ? `fits, with ${usd(-r.overdraft)} to spare`
                  : `${usd(r.overdraft)} over · ${r.multiple.toFixed(2)}\u00d7 its share`}
              </span>
            </div>
            <div className="relative h-5 rounded" style={{ background: 'var(--surface-3)' }}>
              <div className="absolute inset-y-0 left-0 flex rounded overflow-hidden"
                style={{ width: w(r.amount) }}>
                <div style={{ width: `${(Math.min(r.amount, r.share) / r.amount) * 100}%`,
                              background: 'var(--status-good)' }} />
                {!r.fits && (
                  <div style={{ width: `${(r.overdraft / r.amount) * 100}%`,
                                background: 'var(--status-critical)' }} />
                )}
              </div>
              {/* where the money for this line runs out — past the bar's end when it fits */}
              <div className="absolute inset-y-0" aria-hidden="true"
                style={{ left: w(r.share), width: 2, marginLeft: -1,
                         background: 'var(--text-primary)' }} />
            </div>
          </li>
        ))}
      </ul>

      <p className="text-[13px] leading-relaxed mt-4 pt-3 border-t"
        style={{ borderColor: 'var(--grid)' }}>
        <strong>Salaries have the longest bar and health insurance has the reddest one.</strong>{' '}
        That is the difference between costing a lot and being the problem: salaries take{' '}
        {rows.find(r => r.key === 'salaries')!.multiple.toFixed(2)}&times; their share
        because they are two thirds of the budget, while health insurance takes{' '}
        {rows[0].multiple.toFixed(2)}&times; theirs and is{' '}
        {Math.round((rows[0].overdraft / -N.leftOver) * 100)}% of the whole shortfall on
        its own.
      </p>
      <p className="text-[13px] leading-relaxed mt-2">
        One line out of six fits, and it fits by {usd(-rows[rows.length - 1].overdraft)}. It
        is &ldquo;everything else&rdquo; &mdash; supplies, materials, technology, athletics,
        clubs &mdash; the only line the School Committee fully controls, the only one it has
        actually been cutting, and the only one that was never the problem. The red segments
        add up to {usd(-N.leftOver)} &mdash; exactly the part of next year&rsquo;s{' '}
        {usd(N.gap)} gap that comes from costs outrunning the increase.
      </p>
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
      <p className="text-2xl font-bold tnum leading-none" style={{
        color: tone === 'critical' ? 'var(--status-critical)' : 'var(--text-primary)' }}>
        {value}
      </p>
      <p className="text-xs mt-2 leading-relaxed" style={{ color: 'var(--text-secondary)' }}>{sub}</p>
    </div>
  )
}

/** The whole projection as one table, with the Prop 2½ increase already taken off.
 *
 *  Added because a reader who had followed everything else still asked the most reasonable
 *  question on the page — "what is the deficit AFTER you subtract the 2½% allowance?" —
 *  and nothing here answered it directly. Every figure existed; none of them were beside
 *  each other. Revenue rises in its own column so it is visibly not being ignored, and
 *  the last two columns separate the two things that both get called the gap.
 *
 *  The running total is what the rest of the site quotes and it is cumulative: FY29's
 *  $1.18M includes FY28's $613k rather than sitting on top of it. The last column is the
 *  money that is genuinely new that year, and it is the one to read — roughly $600,000
 *  every year, for ever, and rising. */
export function YearLedger({ overrideLevy = 0, title, intro, footer }: {
  /** A school override passed in the first year, carried forward at the levy cap. */
  overrideLevy?: number
  title: string
  intro: ReactNode
  /** Given the numbers the table just computed, so the prose cannot drift from them. */
  footer: (ctx: { years: ReturnType<typeof run>; grew: number[]; avg: number }) => ReactNode
}) {
  const years = run(10, { ...DEFAULT_SCENARIO, overrideLevy })
  const overrideAt = (i: number) => overrideLevy * (1 + LEVY_CAP) ** i
  /* Simple difference between adjacent rows, starting from what FY27 is already behind.
   *
   * The obvious thing, and it was not what this column did. It used the "fresh" measure —
   * net of the growth last year's fix would itself have produced — which is the right
   * concept for the override treadmill and the wrong one here, because its first year is
   * computed differently from all the others: it counts the whole $613,238 as new,
   * ignoring the $103,724 the district was already behind. That inflated FY28 and made
   * FY29 look like a fall in a series that only ever rises.
   *
   * This version can be checked by subtracting the column beside it, and its first year
   * is the same $509,515 the top of the section already names. */
  const grew = years.map((y, i) =>
    y.gap - (i === 0 ? N.startingBehind : years[i - 1].gap))
  const avg = Math.round(grew.reduce((a, b) => a + b, 0) / grew.length)

  return (
    <div className="card p-4">
      <h3 className="text-[15px] font-bold">{title}</h3>
      <div className="text-[12px] mt-1 mb-3" style={{ color: 'var(--text-secondary)' }}>
        {intro}
      </div>
      <table className="stack w-full text-[13px] tnum">
        <caption className="sr-only">
          Cost of level service, revenue available after growth, and the resulting gap by
          fiscal year, shown both as a running total and as the amount new in each year
        </caption>
        <thead>
          <tr className="text-left" style={{ color: 'var(--text-muted)' }}>
            <th className="font-semibold py-1.5">Year</th>
            <th className="font-semibold py-1.5 text-right">Cost of today&rsquo;s services</th>
            <th className="font-semibold py-1.5 text-right">Revenue available</th>
            {overrideLevy > 0 && (
              <th className="font-semibold py-1.5 text-right">of which, the override</th>
            )}
            <th className="font-semibold py-1.5 text-right">Revenue rose by</th>
            <th className="font-semibold py-1.5 text-right">Gap, running total</th>
            <th className="font-semibold py-1.5 text-right">Grew by</th>
          </tr>
        </thead>
        <tbody>
          <tr className="border-t" style={{ borderColor: 'var(--grid)' }}>
            <td className="rowhead py-1.5 font-semibold">
              FY27 <span className="text-[11px] font-normal"
                style={{ color: 'var(--text-muted)' }}>today</span>
            </td>
            <td data-label="Cost of today&rsquo;s services" className="py-1.5 text-right">
              {usd(N.costFy27)}
            </td>
            <td data-label="Revenue available" className="py-1.5 text-right">
              {usd(N.appropFy27)}
            </td>
            {overrideLevy > 0 && (
              <td data-label="of which, the override" className="py-1.5 text-right"
                style={{ color: 'var(--text-muted)' }}>&mdash;</td>
            )}
            <td data-label="Revenue rose by" className="py-1.5 text-right"
              style={{ color: 'var(--text-muted)' }}>&mdash;</td>
            <td data-label="Gap, running total" className="py-1.5 text-right">
              {usd(N.startingBehind)}
            </td>
            <td data-label="Grew by" className="py-1.5 text-right"
              style={{ color: 'var(--text-muted)' }}>&mdash;</td>
          </tr>
          {years.map((y, i) => (
            <tr key={y.fy} className="border-t" style={{ borderColor: 'var(--grid)' }}>
              <td className="rowhead py-1.5 font-semibold">FY{y.fy}</td>
              <td data-label="Cost of today&rsquo;s services" className="py-1.5 text-right">
                {usd(y.cost)}
              </td>
              <td data-label="Revenue available" className="py-1.5 text-right">
                {usd(y.revenue)}
              </td>
              {overrideLevy > 0 && (
                <td data-label="of which, the override" className="py-1.5 text-right"
                  style={{ color: 'var(--series-cost)' }}>{usd(overrideAt(i))}</td>
              )}
              <td data-label="Revenue rose by" className="py-1.5 text-right"
                style={{ color: 'var(--status-good)' }}>
                +{usd(y.revenue - (i === 0 ? N.appropFy27 : years[i - 1].revenue))}
              </td>
              <td data-label="Gap, running total" className="py-1.5 text-right font-semibold"
                style={{ color: y.gap > 0 ? 'var(--status-critical)' : 'var(--status-good)' }}>
                {y.gap > 0 ? usd(y.gap) : `funded, ${usd(-y.gap)} spare`}
              </td>
              <td data-label="Grew by" className="py-1.5 text-right font-bold"
                style={{ color: grew[i] < 0 ? 'var(--status-good)' : undefined }}>
                {usd(grew[i])}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="text-[13px] leading-relaxed mt-3 pt-3 border-t"
        style={{ borderColor: 'var(--grid)' }}>
        {footer({ years, grew, avg })}
      </div>
    </div>
  )
}
