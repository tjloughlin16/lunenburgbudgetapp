import { useState, type ReactNode } from 'react'
import {
  Bar, BarChart, CartesianGrid, LabelList, Line, LineChart, ReferenceLine,
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
  kept_pace: { bill0: number; bill: number; actual: number; cola: number } }

const usd = (v: number) => `$${Math.round(v).toLocaleString('en-US')}`
const k = (v: number) => (v >= 1000 ? `$${Math.round(v / 1000)}k` : `$${v}`)

/** HOMES AND THE TAX BILL against inflation (TJ, 2 November 2026). Each panel asks one question --
 *  did this outpace inflation? -- so each draws exactly two lines, named where they end, with their
 *  values; there is no legend to look up. A third line on a second axis was tried and removed: TJ,
 *  reading it, "super not clear".
 *
 *  A TOGGLE between two honest views of the same figures (TJ: "sure add the toggle"):
 *    ACTUAL DOLLARS (the default) -- each year as it was paid, beside the first year's figure grown
 *      only with inflation. Nobody has to convert, and the right edge reads as two numbers.
 *    TODAY'S DOLLARS -- every year in the last year's money, so any two years compare directly and
 *      real dips show (a home fell 29% in real terms FY2007-FY2015). Here "only kept up with
 *      inflation" is a FLAT line at the first year's value, which is what keeping pace looks like.
 *  The same component draws the historical report and /homes-and-taxes/growth-and-tax-rate (a custom
 *  block there), so the two pages cannot drift. Two panels, because a home is worth about seventy
 *  times its bill. */
export function HistoricalHomes({ h }: { h: Homes }) {
  const [mode, setMode] = useState<'actual' | 'today'>('actual')
  const today = mode === 'today'
  const f0 = h.rows[0]
  const rows = h.rows.map(r => ({
    x: r.fy,
    bill: today ? r.bill_real : r.bill, bill_cpi: today ? f0.bill_real : r.bill_cpi,
    value: today ? r.value_real : r.value, value_cpi: today ? f0.value_real : r.value_cpi,
  }))
  const last = rows.length - 1
  const a = rows[0], z = rows[last]
  const label = (p: { x?: number | string; y?: number | string; index?: number }, k: number, text: string,
    colour: string, below: boolean, start = false) =>
    p.index === k && p.x != null && p.y != null ? (
      <g key={`${k}${text}`}>
        <circle cx={Number(p.x)} cy={Number(p.y)} r={3.5} fill={colour} />
        <text x={Number(p.x) + (start ? 6 : -6)} y={Number(p.y) + (below ? 17 : -9)} textAnchor={start ? 'start' : 'end'}
          fontSize={12} fontWeight={600} fill="var(--text-primary)" stroke="var(--surface-1)" strokeWidth={3}
          paintOrder="stroke">{text}</text>
      </g>) : null
  const startText = (v: number, what: string) => today
    ? `${usd(v)}, the ${h.first} ${what} in ${h.base} dollars`
    : `${usd(v)}, the ${h.first} ${what}: both lines start here`
  const panel = (title: string, actual: 'value' | 'bill', cpi: 'value_cpi' | 'bill_cpi', colour: string, what: string,
    under?: ReactNode) => (
    <>
      <p className="text-[13px] font-semibold mt-3" style={{ color: 'var(--text-secondary)' }}>
        {title}{today ? `, in ${h.base} dollars` : ''}</p>
      <div style={{ width: '100%', height: 230 }}>
        <ResponsiveContainer>
          <LineChart data={rows} margin={{ top: 24, right: 12, left: 0, bottom: 4 }}>
            <CartesianGrid stroke="var(--grid)" vertical={false} />
            <XAxis dataKey="x" type="number" domain={['dataMin', 'dataMax']} tickCount={8} allowDecimals={false}
              tick={tick} tickFormatter={(v: number) => `FY${String(v).slice(2)}`} />
            <YAxis tickFormatter={(v: number) => k(N(v))} width={52} tick={tick} domain={[0, 'auto']} />
            <Tooltip contentStyle={box} labelFormatter={(l) => `FY${l}`}
              formatter={(v, n) => [usd(N(v)), n === actual
                ? `${what}, ${today ? `${h.base} dollars` : 'actual'}` : 'if it had only kept up with inflation']} />
            <Line dataKey={actual} name={actual} stroke={colour} strokeWidth={2.25} dot={false} isAnimationActive={false}>
              <LabelList dataKey={actual} content={(p: { x?: number | string; y?: number | string; index?: number }) =>
                label(p, 0, startText(a[actual], what), colour, true, true)
                ?? label(p, last, `${usd(z[actual])}, actual ${what}`, colour, false)} />
            </Line>
            <Line dataKey={cpi} name={cpi} stroke="var(--text-muted)" strokeWidth={1.75} strokeDasharray="5 4"
              dot={false} isAnimationActive={false}>
              <LabelList dataKey={cpi} content={(p: { x?: number | string; y?: number | string; index?: number }) =>
                label(p, last, `${usd(z[cpi])}, inflation only`, 'var(--text-muted)', true)} />
            </Line>
          </LineChart>
        </ResponsiveContainer>
      </div>
      {under}
    </>
  )
  const btn = (m: 'actual' | 'today', text: string) => (
    <button type="button" onClick={() => setMode(m)} aria-pressed={mode === m}
      className="px-3 py-1 text-[13px] font-semibold rounded-md cursor-pointer"
      style={mode === m ? { background: 'var(--series-cost)', color: '#fff' }
        : { color: 'var(--text-secondary)', border: '1px solid var(--grid)' }}>{text}</button>)
  return (
    <div className="min-w-0">
      <div className="flex flex-wrap items-center gap-2 mt-3" role="group" aria-label="Dollars shown as">
        {btn('actual', 'Actual dollars')}{btn('today', `Today’s dollars (${h.base})`)}
      </div>
      {panel('Average tax bill', 'bill', 'bill_cpi', AMBER, 'bill',
        <p className="text-[12.5px] mt-1" style={{ color: 'var(--text-muted)' }}>
          Grown instead by Social Security’s cost-of-living adjustments, the {h.first} bill would
          be {usd(h.kept_pace.cola)} in {h.base}. Inflation here is the Boston-area consumer price index.</p>)}
      {panel('Average single-family home, assessed value', 'value', 'value_cpi', BLUE, 'value')}
    </div>
  )
}
