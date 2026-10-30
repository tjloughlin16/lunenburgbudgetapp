import {
  Bar, BarChart, CartesianGrid, Line, LineChart, ReferenceLine,
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
