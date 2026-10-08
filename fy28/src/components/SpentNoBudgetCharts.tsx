import {
  Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import type { ChartProps } from './analysisCharts'

/* The charts for /analysis/spent-with-no-budget, drawn from /data/spent-with-no-budget.json,
 * which scripts/build_spent_no_budget.py writes in the same pass as the markdown. Rule 7f:
 * the SVGs beside the markdown stay for /docs and the PDF; the web page draws these.
 *
 * Nothing here computes a figure (rule 2). The three definitions arrive separately in the
 * payload and are drawn side by side, never stacked: they overlap, so adding them would
 * count the same dollars twice. */

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
      : `${v < 0 ? '-' : ''}$${Math.round(Math.abs(v))}`
const tick = { fontSize: 10.5, fill: 'var(--text-muted)' }
const C_A = '#dc2626'
const C_B = '#7f1d1d'
const C_C = '#2b6cb0'
const VOTED = '#94a3b8'
const YEAR_COLOR: Record<number, string> = { 2023: '#fca5a5', 2024: '#f87171', 2025: '#dc2626', 2026: '#7f1d1d' }

type Yr = { fy: number; a_n: number; a_spent: number; b_n: number; b_spent: number;
  c_n: number; c_moved: number }
type LineYr = { fy: number; orig: number; rev: number; spent: number; defs: string[] }
type Line = { account: string; name: string; munis: string; a_total: number; years: LineYr[] }
type KgYr = { fy: number; voted: number; revised: number; spent: number }
type Payload = { by_year: Yr[]; lines: Line[]; kindergarten: { years: KgYr[] } }

/** THE SIGNATURE: for each closed year, the three definitions side by side. */
export function SpentNoBudgetYears({ data }: ChartProps) {
  const rows = (data as Payload).by_year.map(y => ({ ...y, fy: `FY${y.fy}` }))
  return (
    <div style={{ width: '100%', height: 320 }}>
      <ResponsiveContainer>
        <BarChart data={rows} margin={{ top: 8, right: 8, left: 4, bottom: 4 }}>
          <CartesianGrid stroke="var(--grid)" vertical={false} />
          <XAxis dataKey="fy" tick={tick} />
          <YAxis tickFormatter={usdk} width={52} tick={tick} />
          <Tooltip contentStyle={box}
            formatter={(v, name, item) => {
              const r = item?.payload as Yr | undefined
              const n = !r ? '' : name === '(a) voted $0, spent' ? ` on ${r.a_n} lines`
                : name === '(b) still $0 after transfers, spent' ? ` on ${r.b_n} lines`
                  : ` onto ${r.c_n} lines`
              return [usd(N(v)) + n, String(name)]
            }} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Bar dataKey="a_spent" name="(a) voted $0, spent" fill={C_A} isAnimationActive={false} />
          <Bar dataKey="b_spent" name="(b) still $0 after transfers, spent" fill={C_B}
            isAnimationActive={false} />
          <Bar dataKey="c_moved" name="(c) moved onto a line voted $0" fill={C_C}
            isAnimationActive={false} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

/** Each line that spent against a $0 vote, largest first, the bar split by the year it
 *  happened in. */
export function SpentNoBudgetLines({ data }: ChartProps) {
  const lines = (data as Payload).lines.filter(l => l.a_total > 0)
  const years = Array.from(new Set(lines.flatMap(l => l.years.map(y => y.fy)))).sort()
  const rows = lines.map(l => {
    const r: Record<string, number | string> = { name: l.name, total: l.a_total }
    for (const y of l.years) r[`y${y.fy}`] = y.defs.includes('a') ? y.spent : 0
    return r
  })
  return (
    <div style={{ width: '100%', height: 60 + rows.length * 26 }}>
      <ResponsiveContainer>
        <BarChart data={rows} layout="vertical" margin={{ top: 4, right: 16, left: 4, bottom: 4 }}>
          <CartesianGrid stroke="var(--grid)" horizontal={false} />
          <XAxis type="number" tickFormatter={usdk} tick={tick} />
          <YAxis type="category" dataKey="name" width={190} tick={{ ...tick, fontSize: 10 }}
            interval={0} />
          <Tooltip contentStyle={box}
            formatter={(v, name) => (N(v) ? [usd(N(v)), String(name)] : [null, null]) as [string, string]}
            labelFormatter={(l, p) => {
              const r = p?.[0]?.payload as { total?: number } | undefined
              return r?.total !== undefined ? `${l} · ${usd(r.total)} in all` : String(l)
            }} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          {years.map(y => (
            <Bar key={y} dataKey={`y${y}`} name={`FY${y}`} stackId="a" fill={YEAR_COLOR[y] ?? C_A}
              isAnimationActive={false} />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

/** The worked case: the two kindergarten aide lines together, voted against spent. */
export function SpentNoBudgetKindergarten({ data }: ChartProps) {
  const rows = (data as Payload).kindergarten.years.map(y => ({ ...y, fy: `FY${y.fy}` }))
  return (
    <div style={{ width: '100%', height: 300 }}>
      <ResponsiveContainer>
        <BarChart data={rows} margin={{ top: 8, right: 8, left: 4, bottom: 4 }}>
          <CartesianGrid stroke="var(--grid)" vertical={false} />
          <XAxis dataKey="fy" tick={tick} />
          <YAxis tickFormatter={usdk} width={52} tick={tick} />
          <Tooltip contentStyle={box} formatter={(v, name) => [usd(N(v)), String(name)]}
            labelFormatter={(l, p) => {
              const r = p?.[0]?.payload as KgYr | undefined
              return r ? `${l} · revised ${usd(r.revised)}` : String(l)
            }} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Bar dataKey="voted" name="voted (original budget)" fill={VOTED} isAnimationActive={false} />
          <Bar dataKey="spent" name="spent at the close" fill={C_A} isAnimationActive={false} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
