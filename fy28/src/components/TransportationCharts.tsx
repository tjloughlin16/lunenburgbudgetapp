import {
  Bar, BarChart, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip,
  XAxis, YAxis,
} from 'recharts'
import type { ChartProps } from './analysisCharts'

/* The charts for /analysis/transportation, from /data/transportation.json. Rule 7f.
 * Nothing here computes a figure: every value, name and year arrives from the payload
 * scripts/build_transportation.py writes -- the same payload the stat row and the
 * conclusion cards read.
 *
 * RULE 1, DRAWN. The signature puts the budget voted before a year and the spending at its
 * close side by side as two bars, never stacked into one: pale is budget, solid is spent.
 * The athletic share is a separate figure on each basis and arrives from the payload.
 *
 * Colours: the subject palette, one hue per kind of bus everywhere on the page, so regular
 * routes, special education and athletics never borrow each other's colour between charts.
 * The fee fund and the circuit breaker are money from OUTSIDE the general fund and share
 * the one green, drawn as their own marks and never added to a general fund bar. */

const N = (v: unknown) => (Array.isArray(v) ? Number(v[0]) : Number(v))
const usd = (v: number) => `${v < 0 ? '−' : ''}$${Math.abs(Math.round(v)).toLocaleString('en-US')}`
const usd2 = (v: number) =>
  `$${v.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
const short = (v: number) => {
  const a = Math.abs(v)
  const s = a >= 1e6 ? `$${(a / 1e6).toFixed(1)}M` : a >= 1e3 ? `$${Math.round(a / 1e3)}k` : `$${a}`
  return v < 0 ? `−${s}` : s
}
const fy = (y: number) => `FY${String(y).slice(2)}`

const COLOUR: Record<string, string> = {
  regular: 'var(--subj-1)', sped: 'var(--subj-4)', athletic: 'var(--subj-2)',
  band: 'var(--text-muted)', outside: 'var(--subj-3)',
}

const box = {
  background: 'var(--surface-1)', border: '1px solid var(--grid)',
  borderRadius: 8, fontSize: 12.5, color: 'var(--text-primary)',
  boxShadow: '0 2px 10px rgba(0,0,0,.12)', opacity: 1,
}
const tick = { fontSize: 11, fill: 'var(--text-muted)' }

type YearRow = {
  fy: number; source: string
  regular_budget: number; regular_spent: number | null
  sped_budget: number; sped_spent: number | null
  athletic_budget: number; athletic_spent: number | null
  band_budget: number; band_spent: number | null
  all_budget: number; all_spent: number | null
  athletic_share_spent?: number; athletic_share_budget?: number
}
type AthRow = {
  fy: number; line_budget: number | null; line_spent: number | null
  sheet_total: number | null; fund_stated: number | null
}
type SportRow = {
  season: string; level: string; sport: string; label: string
  fy2024: number | null; fy2025: number | null; trips: number | null; trips_nowait: number | null
}
type ContractYear = {
  fy: number; optional: boolean; p77: number; p83: number; regular: number
  trip_rate: number; wait_rate: number; total: number
}
type RegRow = { fy: number; budget: number | null; spent: number | null; contract: number | null; optional: boolean }
type SpedRow = { fy: number; budget: number | null; spent: number | null; cb_transport: number | null }
type Payload = {
  by_year: YearRow[]
  by_year_keys: { key: string; name: string }[]
  athletics: AthRow[]
  sports: SportRow[]
  contract: { years: ContractYear[]; regular_line: RegRow[]; trip_full: number; trip_nowait: number }
  sped: SpedRow[]
}

/** THE SIGNATURE: every year, the budget voted (pale) beside the spending (solid), each
 *  split by kind of bus. Athletics is the thin top slice. */
export function TransportationSchoolsAthletics({ data }: ChartProps) {
  const d = data as Payload
  const rows = d.by_year.map(r => {
    const o: Record<string, number | string | null> = { label: fy(r.fy), fy: r.fy }
    for (const k of d.by_year_keys) {
      o[`${k.key}_b`] = (r as unknown as Record<string, number | null>)[`${k.key}_budget`]
      o[`${k.key}_s`] = (r as unknown as Record<string, number | null>)[`${k.key}_spent`]
    }
    o.share_s = r.athletic_share_spent ?? null
    o.share_b = r.athletic_share_budget ?? null
    o.all_b = r.all_budget
    o.all_s = r.all_spent
    return o
  })
  return (
    <div style={{ width: '100%', height: 380 }}>
      <ResponsiveContainer>
        <BarChart data={rows} margin={{ top: 8, right: 8, left: 4, bottom: 4 }} barGap={1}>
          <CartesianGrid stroke="var(--grid)" vertical={false} />
          <XAxis dataKey="label" tick={tick} interval="preserveStartEnd" minTickGap={10} />
          <YAxis width={52} tickFormatter={v => short(N(v))} tick={tick} />
          <Tooltip contentStyle={box}
            formatter={(v, name) => [usd(N(v)), String(name)]}
            labelFormatter={(_l, p) => {
              const r = (p?.[0] as { payload?: Record<string, number | null> } | undefined)?.payload
              if (!r) return ''
              const spent = r.all_s != null
                ? `spent ${usd(Number(r.all_s))}, athletics ${r.share_s}% of it`
                : 'budget only'
              return `FY${r.fy} — voted ${usd(Number(r.all_b))}, athletics ${r.share_b}% of it · ${spent}`
            }} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          {d.by_year_keys.map(k => (
            <Bar key={`${k.key}_b`} dataKey={`${k.key}_b`} name={`${k.name}, budget`}
              stackId="budget" fill={COLOUR[k.key]} fillOpacity={0.4} isAnimationActive={false}
              legendType="none" />
          ))}
          {d.by_year_keys.map(k => (
            <Bar key={`${k.key}_s`} dataKey={`${k.key}_s`} name={k.name}
              stackId="spent" fill={COLOUR[k.key]} isAnimationActive={false} />
          ))}
        </BarChart>
      </ResponsiveContainer>
      <p className="text-[12px] mt-1" style={{ color: 'var(--text-muted)' }}>
        Left bar, pale: budget voted before the year. Right bar, solid: spent at the close.
        General fund. The last year is budget only.
      </p>
    </div>
  )
}

/** Athletics alone, on its own scale: the general fund line, and the full cost where a
 *  district document states one. */
export function TransportationAthletics({ data }: ChartProps) {
  const d = data as Payload
  const rows = d.athletics.map(r => ({ ...r, label: fy(r.fy) }))
  return (
    <div style={{ width: '100%', height: 340 }}>
      <ResponsiveContainer>
        <ComposedChart data={rows} margin={{ top: 8, right: 8, left: 4, bottom: 4 }} barGap={1}>
          <CartesianGrid stroke="var(--grid)" vertical={false} />
          <XAxis dataKey="label" tick={tick} interval="preserveStartEnd" minTickGap={10} />
          <YAxis width={52} tickFormatter={v => short(N(v))} tick={tick} />
          <Tooltip contentStyle={box} formatter={(v, name) => [usd(N(v)), String(name)]} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Bar dataKey="line_budget" name="General fund line, budget" fill={COLOUR.athletic}
            fillOpacity={0.4} isAnimationActive={false} />
          <Bar dataKey="line_spent" name="General fund line, spent" stackId="s"
            fill={COLOUR.athletic} isAnimationActive={false} />
          <Bar dataKey="fund_stated" name="Fee fund, as the district stated it" stackId="s"
            fill={COLOUR.outside} isAnimationActive={false} />
          <Line dataKey="sheet_total" name="Full cost, district by-sport sheet (stated)"
            stroke="var(--text-primary)" strokeWidth={0} dot={{ r: 5, fill: 'var(--text-primary)' }}
            connectNulls={false} isAnimationActive={false} />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}

/** Per sport, both years, with OUR trip estimate in the tooltip. */
export function TransportationSports({ data }: ChartProps) {
  const d = data as Payload
  const rows = d.sports.filter(r => (r.fy2024 ?? 0) > 0 || (r.fy2025 ?? 0) > 0)
  const h = Math.max(320, rows.length * 24 + 60)
  return (
    <div style={{ width: '100%', height: h }}>
      <ResponsiveContainer>
        <BarChart data={rows} layout="vertical" margin={{ top: 4, right: 12, left: 4, bottom: 4 }}
          barGap={0}>
          <CartesianGrid stroke="var(--grid)" horizontal={false} />
          <XAxis type="number" tickFormatter={v => short(N(v))} tick={tick} />
          <YAxis type="category" dataKey="label" width={150} interval={0}
            tick={{ fontSize: 10.5, fill: 'var(--text-secondary)' }} />
          <Tooltip contentStyle={box}
            formatter={(v, name) => [usd2(N(v)), String(name)]}
            labelFormatter={(_l, p) => {
              const r = (p?.[0] as { payload?: SportRow } | undefined)?.payload
              if (!r) return ''
              const t = r.trips != null
                ? ` · FY25 ≈ ${Math.round(r.trips)} trips (up to ${Math.round(r.trips_nowait ?? 0)} with no waiting) — our estimate`
                : ''
              return `${r.level} ${r.sport}, ${r.season}${t}`
            }} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Bar dataKey="fy2024" name="FY2024" fill={COLOUR.athletic} fillOpacity={0.4}
            isAnimationActive={false} />
          <Bar dataKey="fy2025" name="FY2025" fill={COLOUR.athletic} isAnimationActive={false} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

/** The regular-route line voted each year, and the price the contract fixes. */
export function TransportationContract({ data }: ChartProps) {
  const d = data as Payload
  const rows = d.contract.regular_line.filter(r => r.fy >= 2016).map(r => ({
    ...r, label: fy(r.fy),
    contract_base: r.optional ? null : r.contract,
    contract_opt: r.optional || r.fy === 2028 ? r.contract : null,
  }))
  return (
    <div style={{ width: '100%', height: 320 }}>
      <ResponsiveContainer>
        <ComposedChart data={rows} margin={{ top: 8, right: 8, left: 4, bottom: 4 }}>
          <CartesianGrid stroke="var(--grid)" vertical={false} />
          <XAxis dataKey="label" tick={tick} interval="preserveStartEnd" minTickGap={10} />
          <YAxis width={52} tickFormatter={v => short(N(v))} tick={tick} />
          <Tooltip contentStyle={box} formatter={(v, name) => [usd(N(v)), String(name)]} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Bar dataKey="budget" name="Regular-route line, voted" fill={COLOUR.regular}
            fillOpacity={0.55} isAnimationActive={false} />
          <Line dataKey="contract_base" name="Contract price" stroke="var(--text-primary)"
            strokeWidth={2.4} dot={{ r: 4 }} connectNulls={false} isAnimationActive={false} />
          <Line dataKey="contract_opt" name="Contract price, optional years"
            stroke="var(--text-primary)" strokeWidth={2} strokeDasharray="5 4"
            dot={{ r: 4, fill: 'var(--surface-1)' }} connectNulls={false}
            isAnimationActive={false} legendType="plainline" />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}

/** Special education transportation: voted and spent, and the circuit breaker's
 *  transportation reimbursement beside it, never netted. */
export function TransportationSped({ data }: ChartProps) {
  const d = data as Payload
  const rows = d.sped.filter(r => r.fy >= 2016).map(r => ({ ...r, label: fy(r.fy) }))
  return (
    <div style={{ width: '100%', height: 320 }}>
      <ResponsiveContainer>
        <ComposedChart data={rows} margin={{ top: 8, right: 8, left: 4, bottom: 4 }}>
          <CartesianGrid stroke="var(--grid)" vertical={false} />
          <XAxis dataKey="label" tick={tick} interval="preserveStartEnd" minTickGap={10} />
          <YAxis width={52} tickFormatter={v => short(N(v))} tick={tick} />
          <Tooltip contentStyle={box} formatter={(v, name) => [usd(N(v)), String(name)]} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Bar dataKey="cb_transport" name="Circuit breaker, transportation, paid that year"
            fill={COLOUR.outside} isAnimationActive={false} />
          <Line dataKey="budget" name="Voted" stroke={COLOUR.sped} strokeDasharray="5 4"
            strokeWidth={2.2} dot={false} connectNulls={false} isAnimationActive={false} />
          <Line dataKey="spent" name="Spent" stroke={COLOUR.sped} strokeWidth={2.4}
            dot={{ r: 2.5 }} connectNulls={false} isAnimationActive={false} />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}
