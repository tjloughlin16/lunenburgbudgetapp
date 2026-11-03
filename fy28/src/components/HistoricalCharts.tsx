import {
  Bar, BarChart, CartesianGrid, ComposedChart, Line, LineChart, ReferenceLine,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import type { ChartProps } from './analysisCharts'

/* The charts for /analysis/historical-report, from /data/historical-report.json, which
 * scripts/build_historical_report.py writes. Rule 7f: a chart is a component, never an
 * image. Nothing here computes a figure -- every value arrives from the payload. */

const N = (v: unknown) => (Array.isArray(v) ? Number(v[0]) : Number(v))

const BLUE = '#184f95'
const AMBER = '#e08214'
const box = {
  background: 'var(--surface-1)', border: '1px solid var(--grid)',
  borderRadius: 8, fontSize: 12.5, color: 'var(--text-primary)',
  boxShadow: '0 2px 10px rgba(0,0,0,.12)', opacity: 1,
}
const tick = { fontSize: 11, fill: 'var(--text-muted)' }

type Rate = { edition: number; rate: number; page: number; printed: string }
type Reval = { edition: number; page: number; quote: string }
type Pop = { year: number; value: number; kind: string; edition: number; page: number }
type Names = { year: number; names: number }
type Payload = {
  tax_rate: Rate[]; revaluations: Reval[]; population: Pop[]; roster_names: Names[]
}

/** THE SIGNATURE: the rate on the front of every report, with the three revaluations the
 *  reports record drawn where they fall. The cliffs are the point -- a rate per $1,000 is
 *  only comparable within one assessment, and this line is several assessments. */
export function HistoricalTaxRate({ data }: ChartProps) {
  const d = data as Payload
  return (
    <div style={{ width: '100%', height: 320 }}>
      <ResponsiveContainer>
        <LineChart data={d.tax_rate} margin={{ top: 20, right: 16, left: 0, bottom: 4 }}>
          <CartesianGrid stroke="var(--grid)" vertical={false} />
          <XAxis dataKey="edition" type="number" domain={['dataMin', 'dataMax']}
            tickCount={8} allowDecimals={false} tick={tick} />
          <YAxis tickFormatter={(v: number) => `$${N(v)}`} width={48} tick={tick} />
          <Tooltip contentStyle={box}
            labelFormatter={(l) => `${l} report`}
            formatter={(v, _n, p: { payload?: Rate }) =>
              [`$${N(v).toFixed(2)} per $1,000 — p. ${p.payload?.page}`, 'printed rate']} />
          {d.revaluations.map(r => (
            <ReferenceLine key={r.edition} x={r.edition} stroke={AMBER} strokeDasharray="4 3"
              label={{ value: 'revalued', position: 'top', fontSize: 10.5, fill: AMBER }} />
          ))}
          <Line dataKey="rate" type="linear" stroke={BLUE} strokeWidth={2}
            dot={{ r: 2.5 }} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

/** Residents by the year each census counted them. Only the census counts are drawn; the
 *  town's own yearly census is a different count and sits in the table. */
export function HistoricalPopulation({ data }: ChartProps) {
  const d = data as Payload
  return (
    <div style={{ width: '100%', height: 300 }}>
      <ResponsiveContainer>
        <LineChart data={d.population} margin={{ top: 8, right: 16, left: 0, bottom: 4 }}>
          <CartesianGrid stroke="var(--grid)" vertical={false} />
          <XAxis dataKey="year" type="number" domain={['dataMin', 'dataMax']}
            tickCount={7} allowDecimals={false} tick={tick} />
          <YAxis tickFormatter={(v: number) => N(v).toLocaleString('en-US')} width={56}
            tick={tick} domain={[0, 'auto']} />
          <Tooltip contentStyle={box}
            labelFormatter={(l) => `counted in ${l}`}
            formatter={(v, _n, p: { payload?: Pop }) =>
              [`${N(v).toLocaleString('en-US')} residents (${p.payload?.kind}) — `
               + `${p.payload?.edition} report, p. ${p.payload?.page}`, 'population']} />
          <Line dataKey="value" type="linear" stroke={BLUE} strokeWidth={2}
            dot={{ r: 3.5 }} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

/** Distinct names printed in the school staff rosters, per report. A count of names on a
 *  page, not a staffing level. */
export function HistoricalRosters({ data }: ChartProps) {
  const d = data as Payload
  return (
    <div style={{ width: '100%', height: 300 }}>
      <ResponsiveContainer>
        <BarChart data={d.roster_names} margin={{ top: 8, right: 16, left: 0, bottom: 4 }}>
          <CartesianGrid stroke="var(--grid)" vertical={false} />
          <XAxis dataKey="year" type="number" domain={['dataMin - 1', 'dataMax + 1']}
            tickCount={8} allowDecimals={false} tick={tick} />
          <YAxis width={40} tick={tick} />
          <Tooltip contentStyle={box}
            labelFormatter={(l) => `${l} report`}
            formatter={(v) => [`${N(v)} names`, 'printed']} />
          <Bar dataKey="names" fill={BLUE} isAnimationActive={false} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

export type HomeRow = { fy: number; value: number; bill: number; value_cpi: number; bill_cpi: number
  value_real: number; bill_real: number
  share: number; rate: number; rate_printed: boolean; parcels: number }
export type Homes = { base: string; first: string; rows: HomeRow[]; value_growth: number; bill_growth: number
  jump: { fy0: string; fy1: string; value: number; bill: number; rate0: number; rate1: number }
  kept_pace: { bill0: number; bill: number; actual: number } }

const usd = (v: number) => `$${Math.round(v).toLocaleString('en-US')}`
const k = (v: number) => (v >= 1000 ? `$${Math.round(v / 1000)}k` : `$${v}`)

/** HOMES AND THE TAX BILL (TJ, 2 November 2026). TWO PANELS on one year axis, not one chart: a
 *  home is worth about seventy times its bill, so on a shared dollar axis the bill is a flat line
 *  on the floor. Each panel draws the ACTUAL figure, in each year's own dollars, beside the first
 *  year's figure grown only with inflation -- the gap is the growth beyond inflation, and nobody
 *  has to convert (a resident had inflated an already-adjusted figure a second time). The bill's
 *  panel carries the bill as a share of the value on its right axis: the tax rate as a percent. */
export function HistoricalHomes({ h }: { h: Homes }) {
  const rows = h.rows.map(r => ({ ...r, x: r.fy }))
  const xa = <XAxis dataKey="x" type="number" domain={['dataMin', 'dataMax']} tickCount={8}
    allowDecimals={false} tick={tick} tickFormatter={(v: number) => `FY${String(v).slice(2)}`} />
  return (
    <div className="min-w-0">
      <div className="flex flex-wrap gap-x-4 gap-y-1 text-[12.5px] font-semibold mt-1" style={{ color: 'var(--text-secondary)' }}>
        <span><span aria-hidden style={{ color: BLUE }}>━</span> Average single-family home, assessed value, actual</span>
        <span><span aria-hidden>┅</span> The {h.first} value, grown only with inflation</span>
      </div>
      <div style={{ width: '100%', height: 200 }}>
        <ResponsiveContainer>
          <LineChart data={rows} margin={{ top: 8, right: 52, left: 0, bottom: 0 }} syncId="homes">
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            {xa}
            <YAxis tickFormatter={(v: number) => k(N(v))} width={52} tick={tick} domain={[0, 'auto']} />
            <Tooltip contentStyle={box} labelFormatter={(l) => `FY${l}`}
              formatter={(v, n) => [usd(N(v)), n === 'value' ? 'average value, actual' : `${h.first} value grown with inflation`]} />
            <Line dataKey="value" name="value" stroke={BLUE} strokeWidth={2} dot={false} isAnimationActive={false} />
            <Line dataKey="value_cpi" name="value_cpi" stroke="var(--text-muted)" strokeWidth={1.5} strokeDasharray="5 4"
              dot={false} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div className="flex flex-wrap gap-x-4 gap-y-1 text-[12.5px] font-semibold mt-3" style={{ color: 'var(--text-secondary)' }}>
        <span><span aria-hidden style={{ color: AMBER }}>━</span> Average tax bill, actual (left)</span>
        <span><span aria-hidden style={{ color: 'var(--text-muted)' }}>┅</span> The {h.first} bill, grown only with inflation (left)</span>
        <span><span aria-hidden>·····</span> Bill as a share of the value, which is the tax rate (right)</span>
      </div>
      <div style={{ width: '100%', height: 220 }}>
        <ResponsiveContainer>
          <ComposedChart data={rows} margin={{ top: 8, right: 0, left: 0, bottom: 4 }} syncId="homes">
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            {xa}
            <YAxis yAxisId="d" tickFormatter={(v: number) => k(N(v))} width={52} tick={tick} domain={[0, 'auto']} />
            <YAxis yAxisId="p" orientation="right" width={52} tick={tick} domain={[0, 'auto']}
              tickFormatter={(v: number) => `${N(v).toFixed(1)}%`} />
            <Tooltip contentStyle={box} labelFormatter={(l) => `FY${l}`}
              formatter={(v, n, p: { payload?: HomeRow }) => n === 'share'
                ? [`${N(v).toFixed(2)}% ($${p.payload?.rate.toFixed(2)} per $1,000)`, 'bill as share of value']
                : [usd(N(v)), n === 'bill' ? 'average bill, actual' : `${h.first} bill grown with inflation`]} />
            <Line yAxisId="d" dataKey="bill" name="bill" stroke={AMBER} strokeWidth={2} dot={false} isAnimationActive={false} />
            <Line yAxisId="d" dataKey="bill_cpi" name="bill_cpi" stroke="var(--text-muted)" strokeWidth={1.5}
              strokeDasharray="5 4" dot={false} isAnimationActive={false} />
            <Line yAxisId="p" dataKey="share" name="share" stroke="var(--text-primary)" strokeWidth={1.5}
              strokeDasharray="1 3" dot={false} isAnimationActive={false} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
