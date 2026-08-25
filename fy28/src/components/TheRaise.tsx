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
        <Fact label="The increase for next year" value={usdShort(N.allowed)}
          sub={`The town gave the schools ${usd(N.appropFy27)} this year. Town revenue rises `
            + `${pct(N.growthRate, 2)}, so next year it can give ${usd(N.allowed)} more than `
            + `it did. That is the entire increase.`} />
        <Fact label="What standing still costs" value={usdShort(N.costTotal)} tone="critical"
          sub={`What the same staff, the same buses and the same buildings cost next year, `
            + `one year older. Nobody is hired and nothing is added.`} />
        <Fact label="The shortfall" value={usdShort(N.leftOver)} tone="critical"
          sub={`Standing still costs ${pct(N.consumed)} of the increase. The rest has to be `
            + `cut from somewhere, charged to somebody, or voted for.`} />
      </div>

      {/* ---- the bar ---- */}
      <div className="card p-4">
        <h3 className="text-[15px] font-bold">
          What the increase has to cover
        </h3>
        <p className="text-[12px] mt-1 mb-4" style={{ color: 'var(--text-secondary)' }}>
          The full width is what next year costs if nothing changes. The mark is how far
          the money goes. Everything past the mark has to come from somewhere else, and no
          rearranging of the segments makes it fit.
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
            <span style={{ color: 'var(--text-muted)' }}>where the money runs out</span>
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

/** Who is living within the increase and who is not.
 *
 *  The bar above answers "is there enough" — no — but it cannot say whose fault that is,
 *  because a big line naturally takes a big share and looks guilty for being big. This
 *  asks the fair version instead: split the increase in proportion to what each line
 *  already costs, and see who still comes up short.
 *
 *  It changes the ranking completely, and it produces the fact this whole page has been
 *  circling. Everything else — supplies, materials, technology, athletics, clubs, the one
 *  line the School Committee genuinely controls and the only one it has actually been
 *  cutting — is the sole line in the budget that lives inside its means. Health insurance
 *  takes three times its share. The town has been cutting the one thing that was not the
 *  problem. */
function WithinShare() {
  const rows = N.costs.slice().sort((a, b) => b.overdraft - a.overdraft)
  const max = Math.max(...rows.map(r => Math.abs(r.overdraft)))
  const width = (r: typeof rows[number]) =>
    `${Math.max((Math.abs(r.overdraft) / max) * 100, 1.5)}%`

  return (
    <div className="card p-4 mt-4">
      <h3 className="text-[15px] font-bold">Which lines live within the increase</h3>
      <p className="text-[12px] mt-1 mb-4" style={{ color: 'var(--text-secondary)' }}>
        The bar above shows that the money runs out, but a large line takes a large share
        of any increase and looks guilty simply for being large. So split the{' '}
        {usdShort(N.allowed)} in proportion to what each line <em>already</em> costs
        &mdash; the fairest division there is &mdash; and ask who still comes up short.
      </p>

      <ul className="space-y-1.5">
        {rows.map(r => (
          <li key={r.key} className="flex items-center gap-2">
            <span className="text-[11px] sm:text-[12px] w-[34%] sm:w-[28%] shrink-0 truncate"
              title={r.label}>{r.label}</span>
            <span className="flex-1 flex items-stretch h-5">
              <span className="w-1/2 flex justify-end">
                {r.fits && (
                  <span className="rounded-l" aria-hidden="true"
                    style={{ width: width(r), background: 'var(--status-good)' }} />
                )}
              </span>
              <span aria-hidden="true" style={{ width: 1, background: 'var(--axis)' }} />
              <span className="w-1/2">
                {!r.fits && (
                  <span className="block h-full rounded-r" aria-hidden="true"
                    style={{ width: width(r), background: 'var(--status-critical)' }} />
                )}
              </span>
            </span>
            <span className="text-[11px] sm:text-[12px] tnum w-[30%] sm:w-[26%] text-right
                             shrink-0 font-semibold"
              style={{ color: r.fits ? 'var(--status-good)' : 'var(--status-critical)' }}>
              {r.fits
                ? `fits, by ${usd(-r.overdraft)}`
                : `+${usd(r.overdraft)}`}
              {!r.fits && (
                <span className="block text-[10px] font-normal"
                  style={{ color: 'var(--text-muted)' }}>
                  {r.multiple.toFixed(2)}&times; its share
                </span>
              )}
            </span>
          </li>
        ))}
      </ul>

      <div className="flex justify-between text-[10px] mt-1 px-[34%] sm:px-[28%]"
        style={{ color: 'var(--text-muted)' }}>
        <span>lives within its share</span>
        <span>takes more than its share</span>
      </div>

      <p className="text-[13px] leading-relaxed mt-4 pt-3 border-t"
        style={{ borderColor: 'var(--grid)' }}>
        <strong>One line out of six fits, and it fits by {usd(-rows[rows.length - 1].overdraft)}.</strong>{' '}
        It is &ldquo;everything else&rdquo; &mdash; supplies, materials, technology,
        athletics, clubs &mdash; the only line the School Committee fully controls, and
        the only one it has actually been cutting. Health insurance takes{' '}
        {rows[0].multiple.toFixed(2)} times its share and accounts for{' '}
        {Math.round((rows[0].overdraft / -N.leftOver) * 100)}% of the whole shortfall on
        its own. The overdrafts add up to {usd(-N.leftOver)}, which is next year&rsquo;s
        problem exactly.
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
