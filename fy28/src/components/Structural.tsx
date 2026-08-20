import { useMemo } from 'react'
import { MODEL, project, usd, usdShort, type Assumptions } from '../model/engine'

const A = MODEL.assumptions
const T = MODEL.taxBase
const LEVY_CAP = 0.025

const BUCKETS: { key: keyof Assumptions; label: string; note: string }[] = [
  { key: 'salaries', label: 'Salaries', note: 'Collectively bargained' },
  { key: 'health', label: 'Health insurance', note: 'Set by the insurance market' },
  { key: 'transport', label: 'Transportation', note: 'Contracted, fuel-exposed' },
  { key: 'sped_tuition', label: 'Out-of-district SPED', note: 'Set by law and by placement' },
  { key: 'utilities', label: 'Utilities', note: 'Market' },
  { key: 'other', label: 'Everything else', note: 'The only genuinely discretionary part' },
]

/** Why the gap reopens every year, and what it would actually take to stop it.
 *
 *  Every other part of this tool answers "what do we do about FY28". This one answers the
 *  question underneath it: why is there an FY28 problem at all, and why did closing FY27
 *  not fix it. The answer is two growth rates, and it is the single most important fact
 *  in the whole projection. */
export function Structural() {
  const base = useMemo(() => project(15, A), [])
  const expense = MODEL.expenseBase as Record<string, number>
  const total = Object.values(expense).reduce((s, v) => s + v, 0)
  const blended = BUCKETS.reduce(
    (s, b) => s + (expense[b.key] / total) * (A[b.key] as number), 0)
  const maxRate = Math.max(...BUCKETS.map(b => A[b.key] as number))

  /** Years fully covered by ONE override — a permanent lift that then grows with the
   *  appropriation, which is what a single ballot question actually buys. */
  const singleOverride = (x: number) => {
    let lift = x
    for (let i = 0; i < base.length; i++) {
      if (base[i].deficit - lift > 0) return i
      lift *= 1 + base[i].growthRate
    }
    return base.length
  }
  /** Years fully covered by building at a sustained rate, forever. */
  const sustained = (value: number) => {
    const d = project(15, { ...A, new_growth: (value * T.rate) / 1000 })
    const i = d.findIndex(y => y.deficit > 0)
    return i === -1 ? 15 : i
  }
  const mix = T.archetypes.find(a => a.id === 'mix')?.value ?? 3_005_000
  const bentHealth = project(10, { ...A, health: 0.04 })

  return (
    <div>
      {/* ---- the two rates ---- */}
      <div className="grid gap-3 sm:grid-cols-3 mb-8">
        <div className="card p-5">
          <p className="text-[11px] font-semibold uppercase tracking-widest mb-1"
            style={{ color: 'var(--text-muted)' }}>School costs rise</p>
          <p className="text-4xl font-bold tnum leading-none"
            style={{ color: 'var(--status-critical)' }}>{(blended * 100).toFixed(2)}%</p>
          <p className="text-[12px] mt-2" style={{ color: 'var(--text-secondary)' }}>
            a year, blended across everything the district buys
          </p>
        </div>
        <div className="card p-5">
          <p className="text-[11px] font-semibold uppercase tracking-widest mb-1"
            style={{ color: 'var(--text-muted)' }}>Revenue may rise</p>
          <p className="text-4xl font-bold tnum leading-none">2.50%</p>
          <p className="text-[12px] mt-2" style={{ color: 'var(--text-secondary)' }}>
            a year, by Proposition 2&frac12;, plus whatever is newly built
          </p>
        </div>
        <div className="card p-5" style={{ background: 'var(--surface-3)' }}>
          <p className="text-[11px] font-semibold uppercase tracking-widest mb-1"
            style={{ color: 'var(--text-muted)' }}>Which leaves</p>
          <p className="text-4xl font-bold tnum leading-none"
            style={{ color: 'var(--status-critical)' }}>
            {((blended - LEVY_CAP) * 100).toFixed(2)}
            <span className="text-lg font-normal"> pts</span>
          </p>
          <p className="text-[12px] mt-2" style={{ color: 'var(--text-secondary)' }}>
            short every year, compounding. Nobody overspent — these are simply two
            different numbers.
          </p>
        </div>
      </div>

      {/* ---- where the 4.94% comes from ---- */}
      <h3 className="text-sm font-bold mb-1">Where the {(blended * 100).toFixed(2)}% comes from</h3>
      <p className="text-[13px] mb-4 max-w-3xl" style={{ color: 'var(--text-secondary)' }}>
        The bar is each item&rsquo;s growth rate; the number beside it is how much of the
        budget it is. The dotted line is the 2&frac12;% the town&rsquo;s revenue is allowed
        to grow. Only one line on this list sits under it, and it is the smallest.
      </p>
      <ul className="space-y-2 mb-8">
        {BUCKETS.map(b => {
          const rate = A[b.key] as number
          const shareOf = expense[b.key] / total
          return (
            <li key={b.key} className="flex items-center gap-3">
              <span className="w-40 sm:w-52 shrink-0 text-[13px]">
                {b.label}
                <span className="block text-[10px]" style={{ color: 'var(--text-muted)' }}>
                  {b.note}
                </span>
              </span>
              <span className="flex-1 relative h-5 rounded"
                style={{ background: 'var(--surface-3)' }}>
                <span className="absolute inset-y-0 left-0 rounded"
                  style={{ width: `${(rate / maxRate) * 100}%`,
                           background: rate > LEVY_CAP ? 'var(--status-critical)'
                             : 'var(--status-good)' }} />
                <span className="absolute inset-y-0 border-l-2 border-dashed"
                  style={{ left: `${(LEVY_CAP / maxRate) * 100}%`,
                           borderColor: 'var(--text-primary)' }} aria-hidden="true" />
              </span>
              <span className="w-24 shrink-0 text-right text-[13px] tnum">
                {(rate * 100).toFixed(0)}%
                <span className="block text-[10px]" style={{ color: 'var(--text-muted)' }}>
                  {(shareOf * 100).toFixed(0)}% of budget
                </span>
              </span>
            </li>
          )
        })}
      </ul>

      {/* ---- what it compounds to ---- */}
      <h3 className="text-sm font-bold mb-1">What 2.44 points a year turns into</h3>
      <p className="text-[13px] mb-3 max-w-3xl" style={{ color: 'var(--text-secondary)' }}>
        This is why closing one year&rsquo;s gap does not fix anything: the shortfall is not
        a one-off, it is a rate, and rates compound.
      </p>
      <div className="flex flex-wrap gap-2 mb-8">
        {[0, 2, 4, 6, 9].map(i => (
          <div key={i} className="card px-4 py-3 flex-1 min-w-[7rem]">
            <p className="text-[11px] font-semibold uppercase tracking-widest"
              style={{ color: 'var(--text-muted)' }}>FY{base[i].fy}</p>
            <p className="text-xl font-bold tnum leading-none mt-1"
              style={{ color: 'var(--status-critical)' }}>
              {usdShort(base[i].deficit)}
            </p>
          </div>
        ))}
      </div>

      {/* ---- the three ways out ---- */}
      <h3 className="text-sm font-bold mb-1">The three ways out, honestly sized</h3>
      <p className="text-[13px] mb-4 max-w-3xl" style={{ color: 'var(--text-secondary)' }}>
        A gap that grows needs a remedy that grows. Anything that arrives once gets
        overtaken &mdash; the only question is how long that takes.
      </p>
      <div className="grid gap-3 md:grid-cols-3">
        <Way title="Pass an override"
          lead={`${singleOverride(613_238)} year`}
          sub={`what one ${usd(613_238)} override buys`}
          body={<>An override permanently raises the levy limit, and that lift then grows
            2&frac12;% a year &mdash; slower than the gap. So one ballot question is not a
            fix, it is a postponement, and the next one has to be bigger.</>}
          rows={[[`${usd(613_238)} once`, `${singleOverride(613_238)} year`],
                 [`${usd(3_000_000)} once`, `${singleOverride(3_000_000)} years`],
                 [`${usd(5_000_000)} once`, `${singleOverride(5_000_000)} years`]]} />

        <Way title="Build commercial"
          lead={`${sustained(150e6)}+ years`}
          sub="at $150M of new value a year, sustained"
          body={<>It genuinely works &mdash; at a scale that would remake the town. $150M a
            year is <strong>97% of Lunenburg&rsquo;s entire existing commercial base, added
            every year</strong>. After a decade the commercial base would be 10.7&times;
            what it is now.</>}
          rows={[[`${usdShort(106.9e6)}/yr · ${Math.round(106.9e6 / mix)} builds`, `${sustained(106.9e6)} years`],
                 [`${usdShort(130e6)}/yr · ${Math.round(130e6 / mix)} builds`, `${sustained(130e6)} years`],
                 [`${usdShort(150e6)}/yr · ${Math.round(150e6 / mix)} builds`, `${sustained(150e6)}+ years`]]} />

        <Way title="Bend the cost curve"
          lead={usdShort(base[9].deficit - bentHealth[9].deficit)}
          sub="off the FY37 gap, from health insurance alone"
          body={<>The one remedy that is neither a tax nor a cut: change the growth rates
            themselves. Health insurance is 15% of the budget growing at 9%. Holding it to
            4% takes the FY37 gap from {usdShort(base[9].deficit)} to{' '}
            {usdShort(bentHealth[9].deficit)} &mdash; it does not close it, but it nearly
            halves it, and it makes everything else smaller.</>}
          rows={[['Health at 6%', usdShort(project(10, { ...A, health: 0.06 })[9].deficit)],
                 ['Health at 4%', usdShort(bentHealth[9].deficit)],
                 ['Unchanged, 9%', usdShort(base[9].deficit)]]} />
      </div>

      <div className="card p-5 mt-4" style={{ background: 'var(--surface-3)' }}>
        <p className="text-[13px] leading-relaxed">
          <strong>Put together:</strong> holding health to 4%, building at{' '}
          {usdShort(106.9e6)} a year, and passing {usd(613_238)} of override covers the
          whole fifteen years. Any one of them alone does not. That is the honest shape of
          the problem &mdash; not a single decision anybody can take at a Town Meeting, but
          three sustained ones, and the cuts on the other pages are what happens in the
          years before they arrive.
        </p>
      </div>
    </div>
  )
}

function Way({ title, lead, sub, body, rows }: {
  title: string; lead: string; sub: string
  body: React.ReactNode; rows: [string, string][]
}) {
  return (
    <div className="card p-5 flex flex-col">
      <h4 className="text-[13px] font-bold mb-2">{title}</h4>
      <p className="text-3xl font-bold tnum leading-none"
        style={{ color: 'var(--series-cost)' }}>{lead}</p>
      <p className="text-[11px] mt-1 mb-3" style={{ color: 'var(--text-muted)' }}>{sub}</p>
      <p className="text-[12px] leading-relaxed flex-1"
        style={{ color: 'var(--text-secondary)' }}>{body}</p>
      <dl className="mt-3 pt-3 border-t space-y-1.5" style={{ borderColor: 'var(--grid)' }}>
        {rows.map(([k, v]) => (
          <div key={k} className="flex items-baseline justify-between gap-3 text-[12px]">
            <dt style={{ color: 'var(--text-secondary)' }}>{k}</dt>
            <dd className="font-bold tnum shrink-0">{v}</dd>
          </div>
        ))}
      </dl>
    </div>
  )
}
