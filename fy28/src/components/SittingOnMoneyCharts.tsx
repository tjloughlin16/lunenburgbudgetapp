import {
  Bar, BarChart, CartesianGrid, Legend, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import type { ChartProps } from './analysisCharts'

/* The charts for /analysis/sitting-on-money, drawn from /data/sitting-on-money.json, which
 * scripts/build_sitting_on_money.py writes in the same pass as the markdown. Rule 7f: the
 * SVGs beside the markdown stay for /docs and the PDF; the web page draws these.
 *
 * Nothing here computes a figure (rule 2). Every value arrives in the payload; these
 * components only lay it out. A year a pot has no document for is drawn as NOTHING, never
 * as zero, because "not read" and "held nothing" are different facts and a zero bar would
 * say the second. */

const N = (v: unknown) => (Array.isArray(v) ? Number(v[0]) : Number(v))
const box = {
  background: 'var(--surface-1)', border: '1px solid var(--grid)',
  borderRadius: 8, fontSize: 12.5, color: 'var(--text-primary)',
  boxShadow: '0 2px 10px rgba(0,0,0,.12)', opacity: 1,
}
const usd = (v: number) => (v < 0 ? '-$' : '$') + Math.abs(Math.round(v)).toLocaleString()
const usdk = (v: number) =>
  Math.abs(v) >= 1e6 ? `${v < 0 ? '-' : ''}$${(Math.abs(v) / 1e6).toFixed(1)}M`
    : Math.abs(v) >= 1e3 ? `${v < 0 ? '-' : ''}$${Math.round(Math.abs(v) / 1e3)}k`
      : `$${Math.round(v)}`
const tick = { fontSize: 10.5, fill: 'var(--text-muted)' }

/* The same hues the generated SVGs use, so /docs and the page agree on which pot is which. */
const POT: Record<string, string> = {
  school: '#dc2626', free_cash: '#2b6cb0', stabilization: '#0d9488',
  town_other: '#ea8c00', enterprise: '#7c3aed', relief: '#92400e',
}
const CAT: Record<string, string> = {
  cb: '#dc2626', choice: '#2b6cb0', lunch: '#ea8c00', fees: '#2f8f4e', gifts: '#7c3aed',
}

type Point = { fy: number; value: number }
type Pot = { key: string; label: string; who: string; points: Point[] }
type Cat = { key: string; label: string; short: string }
type SchoolRow = { fy: number; basis: string; total: number } & Record<string, number | string>
type Turn = { fy: number; school: number | null; town_wide: number | null }
type Payload = {
  pots: Pot[]; years: number[]
  school_categories: Cat[]; school_series: SchoolRow[]
  turnback: Turn[]
}

/** THE SIGNATURE: one small panel per pot, every panel on ONE dollar scale and the same
 *  run of years, so whether each one is growing -- and how big it is beside the others --
 *  reads at a glance. */
export function SittingOnMoneyBalances({ data }: ChartProps) {
  const { pots, years } = data as Payload
  const all = pots.flatMap(p => p.points.map(q => q.value))
  const hi = Math.max(...all) * 1.05
  const lo = Math.min(0, ...all)
  return (
    <div className="grid gap-x-5 gap-y-6"
      style={{ gridTemplateColumns: 'repeat(auto-fit,minmax(240px,1fr))' }}>
      {pots.map(p => {
        const at = new Map(p.points.map(q => [q.fy, q.value]))
        const rows = years.map(fy => ({ fy: `FY${String(fy).slice(2)}`, value: at.get(fy) ?? null }))
        const first = p.points[0], last = p.points[p.points.length - 1]
        return (
          <div key={p.key} style={{ minWidth: 0 }}>
            <div className="text-[12.5px] font-semibold" style={{ color: 'var(--text-primary)' }}>
              {p.label}
            </div>
            <div className="text-[11px]" style={{ color: 'var(--text-muted)' }}>
              FY{first.fy} {usdk(first.value)} → FY{last.fy} {usdk(last.value)}
            </div>
            <div style={{ width: '100%', height: 132 }}>
              <ResponsiveContainer>
                <BarChart data={rows} margin={{ top: 6, right: 4, left: 0, bottom: 0 }}>
                  <CartesianGrid stroke="var(--grid)" vertical={false} />
                  <XAxis dataKey="fy" tick={tick} interval="preserveStartEnd" />
                  <YAxis domain={[lo, hi]} tickFormatter={usdk} width={46} tick={tick} />
                  <Tooltip contentStyle={box}
                    formatter={(v) => [usd(N(v)), 'held at 30 June']} />
                  <Bar dataKey="value" fill={POT[p.key] ?? '#2b6cb0'} isAnimationActive={false} />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div className="text-[10.5px]" style={{ color: 'var(--text-muted)' }}>{p.who}</div>
          </div>
        )
      })}
    </div>
  )
}

/** The same fourteen school funds, stacked by kind. A fund below zero (the circuit breaker
 *  in FY2013-FY2015) stacks below the axis rather than being hidden inside a total. */
export function SittingOnMoneySchool({ data }: ChartProps) {
  const { school_categories: cats, school_series: series } = data as Payload
  const rows = series.map(r => ({ ...r, fy: `FY${String(r.fy).slice(2)}` }))
  return (
    <div style={{ width: '100%', height: 340 }}>
      <ResponsiveContainer>
        <BarChart data={rows} stackOffset="sign" margin={{ top: 8, right: 8, left: 4, bottom: 4 }}>
          <CartesianGrid stroke="var(--grid)" vertical={false} />
          <XAxis dataKey="fy" tick={tick} interval={0} />
          <YAxis tickFormatter={usdk} width={52} tick={tick} />
          <ReferenceLine y={0} stroke="var(--text-muted)" />
          <Tooltip contentStyle={box} formatter={(v, name) => [usd(N(v)), String(name)]}
            labelFormatter={(l, p) => {
              const row = p?.[0]?.payload as SchoolRow | undefined
              return row ? `${l} · total ${usd(Number(row.total))} · ${row.basis}` : String(l)
            }} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          {cats.map(c => (
            <Bar key={c.key} dataKey={c.key} name={c.short} stackId="s"
              fill={CAT[c.key] ?? '#888'} isAnimationActive={false} />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

/** Unspent appropriations at each close: the whole town from the state's free cash proof,
 *  beside the school department from its own period-13 ledger. Side by side, never added --
 *  they come from two documents. */
export function SittingOnMoneyTurnback({ data }: ChartProps) {
  const rows = (data as Payload).turnback.map(r => ({ ...r, fy: `FY${r.fy}` }))
  return (
    <div style={{ width: '100%', height: 300 }}>
      <ResponsiveContainer>
        <BarChart data={rows} margin={{ top: 8, right: 8, left: 4, bottom: 4 }}>
          <CartesianGrid stroke="var(--grid)" vertical={false} />
          <XAxis dataKey="fy" tick={tick} />
          <YAxis tickFormatter={usdk} width={52} tick={tick} />
          <Tooltip contentStyle={box} formatter={(v, name) => [usd(N(v)), String(name)]} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Bar dataKey="town_wide" name="Whole town (state free cash proof)" fill="#2b6cb0"
            isAnimationActive={false} />
          <Bar dataKey="school" name="School department 300 (MUNIS, period 13)" fill="#dc2626"
            isAnimationActive={false} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
