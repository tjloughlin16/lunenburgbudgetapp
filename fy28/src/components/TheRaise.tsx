import { usd, usdShort } from '../model/engine'
import { nextYear, RATE_LINES, type Bucket } from '../model/rates'

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
        <Fact label={`What FY${N.fy} adds`} value={usdShort(N.allowed)}
          sub={`${pct(N.growthRate, 2)} more than the ${usdShort(N.appropFy27)} appropriated this year — every extra dollar the schools have`} />
        <Fact label="What the six lines want" value={usdShort(N.costTotal)} tone="critical"
          sub="To buy exactly what the district buys today, for the same children" />
        <Fact label="Left to spend" value={usdShort(N.leftOver)} tone="critical"
          sub={`The lines consume ${pct(N.consumed)} of the raise. Nothing is added, nothing improves, and it is still short.`} />
      </div>

      {/* ---- the bar ---- */}
      <div className="card p-4">
        <h3 className="text-[15px] font-bold">
          What next year&rsquo;s raise has to cover
        </h3>
        <p className="text-[12px] mt-1 mb-4" style={{ color: 'var(--text-secondary)' }}>
          The full width is what the six lines want. The mark is everything the town is
          able to give. There is no version of this bar where the segments are rearranged
          into something that fits.
        </p>

        <div className="relative">
          <div className="flex h-10 rounded-lg overflow-hidden"
            style={{ background: 'var(--surface-3)' }}>
            {N.costs.map(c => (
              <div key={c.key} style={{ width: scale(c.amount), background: COLOR[c.key] }}
                title={`${c.label} +${usd(c.amount)}`} />
            ))}
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
            <span style={{ color: 'var(--text-muted)' }}>all the town can give</span>
          </span>
          <span className="absolute right-0 text-right leading-tight"
            style={{ color: 'var(--status-critical)' }}>
            <strong>{usdShort(-N.leftOver)} over</strong><br />
            <span style={{ color: 'var(--text-muted)' }}>cut, charge, or vote for it</span>
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
              <th className="font-semibold py-1.5 text-right">Of the raise</th>
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
                  <td data-label="Of the raise" className="py-1.5 text-right font-semibold">
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
          raise</strong> while being{' '}
          {pct(RATE_LINES.find(l => l.key === N.costs[1].key)!.weight, 0)} of the budget.
          Salaries take{' '}
          {pct(N.costs[0].shareOfAllowed)} on their own. By the third line the raise is
          gone, and there are three more lines. Nothing in this table is new spending
          &mdash; it is the same staff, the same buses and the same buildings, a year older.
        </p>
      </div>

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
              ['Less the raise', -N.allowed],
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
