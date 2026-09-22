import {
  Bar, BarChart, CartesianGrid, Cell, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import type { ChartProps } from './analysisCharts'

/* Recharts hands a tooltip value as `ValueType | undefined` -- a string, a number or an
 * array of either. Every formatter here wants a number, so it is coerced once, here,
 * rather than asserted at each call site. */
const N = (v: unknown) => (Array.isArray(v) ? Number(v[0]) : Number(v))

/* The charts for /analysis/stabilization-option, from /data/stabilization-option.json.
 * Rule 7f. EVERY FIGURE HERE IS MODELLED, not measured -- this page asks what would
 * happen if the reserve were spent on the school gap -- so the axis labels and the
 * tooltips say `scenario` rather than naming a year as if it had happened. Rule 7b: a
 * modelled figure must stay visibly modelled however short the label gets. */

const box = {
  background: 'var(--surface-1)', border: '1px solid var(--grid)',
  borderRadius: 8, fontSize: 12.5, color: 'var(--text-primary)',
  boxShadow: '0 2px 10px rgba(0,0,0,.12)', opacity: 1,
}
const usdk = (v: number) =>
  Math.abs(N(v)) >= 1e6 ? `$${(v / 1e6).toFixed(1)}M`
    : Math.abs(N(v)) >= 1e3 ? `$${Math.round(v / 1e3)}k` : `$${Math.round(v)}`
const usd = (v: number) => '$' + Math.round(v).toLocaleString()

type Both = {
  fy: number; gap: number; redirected: number; drawn: number
  left: number; shortfall: number
}
type Burn = { fy: number; gap: number; covered: number; left: number; shortfall: number }
type Payload = { both: Both[]; burndown: Burn[] }

/** Each year's gap, split into what the reserve could cover and what stays short. */
export function StabilizationOptionSplit({ data }: ChartProps) {
  const rows = (data as Payload).both.map(r => ({
    fy: `FY${r.fy}`,
    redirected: r.redirected,
    // The per-year draw, net of the part the redirected deposits already covered.
    reserve: Math.max(r.drawn - r.redirected, 0),
    short: r.shortfall,
  }))
  return (
    <div style={{ width: '100%', height: 360 }}>
      <ResponsiveContainer>
        <BarChart data={rows} margin={{ top: 8, right: 16, left: 4, bottom: 4 }}>
          <CartesianGrid stroke="var(--grid)" vertical={false} />
          <XAxis dataKey="fy" tick={{ fontSize: 11, fill: 'var(--text-muted)' }} />
          <YAxis tickFormatter={usdk} width={54}
            tick={{ fontSize: 11, fill: 'var(--text-muted)' }} />
          <Tooltip contentStyle={box} formatter={(v) => usd(N(v))} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Bar dataKey="redirected" stackId="g" name="redirected deposits"
            fill="#22795a" isAnimationActive={false} />
          <Bar dataKey="reserve" stackId="g" name="drawn from the reserve"
            fill="#184f95" isAnimationActive={false} />
          <Bar dataKey="short" stackId="g" name="still short"
            fill="#e08214" isAnimationActive={false} radius={[3, 3, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

/** What is left in the fund each year under the scenario, until it is empty. */
export function StabilizationOptionBurndown({ data }: ChartProps) {
  const rows = (data as Payload).burndown.map(r => ({
    fy: `FY${r.fy}`, left: r.left, covered: r.covered,
  }))
  return (
    <div style={{ width: '100%', height: 320 }}>
      <ResponsiveContainer>
        <BarChart data={rows} margin={{ top: 8, right: 16, left: 4, bottom: 4 }}>
          <CartesianGrid stroke="var(--grid)" vertical={false} />
          <XAxis dataKey="fy" tick={{ fontSize: 11, fill: 'var(--text-muted)' }} />
          <YAxis tickFormatter={usdk} width={54}
            tick={{ fontSize: 11, fill: 'var(--text-muted)' }} />
          <Tooltip contentStyle={box}
            formatter={(v, n) =>
              [usd(N(v)), n === 'left' ? 'left in the fund, modelled' : 'drawn that year']} />
          <Bar dataKey="left" name="left in the fund" isAnimationActive={false}
            radius={[3, 3, 0, 0]}>
            {rows.map(r => (
              <Cell key={r.fy} fill={r.left > 0 ? '#184f95' : '#9aa4ad'} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
