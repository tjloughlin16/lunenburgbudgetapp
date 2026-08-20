import { useMemo } from 'react'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ReferenceArea,
  ResponsiveContainer,
} from 'recharts'
import {
  MODEL, project, runCascade, usd, usdShort, type Assumptions,
} from '../model/engine'

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

  // Cutting does not slow the gap — it converts a compounding number into a recurring
  // one, and spends the program catalog doing it. The cascade uses the School
  // Committee's own revealed ranking; a different ranking changes what is lost, not the
  // arithmetic.
  const casc = useMemo(
    () => runCascade(MODEL.presets.school_committee.order, A, 10), [])
  const trajectory = base.slice(0, 10).map((y, i) => ({
    fy: y.fy,
    nothingCut: y.deficit,
    afterCuts: casc[i].deficit,
    unclosed: casc[i].unclosed,
  }))
  const exhausted = casc.find(y => y.unclosed > 0)
  const cutting = casc.filter(y => y.cutTotal > 0)
  const recurring = cutting.reduce((s2, y) => s2 + y.deficit, 0) / cutting.length
  const cumCut = casc.reduce((s2, y) => s2 + y.cutTotal, 0)
  const cumFte = casc[casc.length - 1].cumFte

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

      {/* ---- what it compounds to, and what cutting does to that ---- */}
      <h3 className="text-sm font-bold mb-1">What 2.44 points a year turns into</h3>
      <p className="text-[13px] mb-4 max-w-3xl" style={{ color: 'var(--text-secondary)' }}>
        Two different futures, and the difference matters more than either number. Leave
        everything funded and the shortfall compounds to {usdShort(base[9].deficit)} by
        FY{base[9].fy}. Close each year by cutting and it does <em>not</em> compound
        &mdash; because every cut permanently lowers the base the next year grows from.
        What you get instead is a gap that lands again every single year, at roughly{' '}
        {usdShort(recurring)}, forever.
      </p>
      <Compounding rows={trajectory} exhausted={exhausted} />
      <div className="grid gap-3 sm:grid-cols-3 mt-4 mb-8">
        <div className="card p-4">
          <p className="text-[11px] font-semibold uppercase tracking-widest mb-1"
            style={{ color: 'var(--text-muted)' }}>The gap you actually face</p>
          <p className="text-2xl font-bold tnum leading-none"
            style={{ color: 'var(--status-critical)' }}>{usdShort(recurring)}</p>
          <p className="text-[12px] mt-1.5" style={{ color: 'var(--text-secondary)' }}>
            of <strong>fresh</strong> cuts a year once you are cutting — not a growing
            number, a repeating one
          </p>
        </div>
        <div className="card p-4">
          <p className="text-[11px] font-semibold uppercase tracking-widest mb-1"
            style={{ color: 'var(--text-muted)' }}>What that costs by FY{exhausted?.fy ?? 33}</p>
          <p className="text-2xl font-bold tnum leading-none"
            style={{ color: 'var(--status-critical)' }}>{cumFte} FTE</p>
          <p className="text-[12px] mt-1.5" style={{ color: 'var(--text-secondary)' }}>
            and {usd(cumCut)} of programs — the damage compounds even though the gap does
            not
          </p>
        </div>
        <div className="card p-4" style={{ background: 'var(--surface-3)' }}>
          <p className="text-[11px] font-semibold uppercase tracking-widest mb-1"
            style={{ color: 'var(--text-muted)' }}>Then the list runs out</p>
          <p className="text-2xl font-bold tnum leading-none"
            style={{ color: 'var(--status-critical)' }}>FY{exhausted?.fy ?? 33}</p>
          <p className="text-[12px] mt-1.5" style={{ color: 'var(--text-secondary)' }}>
            every discretionary program in the model is gone, and the gap starts
            compounding for real &mdash; {usdShort(base[9].deficit - cumCut)} unclosed by
            FY{base[9].fy}
          </p>
        </div>
      </div>

      {/* ---- how to read the number, because it is easy to read it wrong ---- */}
      <div className="card p-5 mb-8">
        <h3 className="text-sm font-bold mb-2">
          How to read &ldquo;{usdShort(base[9].deficit)} by FY{base[9].fy}&rdquo;
        </h3>
        <div className="grid gap-4 md:grid-cols-3 text-[13px] leading-relaxed"
          style={{ color: 'var(--text-secondary)' }}>
          <div>
            <p className="text-[11px] font-bold uppercase tracking-widest mb-1"
              style={{ color: 'var(--text-muted)' }}>It is an annual figure</p>
            <p>
              Not a running total. In FY{base[9].fy} alone, running FY27&rsquo;s services
              would cost {usd(base[9].levelService)} against {usd(base[9].available)} of
              revenue. The next year it starts again, larger.
            </p>
          </div>
          <div>
            <p className="text-[11px] font-bold uppercase tracking-widest mb-1"
              style={{ color: 'var(--text-muted)' }}>It is in future dollars</p>
            <p>
              {usdShort(base[9].deficit)} of FY{base[9].fy} money, ten fiscal years out.
              In today&rsquo;s purchasing power that is roughly{' '}
              <strong>{usd(Math.round(base[9].deficit / Math.pow(1 + LEVY_CAP, 10)))}</strong>{' '}
              &mdash; still enormous, but not as enormous as it looks.
            </p>
          </div>
          <div>
            <p className="text-[11px] font-bold uppercase tracking-widest mb-1"
              style={{ color: 'var(--status-critical)' }}>Nobody will ever see it</p>
            <p>
              Massachusetts budgets must balance, so this shortfall never appears on a
              statement. It is not a prediction of a deficit &mdash; it is{' '}
              <strong>the annual price, in FY{base[9].fy}, of still having what the
              district has today</strong>.
            </p>
          </div>
        </div>
        <p className="text-[13px] leading-relaxed mt-4 pt-4 border-t"
          style={{ borderColor: 'var(--grid)' }}>
          <strong>What you would actually see in FY{base[9].fy}</strong> is that figure
          paid in two currencies instead of one: about <strong>{usd(cumCut)}</strong> of
          programs and {cumFte} staff positions already gone, so the district is no longer
          buying them &mdash; plus roughly <strong>{usdShort(casc[9].unclosed)}</strong>{' '}
          still unfunded in that year, with nothing left on the list to cut. The two do not
          add exactly to {usdShort(base[9].deficit)}, because a cut made early also stops
          inflating; cutting sooner is worth more than cutting later.
        </p>
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
          three sustained ones. Cutting is not a fourth option so much as what happens
          while none of them is chosen: it holds the line for about{' '}
          {cutting.length} years, at {cumFte} staff positions and {usd(cumCut)} of
          programs, and then there is nothing left to cut and the arithmetic resumes.
        </p>
      </div>
    </div>
  )
}

/** The two trajectories, and the point where one of them stops being available. */
function Compounding({ rows, exhausted }: {
  rows: { fy: number; nothingCut: number; afterCuts: number; unclosed: number }[]
  exhausted?: { fy: number }
}) {
  return (
    <div>
      <div style={{ width: '100%', height: 280 }}>
        <ResponsiveContainer>
          <LineChart data={rows} margin={{ top: 8, right: 12, bottom: 4, left: 4 }}>
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            {exhausted && (
              <ReferenceArea x1={exhausted.fy} x2={rows[rows.length - 1].fy}
                fill="var(--status-critical)" fillOpacity={0.07} />
            )}
            <XAxis dataKey="fy" tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
              stroke="var(--axis)" tickLine={false} tickFormatter={v => `FY${v}`} />
            <YAxis width={56} tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
              stroke="var(--axis)" tickLine={false} axisLine={false}
              tickFormatter={v => usdShort(v as number)} />
            <Tooltip
              contentStyle={{ background: 'var(--surface-1)', border: '1px solid var(--grid)',
                              borderRadius: 10, fontSize: 12, color: 'var(--text-primary)' }}
              labelFormatter={v => `FY${v}`}
              formatter={(v, n) => [usd(v as number),
                n === 'nothingCut' ? 'If nothing is cut' : 'Fresh gap after cutting']} />
            <Legend verticalAlign="top" height={28} iconType="plainline"
              wrapperStyle={{ fontSize: 12, color: 'var(--text-secondary)' }}
              formatter={v => v === 'nothingCut'
                ? 'If nothing is cut' : 'Fresh gap each year, after cutting'} />
            <Line type="monotone" dataKey="nothingCut" stroke="var(--status-critical)"
              strokeWidth={2} dot={false} isAnimationActive={false} />
            <Line type="monotone" dataKey="afterCuts" stroke="var(--series-cost)"
              strokeWidth={2} dot={false} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      {exhausted && (
        <p className="text-[11px] mt-1" style={{ color: 'var(--text-muted)' }}>
          The shaded years are after the model has run out of programs to cut. The blue
          line rejoins the red one because there is nothing left to hold it down &mdash;
          cutting bought time, not a solution. Which programs go, and in what order, comes
          from the School Committee&rsquo;s own revealed ranking; a different ranking
          changes what is lost, not the arithmetic.
        </p>
      )}
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
