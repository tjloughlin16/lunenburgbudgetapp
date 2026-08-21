import {
  ComposedChart, Line, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend,
} from 'recharts'
import { usd, usdShort, type YearProjection } from '../model/engine'

interface Row { fy: string; cost: number; revenue: number; deficit: number }

function GapTooltip({ active, payload }: {
  active?: boolean; payload?: { payload: Row }[]
}) {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  return (
    <div className="rounded-[10px] px-3 py-2 text-xs"
      style={{ background: 'var(--surface-1)', border: '1px solid var(--grid)' }}>
      <p className="font-semibold mb-1.5" style={{ color: 'var(--text-secondary)' }}>{d.fy}</p>
      <p className="flex justify-between gap-4">
        <span style={{ color: 'var(--series-cost)' }}>Cost of today&rsquo;s services</span>
        <span className="tnum font-semibold">{usd(d.cost)}</span>
      </p>
      <p className="flex justify-between gap-4">
        <span style={{ color: 'var(--series-revenue)' }}>Revenue available</span>
        <span className="tnum font-semibold">{usd(d.revenue)}</span>
      </p>
      <p className="flex justify-between gap-4 mt-1 pt-1 border-t"
        style={{ borderColor: 'var(--grid)' }}>
        <span style={{ color: 'var(--status-critical)' }}>Gap</span>
        <span className="tnum font-bold" style={{ color: 'var(--status-critical)' }}>
          {usd(d.deficit)}
        </span>
      </p>
    </div>
  )
}

/** Level-service cost against available revenue. Two series, one axis, shaded gap. */
export function YearChart({ years }: { years: YearProjection[] }) {
  const data = years.map(y => ({
    fy: `FY${y.fy}`,
    cost: y.levelService,
    revenue: y.available,
    gapBand: [y.available, y.levelService] as [number, number],
    deficit: y.deficit,
  }))
  const lo = Math.min(...data.map(d => d.revenue)) * 0.97
  const hi = Math.max(...data.map(d => d.cost)) * 1.02

  return (
    <div className="card p-4">
      <div style={{ width: '100%', height: 300 }}>
        <ResponsiveContainer>
          <ComposedChart data={data} margin={{ top: 8, right: 12, bottom: 4, left: 4 }}>
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="fy" tick={{ fill: 'var(--text-muted)', fontSize: 12 }}
              stroke="var(--axis)" tickLine={false} />
            <YAxis domain={[lo, hi]} width={58}
              tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
              stroke="var(--axis)" tickLine={false} axisLine={false}
              tickFormatter={v => usdShort(v as number)} />
            <Tooltip content={<GapTooltip />} cursor={{ stroke: 'var(--axis)' }} />
            <Legend verticalAlign="top" height={30} iconType="plainline"
              wrapperStyle={{ fontSize: 12, color: 'var(--text-secondary)' }}
              formatter={v => v === 'cost'
                ? 'Cost to keep today’s services' : 'Revenue available'} />
            <Area dataKey="gapBand" fill="var(--status-critical)" fillOpacity={0.13}
              stroke="none" legendType="none" isAnimationActive={false}
              activeDot={false} />
            <Line type="monotone" dataKey="cost" stroke="var(--series-cost)"
              strokeWidth={2} dot={{ r: 4, strokeWidth: 2, fill: 'var(--surface-1)' }}
              isAnimationActive={false} />
            <Line type="monotone" dataKey="revenue" stroke="var(--series-revenue)"
              strokeWidth={2} dot={{ r: 4, strokeWidth: 2, fill: 'var(--surface-1)' }}
              isAnimationActive={false} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      <table className="stack w-full text-xs mt-4 tnum">
        <caption className="sr-only">
          Projected cost of maintaining current services, revenue available, and the resulting gap, by fiscal year, assuming no cuts are made
        </caption>
        <thead>
          <tr className="text-left" style={{ color: 'var(--text-muted)' }}>
            <th className="font-semibold py-1.5">Year</th>
            <th className="font-semibold py-1.5 text-right">Cost of today&rsquo;s services</th>
            <th className="font-semibold py-1.5 text-right">Revenue available</th>
            <th className="font-semibold py-1.5 text-right">Gap</th>
          </tr>
        </thead>
        <tbody>
          {years.map(y => (
            <tr key={y.fy} className="border-t" style={{ borderColor: 'var(--grid)' }}>
              <td className="rowhead py-1.5 font-semibold">FY{y.fy}</td>
              <td data-label="Cost of today&rsquo;s services"
                className="py-1.5 text-right">{usd(y.levelService)}</td>
              <td data-label="Revenue available"
                className="py-1.5 text-right">{usd(y.available)}</td>
              <td data-label="Gap" className="py-1.5 text-right font-semibold"
                style={{ color: 'var(--status-critical)' }}>{usd(y.deficit)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
