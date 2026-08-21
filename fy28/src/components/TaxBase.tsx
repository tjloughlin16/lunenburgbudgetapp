import { useState } from 'react'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, ReferenceDot,
} from 'recharts'
import { MODEL, usd, usdShort } from '../model/engine'
import { GrowthReality } from './CommercialTrend'
import { TaxpayerView } from './TaxpayerView'

const T = MODEL.taxBase

/** How the tax base is actually split, and why rising home values don't help. */
export function TaxStructure() {
  const res = T.totalValue * T.residentialShare
  const cip = T.totalValue * T.cipShare
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <div className="card p-5">
        <h3 className="text-sm font-bold mb-4">Who owns the tax base</h3>
        <p className="text-3xl font-bold tnum leading-none mb-1">{usdShort(T.totalValue)}</p>
        <p className="text-[12px] mb-5" style={{ color: 'var(--text-secondary)' }}>
          Total taxable value, FY26 — derived from the {usd(T.levy)} levy at{' '}
          ${T.rate.toFixed(2)} per $1,000.
        </p>

        {[['Homes and residential land', res, T.residentialShare, 'var(--series-cost)'],
          ['Commercial, industrial & personal property', cip, T.cipShare, 'var(--series-revenue)'],
        ].map(([label, val, share, color]) => (
          <div key={label as string} className="mb-4">
            <div className="flex items-baseline justify-between gap-3 mb-1">
              <span className="text-[13px] font-medium">{label as string}</span>
              <span className="text-sm font-bold tnum shrink-0">
                {usdShort(val as number)}{' '}
                <span className="font-normal" style={{ color: 'var(--text-muted)' }}>
                  {(((share as number) * 100)).toFixed(0)}%
                </span>
              </span>
            </div>
            <div className="h-3 rounded-full overflow-hidden" style={{ background: 'var(--surface-3)' }}>
              <div className="h-full rounded-full"
                style={{ width: `${(share as number) * 100}%`, background: color as string }} />
            </div>
          </div>
        ))}

        <p className="text-[12px] leading-relaxed mt-4 pt-3 border-t"
          style={{ borderColor: 'var(--grid)', color: 'var(--text-secondary)' }}>
          Lunenburg uses a <strong>single tax rate</strong> — a house and a warehouse of the
          same assessed value pay exactly the same. The Select Board considered a split rate
          for FY26 and declined it: residential would have fallen to{' '}
          ${T.splitRate.residential.toFixed(2)} and commercial risen to{' '}
          ${T.splitRate.commercial.toFixed(2)}, adding about{' '}
          {usd(T.splitRate.avgCommercialIncrease)} to the average commercial bill. Their
          stated reasoning was to build the commercial base first.
        </p>
      </div>

      <div className="card p-5">
        <h3 className="text-sm font-bold mb-3">The thing almost nobody knows</h3>
        <p className="text-[14px] leading-relaxed mb-4">
          <strong>When your home value goes up, the town does not get more money.</strong>
        </p>
        <ul className="space-y-3 text-[13px] leading-relaxed"
          style={{ color: 'var(--text-secondary)' }}>
          <li>
            Proposition 2½ caps the <em>total</em> the town may collect — the levy limit —
            at last year&rsquo;s limit plus 2.5%, plus new growth. It does not cap your
            individual bill.
          </li>
          <li>
            So if every assessment in town rose 10% tomorrow, the levy limit would not
            move. The Assessors would simply <strong>lower the rate</strong> until the levy
            fell back under the cap. The town collects the same money either way.
          </li>
          <li>
            The Town&rsquo;s own analysis says exactly this: assessed value has been rising
            faster than the levy since 2017, meaning{' '}
            <em>&ldquo;less available revenue during more growth.&rdquo;</em>
          </li>
          <li>
            <strong>New growth is different.</strong> Genuinely new construction is added
            to the levy limit on top of the 2.5% — permanently. It is the only way the town
            raises more money without an override.
          </li>
        </ul>
        <p className="text-[13px] leading-relaxed mt-4 pt-3 border-t font-medium"
          style={{ borderColor: 'var(--grid)' }}>
          That is why &ldquo;we need more business&rdquo; and &ldquo;we need an
          override&rdquo; are answers to the same question — and why one of them takes
          years to work.
        </p>
      </div>
    </div>
  )
}

/** How much commercial development would it actually take? */
export function GrowthCalculator({ gap, newValue, setNewValue, share = 1,
  compact = false }: {
  gap: number; newValue: number; setNewValue: (n: number) => void
  /** On the adjustments page this is a dial with an explanation. The ten-year chart and
   *  the how-new-growth-works essay belong on the development page, not in a panel
   *  beside the athletics fee. */
  compact?: boolean
  /** Fraction of new-growth revenue that reaches the SCHOOL gap. New growth lifts the
   *  town's levy limit; the schools get their share of the town's revenue, not all of
   *  it. Treating it as a dollar for a dollar roughly doubles what development appears
   *  to be worth. */
  share?: number
}) {
  const [archetype, setArchetype] = useState('mix')
  const arch = T.archetypes.find(a => a.id === archetype)!

  const annual = (newValue * T.rate) / 1000
  // The projection ALREADY assumes the town's current new growth. Only the part above
  // that baseline is new money against the gap — comparing gross new-growth revenue to
  // the gap counts the same $400,000 twice.
  const baseline = T.currentNewGrowthRevenue
  const extra = annual - baseline
  // What actually lands on the school side of the ledger.
  const toSchools = extra * share
  const buildings = newValue / arch.value
  // Buildings and businesses are not the same count, and conflating them is how "we just
  // need a few more developments" becomes convincing. A development is a structure; the
  // town's average commercial PARCEL is worth $658,001, and a single plaza holds several.
  // The parcel figure is the one number here that is not our estimate — it comes off the
  // tax rolls.
  const businesses = newValue / T.avgCommercialValue
  const shareOfBase = (newValue / T.totalValue) * 100
  // Value needed ON TOP of today's new growth, grossed up for the town's share.
  const valueForGap = ((gap / share) * 1000) / T.rate
  const businessesForGap = valueForGap / T.avgCommercialValue
  // Where the slider has to reach for growth alone to close the gap: today's new growth
  // plus the extra the gap needs. The slider used to stop at a hardcoded $60M, below
  // this figure — so the one thing this control exists to show could not be reached.
  const closesAt = T.currentNewGrowthValue + valueForGap
  const sliderMax = Math.ceil((closesAt * 1.1) / 10_000_000) * 10_000_000

  // Ten years: extra new growth compounding vs a one-off override of the same gap.
  const data: { year: number; growth: number; override: number }[] = []
  let g = 0
  for (let i = 0; i < 10; i++) {
    g = g * (1 + T.levyGrowth) + annual * share
    data.push({ year: i + 1, growth: Math.round(g),
                override: Math.round(gap * Math.pow(1 + T.levyGrowth, i)) })
  }
  const cross = data.find(d => d.growth >= d.override)

  return (
    <div>
      <div className="card p-5 mb-4">
        <div className="grid gap-5 md:grid-cols-2">
          <div>
            <div className="flex items-baseline justify-between mb-1">
              <label htmlFor="newval" className="text-[13px] font-medium">
                New commercial value added per year
              </label>
              <span className="flex items-baseline gap-2">
                <span className="text-xl font-bold tnum">{usdShort(newValue)}</span>
                {newValue !== T.currentNewGrowthValue && (
                  <button onClick={() => setNewValue(T.currentNewGrowthValue)}
                    className="text-[10px] font-semibold underline"
                    style={{ color: 'var(--text-secondary)' }}>
                    reset
                  </button>
                )}
              </span>
            </div>
            <p className="text-[10px] mb-1" style={{ color: 'var(--text-muted)' }}>
              Today: <strong>{usdShort(T.currentNewGrowthValue)}</strong> a year, worth{' '}
              {usd(T.currentNewGrowthRevenue)} — already assumed in the projection. New
              growth lifts the <em>town&rsquo;s</em> levy limit, and the schools get their
              share of town revenue, so only about{' '}
              <strong>{(share * 100).toFixed(0)}&cent; of each dollar</strong> reaches this
              gap. Growth alone closes it at{' '}
              <strong>{usdShort(closesAt)} a year, every year</strong> &mdash;{' '}
              {(closesAt / T.currentNewGrowthValue).toFixed(1)}× what the town has been
              managing.
            </p>
            <input id="newval" type="range" min={0} max={sliderMax} step={1_000_000}
              value={Math.min(newValue, sliderMax)}
              onChange={e => setNewValue(Number(e.target.value))}
              className="w-full" />
            <div className="relative h-8 mb-2">
              <span className="absolute left-0 top-0 text-[10px] leading-tight"
                style={{ color: 'var(--text-muted)' }}>
                <span className="block w-px h-1.5 mb-0.5" style={{ background: 'var(--axis)' }}
                  aria-hidden="true" />
                none
              </span>
              {/* The only mark on this slider that means anything: where growth alone
                  closes the gap. */}
              <button onClick={() => setNewValue(Math.round(closesAt / 1e6) * 1e6)}
                className="absolute top-0 text-[10px] leading-tight text-center hover:opacity-70"
                style={{ left: `${(closesAt / sliderMax) * 100}%`,
                         transform: 'translateX(-50%)', color: 'var(--status-good)' }}>
                <span className="block w-px h-1.5 mb-0.5 mx-auto"
                  style={{ background: 'var(--status-good)' }} aria-hidden="true" />
                <span className="whitespace-nowrap font-semibold">
                  {usdShort(closesAt)} closes it
                </span>
              </button>
              <span className="absolute right-0 top-0 text-[10px] leading-tight text-right"
                style={{ color: 'var(--text-muted)' }}>
                <span className="block w-px h-1.5 mb-0.5 ml-auto"
                  style={{ background: 'var(--axis)' }} aria-hidden="true" />
                {usdShort(sliderMax)}
              </span>
            </div>

            <label htmlFor="arch" className="text-[12px] block mb-1"
              style={{ color: 'var(--text-muted)' }}>Measured in</label>
            <select id="arch" value={archetype} onChange={e => setArchetype(e.target.value)}
              className="w-full px-2 py-1.5 rounded-lg border text-[13px] mb-1"
              style={{ borderColor: 'var(--grid)', background: 'var(--surface-2)',
                       color: 'var(--text-primary)' }}>
              <optgroup label="Realistic for Lunenburg">
                {T.archetypes.filter(a => a.plausible).map(a => (
                  <option key={a.id} value={a.id}>{a.name} — {usdShort(a.value)}</option>
                ))}
              </optgroup>
              <optgroup label="For scale only — not realistic here">
                {T.archetypes.filter(a => !a.plausible).map(a => (
                  <option key={a.id} value={a.id}>{a.name} — {usdShort(a.value)}</option>
                ))}
              </optgroup>
            </select>
            {arch.note && (
              <p className="text-[11px] mb-3"
                style={{ color: arch.plausible ? 'var(--text-secondary)' : 'var(--status-serious)' }}>
                {!arch.plausible && <strong>Unlikely: </strong>}{arch.note}
              </p>
            )}

            {/* Everything below is driven by the one control above. */}
            <div className="py-3 mb-3 border-y" style={{ borderColor: 'var(--grid)' }}>
              <div className="flex items-end justify-between gap-4 mb-3">
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-widest mb-0.5"
                    style={{ color: 'var(--text-muted)' }}>
                    Share of the FY28 school gap
                  </p>
                  <p className="text-4xl font-bold tnum leading-none"
                    style={{ color: toSchools >= gap ? 'var(--status-good)'
                      : toSchools >= gap / 2 ? 'var(--status-serious)' : 'var(--status-critical)' }}>
                    {toSchools <= 0 ? '0%' : `${((toSchools / gap) * 100).toFixed(0)}%`}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-[11px] font-semibold uppercase tracking-widest mb-0.5"
                    style={{ color: 'var(--text-muted)' }}>New money every year</p>
                  <p className="text-2xl font-bold tnum leading-none">
                    {usd(Math.max(0, toSchools))}
                  </p>
                  <p className="text-[10px]" style={{ color: 'var(--text-muted)' }}>
                    {usd(annual)} raised, less {usd(baseline)} already assumed
                  </p>
                </div>
              </div>
              <div className="h-2.5 rounded-full overflow-hidden"
                style={{ background: 'var(--surface-3)' }}>
                <div className="h-full rounded-full"
                  style={{ width: `${Math.min(100, Math.max(0, toSchools / gap) * 100)}%`,
                           background: toSchools >= gap ? 'var(--status-good)'
                             : 'var(--series-cost)' }} />
              </div>
              <p className="text-[11px] mt-1.5" style={{ color: 'var(--text-secondary)' }}>
                {toSchools <= 0
                  ? <>The town already adds about {usd(baseline)} a year of new growth, and
                    the projection assumes it. At this level nothing is gained &mdash; and
                    below it, the gap gets <em>worse</em>.</>
                  : toSchools >= gap
                    ? <>Covers the whole {usd(gap)} gap in year one, on top of the growth
                      already assumed.</>
                    : <>Leaves <strong>{usd(gap - toSchools)}</strong> of the {usd(gap)} gap
                      still to find in year one &mdash; though this compounds and the gap
                      does not grow as fast.</>}
              </p>

              <div className="grid grid-cols-3 gap-3 mt-4 pt-3 border-t"
                style={{ borderColor: 'var(--grid)' }}>
                <div>
                  <p className="text-2xl font-bold tnum leading-none">
                    {buildings.toFixed(buildings < 10 ? 1 : 0)}
                  </p>
                  <p className="text-[11px] font-semibold mt-1">
                    × {arch.name.split('(')[0].trim().toLowerCase()}
                  </p>
                  <p className="text-[10px]" style={{ color: 'var(--text-muted)' }}>
                    buildings, not businesses — {usdShort(arch.value)} each
                  </p>
                </div>
                <div>
                  <p className="text-2xl font-bold tnum leading-none">
                    {businesses.toFixed(businesses < 10 ? 1 : 0)}
                  </p>
                  <p className="text-[11px] font-semibold mt-1">× businesses</p>
                  <p className="text-[10px]" style={{ color: 'var(--text-muted)' }}>
                    at the town&rsquo;s {usdShort(T.avgCommercialValue)} average commercial
                    parcel — from the tax rolls
                  </p>
                </div>
                <div>
                  <p className="text-2xl font-bold tnum leading-none"
                    style={{ color: 'var(--series-cost)' }}>
                    {((newValue / MODEL.taxBase.fy23.cipValue) * 100).toFixed(1)}%
                  </p>
                  <p className="text-[11px] font-semibold mt-1">of the commercial base</p>
                  <p className="text-[10px]" style={{ color: 'var(--text-muted)' }}>
                    added annually, sustained
                  </p>
                </div>
              </div>
            </div>

            <p className="text-[11px]" style={{ color: 'var(--text-muted)' }}>
              <strong>Buildings and businesses are different counts.</strong> One retail
              plaza is a single development but several businesses, so the two figures
              above answer different questions and neither is wrong. The{' '}
              {usdShort(T.avgCommercialValue)} average commercial parcel comes from the tax
              rolls; the building values are our order-of-magnitude estimates rather than
              Lunenburg assessments. They exist so you can think in buildings instead of
              millions.
            </p>
          </div>

          <div className="space-y-2.5">
            <Row k="In buildings" v={`${buildings.toFixed(1)} × ${arch.name.split('(')[0].trim()}`} />
            <Row k="In businesses" v={`${businesses.toFixed(0)} at ${usdShort(T.avgCommercialValue)} each`} />
            <Row k="To close FY28 in one year"
              v={`${(valueForGap / arch.value).toFixed(1)} buildings, or `
                 + `${businessesForGap.toFixed(0)} businesses`} />
            <Row k="Share of the whole tax base" v={`${shareOfBase.toFixed(2)}%`} />
            <Row k="Versus the town's recent new growth"
              v={`${(newValue / MODEL.taxBase.fy23NewValue).toFixed(1)}×`} />
            <Row k="By year 10" v={usd(data[9].growth)} bold />
            <Row k="Ten-year total"
              v={usd(data.reduce((s, d) => s + d.growth, 0))} bold />
            <p className="text-[12px] leading-relaxed pt-2 border-t"
              style={{ borderColor: 'var(--grid)', color: 'var(--text-secondary)' }}>
              Every $1M of new value is worth <strong>{usd((1_000_000 * T.rate) / 1000)}</strong>{' '}
              a year to the town — and it never goes away. It joins the levy limit
              permanently and grows 2.5% a year on top. About{' '}
              {usd(((1_000_000 * T.rate) / 1000) * share)} of that reaches the schools.
            </p>
          </div>
        </div>
      </div>

      {!compact && <>
      {/* The question everybody asks second: if a building is permanent, why do we need
          new ones every year? */}
      <div className="card p-5 mb-4">
        <h3 className="text-sm font-bold mb-2">
          Built once, or built again every year?
        </h3>
        <div className="grid gap-4 md:grid-cols-2 text-[13px] leading-relaxed"
          style={{ color: 'var(--text-secondary)' }}>
          <div>
            <p className="text-[11px] font-bold uppercase tracking-widest mb-1"
              style={{ color: 'var(--text-muted)' }}>What a building does forever</p>
            <p>
              A development added this year raises the levy limit by its tax value{' '}
              <strong>permanently</strong>. It does not have to be rebuilt, and the town
              does not lose it next year. From then on it is simply part of the base, and
              the whole base rises 2.5% a year.
            </p>
          </div>
          <div>
            <p className="text-[11px] font-bold uppercase tracking-widest mb-1"
              style={{ color: 'var(--text-muted)' }}>What it stops doing</p>
            <p>
              It only counts as <em>new growth</em> once &mdash; in the year it is added.
              After that it grows 2.5% like every other property. So &ldquo;
              {(closesAt / arch.value).toFixed(0)} developments a year&rdquo; means{' '}
              {(closesAt / arch.value).toFixed(0)} <strong>more</strong> each year, on top
              of last year&rsquo;s, standing and cumulative.
            </p>
          </div>
        </div>
        <p className="text-[13px] leading-relaxed mt-3 pt-3 border-t"
          style={{ color: 'var(--text-secondary)', borderColor: 'var(--grid)' }}>
          <strong>Why once is not enough.</strong> The gap grows by roughly $600,000 to
          $760,000 every year, because costs rise faster than Proposition 2&frac12; lets
          revenue rise. A one-off wave of building lifts the base permanently, but that
          lift then grows only 2.5% a year &mdash; about $20,000 &mdash; while the gap
          grows thirty times faster. So a single good year of development closes the gap
          once and then watches it reopen. Only a <em>sustained</em> rate keeps pace, which
          is what the slider above sets.
        </p>
      </div>

      <div className="card p-5 mb-4">
        <h3 className="text-sm font-bold mb-1">Business growth versus an override</h3>
        <p className="text-[12px] mb-4" style={{ color: 'var(--text-secondary)' }}>
          Both are permanent. An override arrives in full immediately but comes out of
          existing taxpayers&rsquo; pockets. New growth starts small and compounds, and
          nobody&rsquo;s bill goes up.
        </p>
        <div style={{ width: '100%', height: 260 }}>
          <ResponsiveContainer>
            <LineChart data={data} margin={{ top: 8, right: 12, bottom: 4, left: 4 }}>
              <CartesianGrid stroke="var(--grid)" vertical={false} />
              <XAxis dataKey="year" tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
                stroke="var(--axis)" tickLine={false}
                tickFormatter={v => `yr ${v}`} />
              <YAxis width={56} tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
                stroke="var(--axis)" tickLine={false} axisLine={false}
                tickFormatter={v => usdShort(v as number)} />
              <Tooltip
                contentStyle={{ background: 'var(--surface-1)', border: '1px solid var(--grid)',
                                borderRadius: 10, fontSize: 12, color: 'var(--text-primary)' }}
                labelFormatter={v => `Year ${v}`}
                formatter={(v, n) => [usd(v as number),
                  n === 'growth' ? 'From business growth' : 'From an override']} />
              <Legend verticalAlign="top" height={28} iconType="plainline"
                wrapperStyle={{ fontSize: 12, color: 'var(--text-secondary)' }}
                formatter={v => v === 'growth' ? 'From business growth' : 'From an override'} />
              <Line type="monotone" dataKey="growth" stroke="var(--series-cost)"
                strokeWidth={2} dot={false} isAnimationActive={false} />
              <Line type="monotone" dataKey="override" stroke="var(--series-revenue)"
                strokeWidth={2} strokeDasharray="5 4" dot={false} isAnimationActive={false} />
              {cross && <ReferenceDot x={cross.year} y={cross.growth} r={5}
                fill="var(--surface-1)" stroke="var(--series-cost)" strokeWidth={2} />}
            </LineChart>
          </ResponsiveContainer>
        </div>
        <p className="text-[13px] leading-relaxed mt-3">
          {cross
            ? <>At {usdShort(newValue)} of new commercial value a year, business growth
              overtakes a {usd(gap)} override in <strong>year {cross.year}</strong> — and
              keeps climbing after that, without raising anyone&rsquo;s tax bill.</>
            : <>At this rate business growth never catches a {usd(gap)} override within ten
              years. Raise the slider to see what it would take.</>}
        </p>
      </div>

      <div className="mb-4"><TaxpayerView newValue={newValue} gap={gap} /></div>

      <div className="mb-4"><GrowthReality newValue={newValue} /></div>

      <div className="card p-5" style={{ borderColor: 'var(--status-serious)' }}>
        <h3 className="text-sm font-bold mb-2">The honest part</h3>
        <ul className="space-y-2 text-[13px] leading-relaxed list-disc pl-4"
          style={{ color: 'var(--text-secondary)' }}>
          <li>
            Closing the FY28 gap with new growth <em>alone, in one year</em> would take{' '}
            <strong>{usd(valueForGap)}</strong> of new taxable value — about{' '}
            {((valueForGap / T.totalValue) * 100).toFixed(2)}% of the entire town tax base,
            added at once — about{' '}
            {(valueForGap / arch.value).toFixed(0)}{' '}
            × {arch.name.split('(')[0].trim().toLowerCase()} in twelve months, when the town
            currently permits nothing like that many.
          </li>
          <li>
            The town already budgets <strong>{usd(T.currentNewGrowthRevenue)}</strong> of new
            growth a year, implying about {usdShort(T.currentNewGrowthValue)} of new value
            annually — most of it residential. Commercial growth has to be{' '}
            <em>on top of</em> that to help.
          </li>
          <li>
            Commercial development is not free: it needs roads, water, sewer, permitting and
            public-safety response. This model counts the revenue, not those costs.
          </li>
          <li>
            None of this arrives in time for FY28. The budget is voted in spring 2027;
            buildings take years. Business growth is the answer to FY32, not next year.
          </li>
        </ul>
      </div>
      </>}
    </div>
  )
}

/** Why residential growth makes the school budget worse, not better. */
export function ResidentialParadox() {
  const [kids, setKids] = useState(2)
  const cost = kids * T.localCostPerPupil
  const net = T.schoolShareOfBill - cost

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <div className="card p-5">
        <h3 className="text-sm font-bold mb-4">One student, in tax bills</h3>
        <dl className="space-y-2.5 text-[13px]">
          <Row k="Average single-family assessment" v={usd(T.avgHomeValue)} />
          <Row k="Average annual tax bill" v={usd(T.avgHomeBill)} />
          <Row k="Share of that bill going to schools"
            v={`${usd(T.schoolShareOfBill)} (${(T.schoolShareOfBudget * 100).toFixed(0)}%)`} />
          <Row k="Chapter 70 aid per pupil"
            v={usd(T.ch70.aid / T.ch70.foundationEnrollment)} />
          <Row k="Cost per pupil paid locally" v={usd(T.localCostPerPupil)} bold />
        </dl>
        <p className="text-2xl font-bold leading-snug mt-4 pt-4 border-t"
          style={{ borderColor: 'var(--grid)' }}>
          It takes the school share of{' '}
          <span style={{ color: 'var(--status-critical)' }}>
            {T.homesPerPupil} average tax bills
          </span>{' '}
          to educate one child.
        </p>
      </div>

      <div className="card p-5">
        <h3 className="text-sm font-bold mb-4">So what does a new house do?</h3>
        <div className="flex items-baseline justify-between mb-1">
          <label htmlFor="kids" className="text-[13px] font-medium">
            Children in the new house
          </label>
          <span className="text-xl font-bold tnum">{kids}</span>
        </div>
        <input id="kids" type="range" min={0} max={4} step={1} value={kids}
          onChange={e => setKids(Number(e.target.value))} className="w-full mb-4" />

        <dl className="space-y-2.5 text-[13px]">
          <Row k="School taxes it pays" v={usd(T.schoolShareOfBill)} />
          <Row k="School costs it creates" v={usd(cost)} />
        </dl>
        <p className="text-3xl font-bold tnum mt-4 pt-4 border-t"
          style={{ borderColor: 'var(--grid)',
                   color: net >= 0 ? 'var(--status-good)' : 'var(--status-critical)' }}>
          {net >= 0 ? '+' : ''}{usd(net)}<span className="text-sm font-normal"
            style={{ color: 'var(--text-secondary)' }}> per year</span>
        </p>
        <p className="text-[13px] leading-relaxed mt-3" style={{ color: 'var(--text-secondary)' }}>
          {kids === 0
            ? 'A house with no children in it pays for schools and uses none of them. So does a business.'
            : <>A house with {kids} child{kids > 1 ? 'ren' : ''} costs the schools{' '}
              {usd(Math.abs(net))} a year more than it contributes. <strong>Residential
              growth makes the school budget harder, not easier.</strong> A commercial
              building of the same assessed value pays the same tax and sends nobody.</>}
        </p>
        <p className="text-[11px] mt-3" style={{ color: 'var(--text-muted)' }}>
          Local cost per pupil is the {usd(MODEL.fy27.lps_appropriation)} school
          appropriation less {usd(T.ch70.aid)} of Chapter 70 aid, over {T.enrollment}{' '}
          students. It is an average: a student needing special education costs far more,
          and the town also collects local receipts and other aid that this comparison
          leaves out.
        </p>
      </div>
    </div>
  )
}

function Row({ k, v, bold }: { k: string; v: string; bold?: boolean }) {
  return (
    <div className="flex items-baseline justify-between gap-3">
      <dt className="min-w-0" style={{ color: 'var(--text-secondary)' }}>{k}</dt>
      <dd className={`tnum text-right ${bold ? 'font-bold text-base' : 'font-semibold'}`}>{v}</dd>
    </div>
  )
}
