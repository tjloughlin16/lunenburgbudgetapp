import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, ReferenceLine, Cell,
} from 'recharts'
import { MODEL, usd, usdShort } from '../model/engine'

const T = MODEL.taxBase

/** New growth over time, and which classes are actually growing. */
export function CommercialTrend() {
  const ng = T.newGrowthHistory
  const decline = (ng.at(-1)!.amount / ng[0].amount - 1) * 100
  const maxAbs = Math.ceil(Math.max(...T.valueByClass.map(v => Math.abs(v.pct))) / 5) * 5

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <div className="card p-5">
        <h3 className="text-sm font-bold mb-1">New growth is falling</h3>
        <p className="text-[12px] mb-4" style={{ color: 'var(--text-secondary)' }}>
          New growth is the only thing that raises the levy limit without an override.
          Lunenburg&rsquo;s has dropped <strong>{Math.abs(decline).toFixed(0)}%</strong> in
          five years.
        </p>
        <div style={{ width: '100%', height: 200 }}>
          <ResponsiveContainer>
            <BarChart data={ng} margin={{ top: 8, right: 8, bottom: 4, left: 4 }}>
              <CartesianGrid stroke="var(--grid)" vertical={false} />
              <XAxis dataKey="fy" tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
                stroke="var(--axis)" tickLine={false} tickFormatter={v => `FY${String(v).slice(2)}`} />
              <YAxis width={54} tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
                stroke="var(--axis)" tickLine={false} axisLine={false}
                tickFormatter={v => usdShort(v as number)} />
              <Tooltip
                contentStyle={{ background: 'var(--surface-1)', border: '1px solid var(--grid)',
                                borderRadius: 10, fontSize: 12, color: 'var(--text-primary)' }}
                labelFormatter={v => `FY${v}`}
                formatter={v => [usd(v as number), 'New growth']} />
              <ReferenceLine y={T.currentNewGrowthRevenue} stroke="var(--status-critical)"
                strokeDasharray="4 4"
                label={{ value: 'FY27 budgeted $400k', position: 'insideTopRight',
                         fill: 'var(--status-critical)', fontSize: 10 }} />
              <Bar dataKey="amount" fill="var(--series-cost)" radius={[4, 4, 0, 0]}
                isAnimationActive={false} />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <p className="text-[12px] leading-relaxed mt-3" style={{ color: 'var(--text-secondary)' }}>
          The FY27 budget assumes <strong>{usd(T.currentNewGrowthRevenue)}</strong> of new
          growth. The town has not reached that since FY22, and FY23 came in at{' '}
          {usd(ng.at(-1)!.amount)} — barely half. Every dollar it falls short is a dollar
          the schools do not get.
        </p>
      </div>

      <div className="card p-5">
        <h3 className="text-sm font-bold mb-1">Only one class is growing</h3>
        <p className="text-[12px] mb-4" style={{ color: 'var(--text-secondary)' }}>
          Change in assessed value by class, FY22 to FY23. Commercial, industrial and
          personal property all fell in <em>absolute dollars</em>.
        </p>
        <div style={{ width: '100%', height: 200 }}>
          <ResponsiveContainer>
            <BarChart data={T.valueByClass} layout="vertical"
              margin={{ top: 8, right: 40, bottom: 4, left: 4 }}>
              <CartesianGrid stroke="var(--grid)" horizontal={false} />
              <XAxis type="number" domain={[-maxAbs, maxAbs]}
                ticks={[-maxAbs, -maxAbs / 2, 0, maxAbs / 2, maxAbs]}
                tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
                stroke="var(--axis)" tickLine={false}
                tickFormatter={v => `${v}%`} />
              <YAxis type="category" dataKey="cls" width={112}
                tick={{ fill: 'var(--text-secondary)', fontSize: 11 }}
                stroke="var(--axis)" tickLine={false} axisLine={false} />
              <Tooltip
                contentStyle={{ background: 'var(--surface-1)', border: '1px solid var(--grid)',
                                borderRadius: 10, fontSize: 12, color: 'var(--text-primary)' }}
                formatter={(v, _n, p) => [
                  `${v as number}%  (${usd((p.payload as { change: number }).change)})`,
                  'Change FY22 to FY23']} />
              <ReferenceLine x={0} stroke="var(--axis)" />
              <Bar dataKey="pct" radius={3} isAnimationActive={false}>
                {T.valueByClass.map(v => (
                  <Cell key={v.cls}
                    fill={v.pct >= 0 ? 'var(--series-cost)' : 'var(--status-critical)'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
        <p className="text-[12px] leading-relaxed mt-3" style={{ color: 'var(--text-secondary)' }}>
          Residential grew <strong>{usd(T.valueByClass[0].change)}</strong> in one year while
          the entire commercial, industrial and personal-property base <em>shrank</em> by{' '}
          <strong>{usd(Math.abs(T.valueByClass.slice(1).reduce((s, v) => s + v.change, 0)))}</strong>.
          That is the concern, in the town&rsquo;s own figures.
        </p>
      </div>
    </div>
  )
}

/** Values up, rate down, bills barely moved — Prop 2½ in one table. */
export function HomeValueParadox() {
  const h = T.avgHomeHistory
  const a = h[0], b = h.at(-1)!
  return (
    <div className="card p-5">
      <h3 className="text-sm font-bold mb-1">Values up 52%. Bills up 19%.</h3>
      <p className="text-[12px] mb-4" style={{ color: 'var(--text-secondary)' }}>
        The Assessors&rsquo; own five-year table. As values rose, the rate was cut to keep
        the levy under the Proposition 2½ cap.
      </p>
      <div style={{ width: '100%', height: 200 }}>
        <ResponsiveContainer>
          <LineChart data={h.map(x => ({ ...x,
            valueIdx: (x.value / a.value) * 100,
            billIdx: (x.bill / a.bill) * 100,
            rateIdx: (x.rate / a.rate) * 100 }))}
            margin={{ top: 8, right: 12, bottom: 4, left: 4 }}>
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="fy" tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
              stroke="var(--axis)" tickLine={false} tickFormatter={v => `FY${String(v).slice(2)}`} />
            <YAxis width={44} tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
              stroke="var(--axis)" tickLine={false} axisLine={false}
              tickFormatter={v => `${v}`} />
            <Tooltip
              contentStyle={{ background: 'var(--surface-1)', border: '1px solid var(--grid)',
                              borderRadius: 10, fontSize: 12, color: 'var(--text-primary)' }}
              labelFormatter={v => `FY${v}`}
              formatter={(v, n) => [`${(v as number).toFixed(0)} (FY19 = 100)`,
                n === 'valueIdx' ? 'Home value' : n === 'billIdx' ? 'Tax bill' : 'Tax rate']} />
            <Legend verticalAlign="top" height={26} iconType="plainline"
              wrapperStyle={{ fontSize: 11, color: 'var(--text-secondary)' }}
              formatter={v => v === 'valueIdx' ? 'Home value'
                : v === 'billIdx' ? 'Tax bill' : 'Tax rate'} />
            <ReferenceLine y={100} stroke="var(--axis)" strokeDasharray="3 3" />
            <Line dataKey="valueIdx" stroke="var(--series-cost)" strokeWidth={2}
              dot={{ r: 3 }} isAnimationActive={false} />
            <Line dataKey="billIdx" stroke="var(--series-revenue)" strokeWidth={2}
              dot={{ r: 3 }} isAnimationActive={false} />
            <Line dataKey="rateIdx" stroke="var(--status-serious)" strokeWidth={2}
              strokeDasharray="5 4" dot={{ r: 3 }} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div className="overflow-x-auto mt-3">
        <table className="stack w-full text-xs tnum sm:min-w-[380px]">
          <caption className="sr-only">
            Average single-family assessment, tax rate and tax bill by fiscal year
          </caption>
          <thead>
            <tr className="text-left" style={{ color: 'var(--text-muted)' }}>
              <th className="font-semibold py-1.5">Year</th>
              <th className="font-semibold py-1.5 text-right">Tax rate</th>
              <th className="font-semibold py-1.5 text-right">Average home</th>
              <th className="font-semibold py-1.5 text-right">Average bill</th>
            </tr>
          </thead>
          <tbody>
            {h.map(x => (
              <tr key={x.fy} className="border-t" style={{ borderColor: 'var(--grid)' }}>
                <td className="rowhead py-1.5 font-semibold">FY{x.fy}</td>
                <td data-label="Tax rate" className="py-1.5 text-right">${x.rate.toFixed(2)}</td>
                <td data-label="Average home" className="py-1.5 text-right">{usd(x.value)}</td>
                <td data-label="Average bill" className="py-1.5 text-right">{usd(x.bill)}</td>
              </tr>
            ))}
            <tr className="border-t-2 font-bold" style={{ borderColor: 'var(--axis)' }}>
              <td className="rowhead py-2">Five-year change</td>
              <td data-label="Tax rate" className="py-2 text-right"
                style={{ color: 'var(--status-good)' }}>
                {((b.rate / a.rate - 1) * 100).toFixed(0)}%
              </td>
              <td data-label="Average home"
                className="py-2 text-right">+{((b.value / a.value - 1) * 100).toFixed(0)}%</td>
              <td data-label="Average bill"
                className="py-2 text-right">+{((b.bill / a.bill - 1) * 100).toFixed(0)}%</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  )
}

/** What a slider figure means in businesses. */
export function GrowthReality({ newValue }: { newValue: number }) {
  const g = T.gapInBusinesses.sustained
  const businesses = newValue / T.avgCommercialValue
  const pctCommercial = (newValue / T.fy23.cipValue) * 100
  const vsActual = newValue / T.fy23NewValue
  const c = T.commercialContext

  return (
    <div className="card p-5" style={{ borderColor: 'var(--status-serious)' }}>
      <h3 className="text-sm font-bold mb-3">
        What {usdShort(newValue)} a year actually means for Lunenburg
      </h3>
      <div className="grid gap-4 sm:grid-cols-3 mb-4">
        <Fig v={businesses.toFixed(0)} k="more average businesses"
          s={`every year, on top of the ${T.businesses} the town has now`} />
        <Fig v={`+${pctCommercial.toFixed(1)}%`} k="of the commercial base"
          s="added every single year, sustained" />
        <Fig v={`${vsActual.toFixed(1)}×`} k="the town's recent new growth"
          s={`FY23 added about ${usdShort(T.fy23NewValue)} across all classes`} />
      </div>
      {/* What it would take to carry the whole gap on business growth alone */}
      <div className="rounded-lg p-4 mb-4"
        style={{ background: 'var(--surface-2)', border: '1px solid var(--grid)' }}>
        <p className="text-[11px] font-semibold uppercase tracking-widest mb-2"
          style={{ color: 'var(--text-muted)' }}>
          To carry the whole gap on business growth alone
        </p>
        <div className="grid gap-4 sm:grid-cols-3 mb-3">
          <Fig v={`${g.businesses}`} k="new businesses a year"
            s={`a ${g.pctOfToday}% increase on today's ${T.businesses}, every year`} />
          <Fig v={`${g.fiveYearTotal}`} k="businesses after five years"
            s={`up from ${T.businesses} — a ${g.fiveYearPct}% increase`} />
          <Fig v={`${g.vsActualNewGrowth}×`} k="the town's actual new growth"
            s="FY23 delivered less than half of one year of this" />
        </div>
        <div className="h-3 rounded-full overflow-hidden flex gap-0.5"
          style={{ background: 'var(--surface-3)' }}>
          <div className="h-full" title="businesses today"
            style={{ width: `${(T.businesses / g.fiveYearTotal) * 100}%`,
                     background: 'var(--series-cost)' }} />
          <div className="h-full" title="businesses that would have to be added"
            style={{ width: `${(g.fiveYearAdded / g.fiveYearTotal) * 100}%`,
                     background: 'var(--status-serious)' }} />
        </div>
        <p className="text-[11px] mt-1.5" style={{ color: 'var(--text-muted)' }}>
          <span aria-hidden="true" style={{ color: 'var(--series-cost)' }}>&#9632; </span>
          {T.businesses} today &nbsp;
          <span aria-hidden="true" style={{ color: 'var(--status-serious)' }}>&#9632; </span>
          {g.fiveYearAdded} more needed over five years
        </p>
        <p className="text-[12px] leading-relaxed mt-2.5"
          style={{ color: 'var(--text-secondary)' }}>
          Closing the FY28 gap in a single year needs{' '}
          {usd(T.gapInBusinesses.fy28.value)} of new value —{' '}
          {T.gapInBusinesses.fy28.businesses} average businesses, a{' '}
          {T.gapInBusinesses.fy28.pctOfToday}% jump in twelve months. But the gap returns
          every year, so carrying it on development alone means about {g.businesses} more
          businesses annually —{' '}
          <strong>more than doubling the number of businesses in Lunenburg within five
          years</strong>. That is not an argument against commercial growth; it is an
          argument against treating it as the whole answer.
        </p>
      </div>

      <ul className="space-y-2 text-[12px] leading-relaxed list-disc pl-4"
        style={{ color: 'var(--text-secondary)' }}>
        <li>
          Lunenburg has <strong>{T.businesses} business establishments</strong> employing{' '}
          {T.employees.toLocaleString()} people (Census, 2024). The whole commercial,
          industrial and personal-property base is {usdShort(T.fy23.cipValue)} —{' '}
          {(T.fy23.cipShare * 100).toFixed(1)}% of the town&rsquo;s value — which works out
          to about <strong>{usd(T.avgCommercialValue)}</strong> per establishment.
        </li>
        <li>
          Development clusters where sewer reaches: {c.corridors.join('; ')}. {c.anchor}
        </li>
        <li>
          The town&rsquo;s economic development targets are {c.targets.join(' and ').toLowerCase()}.
          {' '}{c.constraint}
        </li>
      </ul>
    </div>
  )
}

function Fig({ v, k, s }: { v: string; k: string; s: string }) {
  return (
    <div>
      <p className="text-3xl font-bold tnum leading-none">{v}</p>
      <p className="text-[12px] font-semibold mt-1">{k}</p>
      <p className="text-[11px]" style={{ color: 'var(--text-muted)' }}>{s}</p>
    </div>
  )
}
