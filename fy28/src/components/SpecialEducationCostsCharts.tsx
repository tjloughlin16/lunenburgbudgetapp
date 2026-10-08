import {
  Bar, BarChart, CartesianGrid, ComposedChart, Legend, Line, LineChart, ReferenceLine,
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
 * breaker is neutral because it is money coming back, not a cost line.
 *
 * The circuit breaker chart is all tuition, split by WHO PAID IT, so there the tuition hue
 * is the general fund (the money the town votes) and the revenue hue is the circuit
 * breaker account (money the state paid back, spent without a town vote). Its two lines
 * are the state's payments: solid by the year received, dashed by the year whose costs
 * earned them -- the same series a year apart, which is how the lag shows. */

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
type CbRow = {
  fy: number; basis: string; gf: number | null; cb_account: number | null
  other: number | null; other_unsplit: number | null; total: number | null
  received: number | null; earned: number | null
}
type Payload = {
  surprise: Surprise[]
  surprise_keys: { key: string; name: string }[]
  trend: Trend[]
  circuit_breaker: {
    rows: CbRow[]
    keys: { key: keyof CbRow; name: string }[]
    lines: { key: keyof CbRow; name: string }[]
  }
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

/** THE CIRCUIT BREAKER SECTION'S SIGNATURE: tuition by who paid it, and the state's money
 *  beside it -- received (solid) against earned a year earlier (dashed). */
export function SpecialEducationCostsCircuitBreaker({ data }: ChartProps) {
  const d = (data as Payload).circuit_breaker
  const rows = d.rows.map(r => ({ ...r, label: `FY${String(r.fy).slice(2)}` }))
  const fill: Record<string, { c: string; o?: number }> = {
    gf: { c: 'var(--series-cost)' }, cb_account: { c: 'var(--series-revenue)' },
    other: { c: 'var(--text-muted)', o: 0.75 }, other_unsplit: { c: 'var(--text-muted)', o: 0.35 },
  }
  const basis: Record<string, string> = {
    dese: 'every fund (DESE); the circuit breaker account is not separated before FY2023',
    'dese+munis': 'every fund (DESE), circuit breaker account from the town ledger',
    munis: 'town ledger only; other funds not yet published by DESE',
  }
  return (
    <div style={{ width: '100%', height: 380 }}>
      <ResponsiveContainer>
        <ComposedChart data={rows} margin={{ top: 8, right: 8, left: 4, bottom: 4 }}>
          <CartesianGrid stroke="var(--grid)" vertical={false} />
          <XAxis dataKey="label" tick={{ fontSize: 11, fill: 'var(--text-muted)' }}
            interval="preserveStartEnd" minTickGap={8} />
          <YAxis width={56} tickFormatter={v => short(N(v))}
            tick={{ fontSize: 11, fill: 'var(--text-muted)' }} />
          <Tooltip contentStyle={box}
            formatter={(v, name) => [usd(N(v)), String(name)]}
            labelFormatter={(_l, p) => {
              const r = (p?.[0] as { payload?: CbRow } | undefined)?.payload
              if (!r) return ''
              const tot = r.total != null ? `tuition, every fund ${usd(r.total)}` : 'every-fund total not yet published'
              return `FY${r.fy} — ${tot} · ${basis[r.basis] ?? ''}`
            }} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          {d.keys.map(k => (
            <Bar key={k.key} dataKey={k.key} name={k.name} stackId="paid"
              fill={fill[k.key]?.c} fillOpacity={fill[k.key]?.o ?? 1} isAnimationActive={false} />
          ))}
          {d.lines.map((l, i) => (
            <Line key={l.key} dataKey={l.key} name={l.name} type="linear"
              stroke="var(--text-primary)" strokeWidth={2} strokeDasharray={i ? '5 4' : undefined}
              dot={{ r: 2.5 }} connectNulls={false} isAnimationActive={false} />
          ))}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}
