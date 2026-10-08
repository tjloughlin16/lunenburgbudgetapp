import {
  Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ReferenceLine,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import type { ChartProps } from './analysisCharts'

/* The charts for /analysis/special-education-costs, from /data/special-education-costs.json.
 * Rule 7f. Nothing here computes a figure: every value, name and year arrives from the
 * payload scripts/build_sped_costs.py writes -- the same payload the stat row and the
 * conclusion cards read.
 *
 * Colours: the site's two series tokens and the one validated third hue (--ch70-floor),
 * so tuition, in-district and transportation never borrow each other's colour between the
 * two charts. The "every fund" tuition line is drawn dashed in the tuition colour rather
 * than given a fourth hue, because it is the same quantity on a wider basis; the circuit
 * breaker is neutral because it is money coming back, not a cost line. */

const N = (v: unknown) => (Array.isArray(v) ? Number(v[0]) : Number(v))
const usd = (v: number) => `${v < 0 ? '−' : ''}$${Math.abs(Math.round(v)).toLocaleString('en-US')}`
const signed = (v: number) => `${v > 0 ? '+' : ''}${usd(v)}`
const short = (v: number) => {
  const a = Math.abs(v)
  const s = a >= 1e6 ? `$${(a / 1e6).toFixed(1)}M` : a >= 1e3 ? `$${Math.round(a / 1e3)}k` : `$${a}`
  return v < 0 ? `−${s}` : s
}

const COLOUR: Record<string, string> = {
  ood: 'var(--series-cost)', indist: 'var(--series-revenue)', trans: 'var(--ch70-floor)',
}

type Surprise = { fy: number; ood: number; indist: number; trans: number; need: number }
type Trend = {
  fy: number; indist_spent: number | null; ood_gf_spent: number | null
  ood_all_funds: number | null; cb_paid: number | null
}
type Payload = {
  surprise: Surprise[]
  surprise_keys: { key: string; name: string }[]
  trend: Trend[]
}

const box = {
  background: 'var(--surface-1)', border: '1px solid var(--grid)',
  borderRadius: 8, fontSize: 12.5, color: 'var(--text-primary)',
  boxShadow: '0 2px 10px rgba(0,0,0,.12)', opacity: 1,
}

/** THE SIGNATURE: how far each line landed from the budget voted for it, every year. */
export function SpecialEducationCostsSurprise({ data }: ChartProps) {
  const d = data as Payload
  const rows = d.surprise.map(r => ({ ...r, label: `FY${String(r.fy).slice(2)}` }))
  return (
    <div style={{ width: '100%', height: 360 }}>
      <ResponsiveContainer>
        <BarChart data={rows} margin={{ top: 8, right: 8, left: 4, bottom: 4 }} barGap={0}>
          <CartesianGrid stroke="var(--grid)" vertical={false} />
          <XAxis dataKey="label" tick={{ fontSize: 11, fill: 'var(--text-muted)' }}
            interval="preserveStartEnd" minTickGap={8} />
          <YAxis width={56} tickFormatter={v => short(N(v))}
            tick={{ fontSize: 11, fill: 'var(--text-muted)' }} />
          <ReferenceLine y={0} stroke="var(--text-muted)" />
          <Tooltip contentStyle={box}
            formatter={(v, name) => [`${signed(N(v))} against the budget voted`, String(name)]}
            labelFormatter={(_l, p) => {
              const r = (p?.[0] as { payload?: Surprise } | undefined)?.payload
              return r ? `FY${r.fy} — overruns added: ${usd(r.need)}` : ''
            }} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          {d.surprise_keys.map(k => (
            <Bar key={k.key} dataKey={k.key} name={k.name} fill={COLOUR[k.key]}
              isAnimationActive={false} />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

/** Spending by year, each series on its own basis; the circuit breaker beside, never netted. */
export function SpecialEducationCostsTrend({ data }: ChartProps) {
  const d = data as Payload
  const rows = d.trend.map(r => ({ ...r, label: `FY${String(r.fy).slice(2)}` }))
  const lines: { key: keyof Trend; name: string; stroke: string; dash?: string }[] = [
    { key: 'indist_spent', name: 'In district, general fund', stroke: COLOUR.indist },
    { key: 'ood_gf_spent', name: 'Tuition, general fund', stroke: COLOUR.ood },
    { key: 'ood_all_funds', name: 'Tuition, every fund (DESE)', stroke: COLOUR.ood, dash: '5 4' },
    { key: 'cb_paid', name: 'Circuit breaker paid', stroke: 'var(--text-muted)' },
  ]
  return (
    <div style={{ width: '100%', height: 340 }}>
      <ResponsiveContainer>
        <LineChart data={rows} margin={{ top: 8, right: 16, left: 4, bottom: 4 }}>
          <CartesianGrid stroke="var(--grid)" vertical={false} />
          <XAxis dataKey="label" tick={{ fontSize: 11, fill: 'var(--text-muted)' }}
            interval="preserveStartEnd" minTickGap={16} />
          <YAxis width={56} tickFormatter={v => short(N(v))}
            tick={{ fontSize: 11, fill: 'var(--text-muted)' }} />
          <Tooltip contentStyle={box} formatter={(v, name) => [usd(N(v)), String(name)]} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          {lines.map(l => (
            <Line key={l.key} dataKey={l.key} name={l.name} dot={false}
              isAnimationActive={false} strokeWidth={2.2} stroke={l.stroke}
              strokeDasharray={l.dash} connectNulls={false} />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
